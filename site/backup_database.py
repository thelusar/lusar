"""Read-only encrypted export with an optional isolated local recovery rehearsal.

Requires PostgreSQL 18 tools, psycopg and age. Production credentials never enter
command arguments. Recovery targets are always freshly initialized loopback-only
clusters; no production restore URL is accepted.
"""
import argparse
import getpass
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


def connection_environment(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path.strip("/"):
        raise ValueError("Set a valid DATABASE_URL in the environment; never pass it as an argument.")
    env = os.environ.copy()
    # Avoid unintentionally inheriting connection overrides from another project.
    for key in tuple(env):
        if key.startswith("PG") or key == "DATABASE_URL":
            env.pop(key)
    env.update(PGHOST=parsed.hostname, PGPORT=str(parsed.port or 5432),
               PGDATABASE=unquote(parsed.path.lstrip("/")), PGUSER=unquote(parsed.username or ""),
               PGPASSWORD=unquote(parsed.password or ""), PGCONNECT_TIMEOUT="10")
    sslmode = parse_qs(parsed.query).get("sslmode", ["require"])[0]
    if sslmode not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("Backup requires an encrypted database connection.")
    env["PGSSLMODE"] = sslmode
    return env


class BackupError(Exception):
    """Safe operational message; raw connection/provider errors are never logged."""


def run(command, *, env=None, timeout=600):
    try:
        options = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL} if Path(command[0]).stem == "pg_ctl" else {"capture_output": True}
        result = subprocess.run([str(x) for x in command], env=env, timeout=timeout, **options)
    except (OSError, subprocess.SubprocessError):
        raise BackupError("Backup tool could not complete. Private connection settings were not printed.") from None
    if result.returncode:
        raise BackupError(f"{Path(command[0]).name} failed; raw output suppressed to protect secrets.")
    return result.stdout or b""


def private_directory(directory):
    directory = Path(directory).resolve()
    repo = Path(__file__).resolve().parents[1]
    if directory == repo or repo in directory.parents:
        raise BackupError("Choose a private directory OUTSIDE the Git repository.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "nt":
        identity = run(["whoami", "/user", "/fo", "csv", "/nh"]).decode(errors="replace")
        sid = re.search(r"S-1-5-[0-9-]+", identity)
        if not sid:
            raise BackupError("Cannot establish private folder ownership.")
        run(["icacls", directory, "/inheritance:r", "/grant:r", f"*{sid[0]}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"])
    else:
        directory.chmod(0o700)
    return directory


def binaries(directory=None):
    result = {}
    for name in ("pg_dump", "pg_restore", "initdb", "pg_ctl", "createdb"):
        candidate = Path(directory) / (name + (".exe" if os.name == "nt" else "")) if directory else shutil.which(name)
        if candidate and Path(candidate).is_file():
            result[name] = str(candidate)
    if not all(x in result for x in ("pg_dump", "pg_restore")):
        raise BackupError("PostgreSQL 18 pg_dump and pg_restore are required.")
    for name in ("pg_dump", "pg_restore"):
        version = run([result[name], "--version"]).decode().strip()
        if not re.search(r"\b18\.[0-9]+\b", version):
            raise BackupError("PostgreSQL 18 client tools are required.")
    return result


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(db):
    """Only aggregate counts and hashes leave the connection; no customer rows."""
    from psycopg import sql
    db.execute("SET TIME ZONE 'UTC'")
    names = list(db.execute("SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT LIKE 'pg_%' AND schemaname <> 'information_schema' ORDER BY schemaname, tablename"))
    tables = {}
    for schema, name in names:
        query = sql.SQL("""SELECT COUNT(*), encode(sha256(convert_to(COALESCE(string_agg(h, '' ORDER BY h), ''), 'UTF8')), 'hex')
            FROM (SELECT encode(sha256(convert_to(row_to_json(t)::text, 'UTF8')), 'hex') h FROM {} t) hashes""").format(sql.Identifier(schema, name))
        count, checksum = db.execute(query).fetchone()
        tables[name if schema == "public" else schema + "." + name] = {"rows": count, "sha256": checksum}
    migrations = [r[0] for r in db.execute("SELECT version FROM public.lusar_migrations ORDER BY version")] if "lusar_migrations" in tables else []
    invalid = db.execute("SELECT COUNT(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema' AND NOT c.convalidated").fetchone()[0]
    return {"tables": tables, "migrations": migrations, "unvalidatedConstraints": invalid}


def source_connection(env):
    import psycopg
    options = {"sslrootcert": env["PGSSLROOTCERT"]} if env.get("PGSSLROOTCERT") else {}
    return psycopg.connect(host=env["PGHOST"], port=env["PGPORT"], dbname=env["PGDATABASE"], user=env["PGUSER"],
                          password=env["PGPASSWORD"], sslmode=env["PGSSLMODE"], connect_timeout=10,
                          options="-c default_transaction_read_only=on", **options)


def create_backup(url, directory, *, tools, age, recipient, network="external"):
    """Snapshot-consistent export and evidence; production connection is read-only."""
    import psycopg
    if not re.fullmatch(r"age1[0-9a-z]{40,100}", recipient):
        raise BackupError("A valid age encryption recipient is required.")
    directory = private_directory(directory)
    env = connection_environment(url)
    # Require certificate verification for the real remote database.
    if network == "render-private":
        if os.environ.get("RENDER") != "true" or not re.fullmatch(r"dpg-[a-z0-9-]+", env["PGHOST"]):
            raise BackupError("Private backup connections require a Render job and its internal database hostname.")
        # Render's private-network certificates are self-signed (official docs).
        env["PGSSLMODE"] = "require"
        env.pop("PGSSLROOTCERT", None)
    elif network == "external":
        env["PGSSLMODE"] = "verify-full"
        env["PGSSLROOTCERT"] = os.environ.get("LUSAR_BACKUP_CA_FILE", "system")
    else:
        raise BackupError("Unknown backup network route.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = directory / ("lusar-" + stamp + ".dump.age")
    partial = target.with_suffix(".age.partial")
    try:
        with tempfile.TemporaryDirectory(prefix=".export-", dir=directory) as temporary:
            archive = Path(temporary) / "database.dump"
            with source_connection(env) as db:
                db.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
                db.read_only = True
                snapshot = db.execute("SELECT pg_export_snapshot()").fetchone()[0]
                evidence = fingerprint(db)
                run([tools["pg_dump"], "--format=custom", "--no-owner", "--no-acl", "--no-password", "--snapshot=" + snapshot,
                     "--file", archive], env=env)
            listing = run([tools["pg_restore"], "--list", archive])
            if not archive.stat().st_size or b"TABLE" not in listing:
                raise BackupError("Archive catalogue is empty or invalid.")
            plain_hash = digest(archive)
            run([age, "--recipient", recipient, "--output", partial, archive])
            partial.rename(target)
        manifest = {"createdUTC": datetime.now(timezone.utc).isoformat(), "bytes": target.stat().st_size,
                    "sha256": digest(target), "plaintextSHA256": plain_hash, "encryption": "age-X25519",
                    "recipient": recipient, "archiveListValidated": True, "restoreTested": False, "source": evidence,
                    "client": run([tools["pg_dump"], "--version"]).decode().strip()}
        manifest_path = target.with_suffix(".json")
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return target, manifest_path, manifest
    except (psycopg.Error, ValueError, OSError) as error:
        raise BackupError("Export or snapshot verification failed. Connection details were not printed.") from None


def restore_locally(archive, manifest_path, *, tools, age, identity):
    """Restore ONLY to a newly initialized loopback cluster, never a supplied URL."""
    import psycopg
    archive = Path(archive).resolve()
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if digest(archive) != manifest["sha256"]:
        raise BackupError("Encrypted archive checksum mismatch.")
    if not all(name in tools for name in ("initdb", "pg_ctl", "createdb")):
        raise BackupError("Local PostgreSQL 18 server tools are required for the restore rehearsal.")
    directory = private_directory(archive.parent)
    with tempfile.TemporaryDirectory(prefix=".restore-", dir=directory) as temporary:
        root = Path(temporary).resolve()
        if root.parent != directory or not root.name.startswith(".restore-"):
            raise BackupError("Invalid recovery directory.")
        data = root / "pgdata"
        password_file = root / "password"
        password = secrets.token_urlsafe(32)
        password_file.write_text(password, encoding="ascii")
        restored_dump = root / "database.dump"
        run([age, "--decrypt", "--identity", identity, "--output", restored_dump, archive])
        if digest(restored_dump) != manifest["plaintextSHA256"]:
            raise BackupError("Decrypted archive checksum mismatch.")
        run([tools["pg_restore"], "--list", restored_dump])
        run([tools["initdb"], "--pgdata", data, "--username=lusar_recovery", "--pwfile", password_file,
             "--auth-local=scram-sha-256", "--auth-host=scram-sha-256", "--encoding=UTF8", "--no-locale"])
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if not k.startswith("PG") and k != "DATABASE_URL"}
        env.update(PGHOST="127.0.0.1", PGPORT=str(port), PGUSER="lusar_recovery", PGPASSWORD=password, PGSSLMODE="disable")
        started = False
        try:
            run([tools["pg_ctl"], "--pgdata", data, "--log", root / "postgres.log", "--wait", "--timeout=60", "-o",
                 f"-h 127.0.0.1 -p {port} -c max_connections=10", "start"])
            started = True
            name = "lusar_restore_" + secrets.token_hex(8)
            run([tools["createdb"], "--no-password", "--template=template0", name], env=env)
            run([tools["pg_restore"], "--no-owner", "--no-acl", "--exit-on-error", "--single-transaction", "--no-password",
                 "--dbname", name, restored_dump], env=env)
            with psycopg.connect(host="127.0.0.1", port=port, user="lusar_recovery", password=password, dbname=name, sslmode="disable") as db:
                db.read_only = True
                recovered = fingerprint(db)
            if recovered != manifest["source"] or recovered["unvalidatedConstraints"]:
                raise BackupError("Recovery data or constraints differ from the exported production snapshot.")
            manifest["restoreTested"] = True
            manifest["restoredUTC"] = datetime.now(timezone.utc).isoformat()
            manifest["restoreChecks"] = {"allTableHashesMatch": True, "constraintsValidated": True,
                                         "tables": {name: item["rows"] for name, item in recovered["tables"].items()},
                                         "notificationsOrAIWorkersStarted": False, "publicConnectionUsed": False}
        finally:
            if started:
                run([tools["pg_ctl"], "--pgdata", data, "--wait", "--mode=fast", "stop"])
        manifest["restoreChecks"]["temporaryClusterStopped"] = True
    manifest["restoreChecks"]["temporaryDataRemoved"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[2] / ".lusar-backups")
    parser.add_argument("--bin-dir", type=Path)
    parser.add_argument("--age", default="age")
    parser.add_argument("--recipient-file", type=Path, required=True)
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    try:
        tools = binaries(args.bin_dir)
        url = getpass.getpass("Paste Render External Database URL (hidden; never goes to chat): ") if args.interactive else os.environ.get("DATABASE_URL", "")
        target, manifest_path, manifest = create_backup(url.strip(), args.directory, tools=tools, age=args.age,
                                                     recipient=args.recipient_file.read_text(encoding="utf-8").strip())
        url = None
        print(f"Encrypted backup: {target}\nBytes: {manifest['bytes']}\nSHA256: {manifest['sha256']}", flush=True)
        if args.identity:
            manifest = restore_locally(target, manifest_path, tools=tools, age=args.age, identity=args.identity)
        print("Restore verified: " + str(manifest["restoreTested"]), flush=True)
    except BackupError as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
