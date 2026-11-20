import json
import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import backup_local as local


class LocalBackupTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows DPAPI")
    def test_windows_protection_roundtrip_without_plaintext_storage(self):
        value = b"postgresql://synthetic:private-value@example.invalid/fixture"
        encrypted = local.protect(value)
        self.assertNotIn(b"private-value", encrypted)
        self.assertEqual(local.protect(encrypted, decrypt=True), value)
        with self.assertRaises(local.backup.BackupError):
            local.protect(b"corrupt-envelope", decrypt=True)

    def test_retention_preserves_newest_two_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(local, "DIRECTORY", Path(temporary)):
            root = Path(temporary) / "daily"
            root.mkdir()
            now = datetime.now(timezone.utc)
            paths = []
            for index in range(4):
                stamp = (now - timedelta(days=40 + index)).strftime("%Y%m%dT%H%M%S%fZ")
                archive = root / ("lusar-" + stamp + ".dump.age")
                archive.write_bytes(b"synthetic-encrypted")
                archive.with_suffix(".json").write_text(json.dumps({"createdUTC": (now - timedelta(days=40 + index)).isoformat(),
                    "sha256": "synthetic", "archiveListValidated": True, "encryption": "age-X25519"}), encoding="utf-8")
                paths.append(archive)
            unrelated = root / "other.dump.age"
            unrelated.write_bytes(b"untouched")
            local.prune(root, days=30, keep=2)
            self.assertEqual([path.exists() for path in paths], [True, True, False, False])
            self.assertTrue(unrelated.exists())

    def test_retention_refuses_other_directories(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(local, "DIRECTORY", Path(temporary)):
            with self.assertRaises(local.backup.BackupError):
                local.prune(Path(temporary), days=30)

    def test_recent_backup_does_not_unlock_credentials_or_connect(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(local, "DIRECTORY", Path(temporary)), \
                patch.object(local.backup, "private_directory", return_value=Path(temporary)), patch.object(local, "protect") as decrypt:
            (Path(temporary) / "last-success.json").write_text(json.dumps({"createdUTC": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
            self.assertEqual(local.run_daily()["state"], "fresh")
            decrypt.assert_not_called()

    def test_status_does_not_claim_unenrolled_schedule(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(local, "DIRECTORY", Path(temporary)):
            state = local.status()
            self.assertFalse(state["schedule"]["enabled"])
            self.assertFalse(state["backupFresh"])
            self.assertFalse(state["cloudUploads"])


if __name__ == "__main__":
    unittest.main()
