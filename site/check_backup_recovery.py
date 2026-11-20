"""Real PostgreSQL 18 rehearsal using synthetic rows and loopback-only clusters."""
import json
import os
import secrets
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
sys.path.insert(0, str(WORKSPACE / ".local-tools/backup-python"))
import psycopg
import backup_database as backup


def main():
    tools = backup.binaries(WORKSPACE / ".local-tools/postgresql-18.7/pgsql/bin")
    age = WORKSPACE / ".local-tools/age-1.3.2/age/age.exe"
    directory = backup.private_directory(WORKSPACE / ".lusar-backup-tests")
    with tempfile.TemporaryDirectory(prefix="rehearsal-", dir=directory) as temporary:
        root = Path(temporary)
        identity = root / "synthetic-identity.key"
        backup.run([age.with_name("age-keygen.exe"), "-o", identity])
        recipient = backup.run([age.with_name("age-keygen.exe"), "-y", identity]).decode().strip()
        password = secrets.token_hex(24)
        password_file = root / "password"
        password_file.write_text(password, encoding="ascii")
        data = root / "source-pgdata"
        backup.run([tools["initdb"], "-D", data, "-U", "lusar_fixture", "--pwfile", password_file,
                    "--auth-host=scram-sha-256", "--auth-local=scram-sha-256", "--no-locale", "--encoding=UTF8"])
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if not k.startswith("PG") and k != "DATABASE_URL"}
        env.update(PGHOST="127.0.0.1", PGPORT=str(port), PGUSER="lusar_fixture", PGPASSWORD=password, PGDATABASE="lusar_fixture", PGSSLMODE="disable")
        backup.run([tools["pg_ctl"], "-D", data, "-l", root / "source.log", "-w", "-o", f"-h 127.0.0.1 -p {port}", "start"])
        try:
            backup.run([tools["createdb"], "--no-password", "lusar_fixture"], env=env)
            def connect(_=None):
                return psycopg.connect(host="127.0.0.1", port=port, user="lusar_fixture", password=password, dbname="lusar_fixture", sslmode="disable")
            with connect() as db:
                db.execute("CREATE TABLE lusar_migrations (version text PRIMARY KEY)")
                for path in sorted((ROOT / "postgres").glob("*.sql")):
                    db.execute(path.read_text(encoding="utf-8"), prepare=False)
                    db.execute("INSERT INTO lusar_migrations VALUES (%s)", (path.name,))
                db.execute("INSERT INTO customers(id,issuer,subject,email,created) VALUES ('fixture','test','fixture','fixture@example.invalid',0)")
                db.execute("INSERT INTO staff_roles VALUES ('fixture','admin')")
                db.execute("INSERT INTO orders(request_id,fingerprint,number,payload,status,customer_id) VALUES ('00000000-0000-4000-8000-000000000001','synthetic','LS-000001','{\"total\":10000,\"payment\":{\"amount\":10000},\"items\":[]}', 'completed','fixture')")
                db.execute("INSERT INTO order_notifications(number) VALUES ('LS-000001')")
            original_run = backup.run
            modified = False
            def run(command, *, env=None, timeout=600):
                nonlocal modified
                if Path(command[0]).stem == "pg_dump" and env is not None:
                    assert env["PGHOST"] == "127.0.0.1"
                    env = dict(env, PGSSLMODE="disable")
                    env.pop("PGSSLROOTCERT", None)
                    # A write AFTER the exported snapshot must not change archive evidence.
                    with connect() as db:
                        db.execute("INSERT INTO customers(id,issuer,subject,email,created) VALUES ('later','test','later','later@example.invalid',1)")
                    modified = True
                return original_run(command, env=env, timeout=timeout)
            with patch.object(backup, "source_connection", connect), patch.object(backup, "run", run):
                archive, manifest_path, manifest = backup.create_backup(
                    f"postgresql://lusar_fixture:{password}@127.0.0.1:{port}/lusar_fixture", root / "archives",
                    tools=tools, age=age, recipient=recipient)
            assert modified and manifest["source"]["tables"]["customers"]["rows"] == 1
            result = backup.restore_locally(archive, manifest_path, tools=tools, age=age, identity=identity)
            assert result["restoreTested"] and result["restoreChecks"]["allTableHashesMatch"]
            assert result["restoreChecks"]["temporaryDataRemoved"]
            assert result["restoreChecks"]["tables"]["orders"] == 1
            assert not list((root / "archives").glob("*.dump"))
            with connect() as db:
                assert db.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 2
            # Corruption must be rejected before initializing any recovery database.
            archive.write_bytes(archive.read_bytes() + b"corruption")
            try:
                backup.restore_locally(archive, manifest_path, tools=tools, age=age, identity=identity)
            except backup.BackupError:
                pass
            else:
                raise AssertionError("Corrupt archive accepted")
            print("PASS: real PostgreSQL 18 snapshot export, encryption, independent restore, all row hashes/constraints, concurrent write isolation, corruption rejection and cleanup. Synthetic data only.")
        finally:
            backup.run([tools["pg_ctl"], "-D", data, "-w", "-m", "fast", "stop"])


if __name__ == "__main__":
    main()
