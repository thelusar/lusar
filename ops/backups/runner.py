"""Opt-in encrypted exports and age monitoring; no application workers imported."""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "site"))
import backup_database as backup

PREFIX = "lusar/"
MAX_AGE_HOURS = 30
RESTORE_MAX_DAYS = 35


def age_hours(record, *, now=None):
    if not record:
        return float("inf")
    created = datetime.fromisoformat(record["createdUTC"])
    if created.tzinfo is None:
        raise backup.BackupError("Backup timestamp must include its timezone.")
    value = ((now or datetime.now(timezone.utc)) - created).total_seconds() / 3600
    if value < -1:
        raise backup.BackupError("Backup timestamp is in the future.")
    return max(0, value)


def client():
    import boto3
    required = ["LUSAR_BACKUP_S3_ENDPOINT", "LUSAR_BACKUP_S3_BUCKET", "LUSAR_BACKUP_ACCESS_KEY_ID", "LUSAR_BACKUP_SECRET_ACCESS_KEY"]
    if not all(os.environ.get(name) for name in required):
        raise backup.BackupError("Private backup storage is not configured.")
    endpoint = urlsplit(os.environ[required[0]])
    if endpoint.scheme != "https" or endpoint.username or endpoint.query or endpoint.fragment:
        raise backup.BackupError("Private storage requires an HTTPS endpoint without embedded credentials.")
    return boto3.client("s3", endpoint_url=os.environ[required[0]], region_name="auto",
                        aws_access_key_id=os.environ[required[2]], aws_secret_access_key=os.environ[required[3]])


def get_record(s3, bucket, key):
    from botocore.exceptions import ClientError
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
    except ClientError as error:
        if error.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
            return None
        raise backup.BackupError("Backup status could not be read.") from None
    with response["Body"] as body:
        return json.loads(body.read(1024 * 1024))


def put_record(s3, bucket, key, record):
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(record).encode(), ContentType="application/json")


def upload_verified(s3, bucket, key, archive, expected_hash):
    if not key.startswith(PREFIX) or not key.endswith(".dump.age"):
        raise backup.BackupError("Only encrypted LUSAR backup objects may be uploaded.")
    s3.upload_file(str(archive), bucket, key, ExtraArgs={"ContentType": "application/octet-stream", "Metadata": {"sha256": expected_hash}})
    response = s3.get_object(Bucket=bucket, Key=key)
    digest = hashlib.sha256()
    with response["Body"] as body:
        for chunk in body.iter_chunks(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != expected_hash:
        raise backup.BackupError("Remote encrypted archive failed read-back checksum verification.")


def signal(success):
    # Optional administrator-owned URLs; no row data, credentials or raw errors.
    targets = []
    heartbeat = os.environ.get("LUSAR_BACKUP_HEARTBEAT_URL", "")
    if heartbeat:
        targets.append((heartbeat if success else heartbeat.rstrip("/") + "/fail", b""))
    alert = os.environ.get("LUSAR_BACKUP_ALERT_WEBHOOK", "")
    if not success and alert:
        targets.append((alert, b'{"service":"LUSAR backups","status":"failed"}'))
    ok = True
    for url, body in targets:
        if urlsplit(url).scheme != "https":
            ok = False
            continue
        try:
            with urlopen(Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=15) as response:
                response.read(1024)
        except Exception:
            ok = False
    return ok


def record_restore(s3, bucket, manifest):
    checks = manifest.get("restoreChecks", {})
    key = manifest.get("remoteKey", "")
    if not (manifest.get("restoreTested") and checks.get("allTableHashesMatch") and checks.get("constraintsValidated")
            and checks.get("temporaryClusterStopped") and checks.get("temporaryDataRemoved") and key.startswith(PREFIX)):
        raise backup.BackupError("A completed independent recovery rehearsal is required.")
    remote = get_record(s3, bucket, key + ".json")
    if not remote or remote.get("sha256") != manifest.get("sha256"):
        raise backup.BackupError("Recovery proof does not match the remote backup.")
    record = {"createdUTC": manifest["restoredUTC"], "restoreTested": True, "key": key,
              "sha256": manifest["sha256"], "allTableHashesMatch": True}
    put_record(s3, bucket, PREFIX + "control/last-restore.json", record)


def execute(mode, *, archive=None, manifest_path=None):
    s3 = client()
    bucket = os.environ["LUSAR_BACKUP_S3_BUCKET"]
    if mode in {"seed", "record-restore"}:
        if not manifest_path:
            raise backup.BackupError("A private manifest path is required.")
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        if mode == "seed":
            if not archive or backup.digest(archive) != manifest.get("sha256") or manifest.get("encryption") != "age-X25519":
                raise backup.BackupError("A valid encrypted local backup is required.")
            key = PREFIX + "daily/" + Path(archive).name
            upload_verified(s3, bucket, key, archive, manifest["sha256"])
            manifest.update(remoteKey=key, remoteReadbackVerified=True)
            put_record(s3, bucket, key + ".json", manifest)
            put_record(s3, bucket, PREFIX + "control/last-success.json", {"createdUTC": manifest["createdUTC"],
                       "key": key, "sha256": manifest["sha256"], "readbackVerified": True})
            Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        record_restore(s3, bucket, manifest)
        print("Encrypted archive and independent recovery proof verified in private storage.")
        return
    latest = get_record(s3, bucket, PREFIX + "control/last-success.json")
    if mode in {"backup", "prechange"} or (mode == "scheduled" and age_hours(latest) >= 20):
        recipient = os.environ.get("LUSAR_BACKUP_RECIPIENT", "").strip()
        with tempfile.TemporaryDirectory(prefix="lusar-export-") as temporary:
            archive, manifest_path, manifest = backup.create_backup(os.environ.get("DATABASE_URL", ""), temporary,
                tools=backup.binaries(), age="age", recipient=recipient, network=os.environ.get("LUSAR_BACKUP_NETWORK", "external"))
            kind = "prechange" if mode == "prechange" else "daily"
            key = PREFIX + kind + "/" + archive.name
            upload_verified(s3, bucket, key, archive, manifest["sha256"])
            manifest.update(remoteKey=key, remoteReadbackVerified=True)
            put_record(s3, bucket, key + ".json", manifest)
            now = datetime.now(timezone.utc)
            if now.day == 1 and kind == "daily":
                monthly = PREFIX + "monthly/" + archive.name
                upload_verified(s3, bucket, monthly, archive, manifest["sha256"])
                put_record(s3, bucket, monthly + ".json", manifest)
            if kind == "daily":
                latest = {"createdUTC": manifest["createdUTC"], "key": key, "sha256": manifest["sha256"], "readbackVerified": True}
                put_record(s3, bucket, PREFIX + "control/last-success.json", latest)
    if mode != "prechange" and (not latest or not latest.get("readbackVerified") or age_hours(latest) > MAX_AGE_HOURS):
        raise backup.BackupError("No verified backup within the last 30 hours.")
    restored = get_record(s3, bucket, PREFIX + "control/last-restore.json")
    restore_due = not restored or not restored.get("restoreTested") or age_hours(restored) > RESTORE_MAX_DAYS * 24
    if restore_due:
        raise backup.BackupError("Backup exists, but independent recovery proof is missing or older than 35 days.")
    print(json.dumps({"backupVerified": True, "backupAgeHours": round(age_hours(latest), 2), "restoreDue": False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["scheduled", "backup", "prechange", "watch", "seed", "record-restore"], default="scheduled")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        execute(args.mode, archive=args.archive, manifest_path=args.manifest)
        if not signal(True):
            raise backup.BackupError("Backup verified, but its configured monitoring signal failed.")
    except Exception as error:
        signal(False)
        # Provider exceptions may contain connection details or signed URLs.
        message = str(error) if isinstance(error, backup.BackupError) else "Backup operation failed; private diagnostics suppressed."
        print(message, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
