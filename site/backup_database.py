"""Read-only PostgreSQL custom-format export, without secrets in command arguments.

Requires PostgreSQL 18 client tools and DATABASE_URL in this process environment.
Restore into a NEW empty database only; this program never restores or deletes data.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[2] / ".lusar-backups")
    args = parser.parse_args()
    tools = {name: shutil.which(name) for name in ("pg_dump", "pg_restore")}
    if not all(tools.values()):
        raise SystemExit("Install PostgreSQL 18 client tools (pg_dump and pg_restore) first.")
    version = subprocess.run([tools["pg_dump"], "--version"], capture_output=True, text=True, check=True).stdout.strip()
    if " 18." not in version:
        raise SystemExit("Use PostgreSQL 18 pg_dump for the current Render database.")
    try:
        env = connection_environment(os.environ.get("DATABASE_URL", ""))
    except ValueError as error:
        raise SystemExit(str(error)) from None
    directory = args.directory.resolve()
    repo = Path(__file__).resolve().parents[1]
    if directory == repo or repo in directory.parents:
        raise SystemExit("Choose a private backup directory OUTSIDE the Git repository.")
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    partial = directory / ("lusar-" + stamp + ".dump.partial")
    target = partial.with_suffix("")
    # Both stderr streams stay private: connection errors can include credentials.
    dump = subprocess.run([tools["pg_dump"], "--format=custom", "--no-owner", "--no-acl", "--no-password", "--file", str(partial)],
                          env=env, capture_output=True)
    if dump.returncode:
        raise SystemExit("Export failed. No complete backup was created. Check private connection settings and client compatibility.")
    verify = subprocess.run([tools["pg_restore"], "--list", str(partial)], capture_output=True)
    if verify.returncode or partial.stat().st_size == 0:
        raise SystemExit("Archive validation failed. Keep the partial file private; do not rely on it.")
    partial.rename(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {"createdUTC": stamp, "bytes": target.stat().st_size, "sha256": digest,
                "client": version, "archiveListValidated": True, "restoreTested": False}
    target.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Backup: {target}\nSHA256: {digest}\nArchive verified; a restore into a separate empty database is still required.")


if __name__ == "__main__":
    main()
