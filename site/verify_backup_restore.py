"""Repeat local recovery of an encrypted archive, without production credentials."""
import argparse
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / ".local-tools/backup-python"))
import backup_database as backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--identity", type=Path, default=WORKSPACE / ".lusar-backups/recovery-identity.key")
    parser.add_argument("--bin-dir", type=Path, default=WORKSPACE / ".local-tools/postgresql-18.7/pgsql/bin")
    parser.add_argument("--age", type=Path, default=WORKSPACE / ".local-tools/age-1.3.2/age/age.exe")
    args = parser.parse_args()
    try:
        manifest = backup.restore_locally(args.archive, args.archive.with_suffix(".json"), tools=backup.binaries(args.bin_dir),
                                         age=args.age, identity=args.identity)
    except Exception:
        raise SystemExit("Recovery verification did not complete; private diagnostics suppressed.") from None
    print(json.dumps({"restoreTested": manifest["restoreTested"], "restoredUTC": manifest["restoredUTC"],
                      "checks": manifest["restoreChecks"]}, indent=2))


if __name__ == "__main__":
    main()
