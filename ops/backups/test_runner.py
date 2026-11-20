import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / ".local-tools/backup-python"))
import runner
from botocore.exceptions import ClientError


class Body(io.BytesIO):
    def iter_chunks(self, size):
        while chunk := self.read(size):
            yield chunk


class Storage:
    def __init__(self):
        self.objects = {}
        self.corrupt = False

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"ResponseMetadata": {"HTTPStatusCode": 404}}, "GetObject")
        return {"Body": Body(self.objects[Key] + (b"corrupt" if self.corrupt and Key.endswith(".age") else b""))}

    def upload_file(self, filename, bucket, key, **kwargs):
        self.objects[key] = Path(filename).read_bytes()


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.s3 = Storage()
        self.now = datetime.now(timezone.utc)
        self.client = patch.object(runner, "client", return_value=self.s3)
        self.client.start()
        self.env = patch.dict(os.environ, {"LUSAR_BACKUP_S3_BUCKET": "synthetic", "LUSAR_BACKUP_RECIPIENT": "synthetic"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.client.stop()

    def record(self, key, age, **values):
        runner.put_record(self.s3, "synthetic", runner.PREFIX + "control/" + key + ".json",
                          {"createdUTC": (self.now - timedelta(hours=age)).isoformat(), **values})

    def test_future_timestamp_rejected(self):
        with self.assertRaises(runner.backup.BackupError):
            runner.age_hours({"createdUTC": (self.now + timedelta(hours=2)).isoformat()}, now=self.now)

    def test_fresh_backup_is_monitored_without_new_export(self):
        self.record("last-success", 12, readbackVerified=True)
        self.record("last-restore", 24, restoreTested=True)
        with patch.object(runner.backup, "create_backup") as create:
            runner.execute("scheduled")
            create.assert_not_called()

    def test_stale_backup_fails_watch(self):
        self.record("last-success", 31, readbackVerified=True)
        with self.assertRaises(runner.backup.BackupError):
            runner.execute("watch")

    def test_missing_recovery_proof_fails(self):
        self.record("last-success", 2, readbackVerified=True)
        with self.assertRaises(runner.backup.BackupError):
            runner.execute("watch")

    def test_recovery_proof_expires_after_35_days(self):
        self.record("last-success", 2, readbackVerified=True)
        self.record("last-restore", 36 * 24, restoreTested=True)
        with self.assertRaises(runner.backup.BackupError):
            runner.execute("watch")

    def test_remote_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.dump.age"
            path.write_bytes(b"encrypted-synthetic")
            self.s3.corrupt = True
            with self.assertRaises(runner.backup.BackupError):
                runner.upload_verified(self.s3, "synthetic", "lusar/daily/test.dump.age", path, runner.backup.digest(path))
        self.assertNotIn("lusar/control/last-success.json", self.s3.objects)

    def test_unencrypted_upload_is_rejected_before_s3(self):
        with self.assertRaises(runner.backup.BackupError):
            runner.upload_verified(self.s3, "synthetic", "lusar/daily/test.dump", "unused", "unused")
        self.assertFalse(self.s3.objects)

    def test_recovery_proof_must_match_remote_archive(self):
        proof = {"restoreTested": True, "remoteKey": "lusar/daily/test.dump.age", "sha256": "correct",
                 "restoredUTC": self.now.isoformat(), "restoreChecks": {"allTableHashesMatch": True, "constraintsValidated": True,
                 "temporaryClusterStopped": True, "temporaryDataRemoved": True}}
        runner.put_record(self.s3, "synthetic", proof["remoteKey"] + ".json", {"sha256": "wrong"})
        with self.assertRaises(runner.backup.BackupError):
            runner.record_restore(self.s3, "synthetic", proof)
        runner.put_record(self.s3, "synthetic", proof["remoteKey"] + ".json", {"sha256": "correct"})
        runner.record_restore(self.s3, "synthetic", proof)
        self.assertTrue(runner.get_record(self.s3, "synthetic", "lusar/control/last-restore.json")["restoreTested"])

    def test_new_export_is_read_back_before_success_marker(self):
        self.record("last-restore", 1, restoreTested=True)
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "test.dump.age"
            archive.write_bytes(b"encrypted-synthetic")
            manifest = {"createdUTC": self.now.isoformat(), "sha256": runner.backup.digest(archive)}
            with patch.object(runner.backup, "binaries", return_value={}), \
                    patch.object(runner.backup, "create_backup", return_value=(archive, archive.with_suffix(".json"), manifest)) as create:
                runner.execute("scheduled")
            create.assert_called_once()
        marker = runner.get_record(self.s3, "synthetic", "lusar/control/last-success.json")
        self.assertTrue(marker["readbackVerified"])

    def test_errors_do_not_expose_credentials_or_signed_urls(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["runner", "--mode", "watch"]), \
                patch.object(runner, "execute", side_effect=RuntimeError("postgres://synthetic-secret@host/db")), \
                patch.object(runner, "signal") as signal, patch.object(sys, "stderr", output):
            with self.assertRaises(SystemExit):
                runner.main()
            signal.assert_called_once_with(False)
        self.assertNotIn("synthetic-secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
