"""Free Windows-only backup scheduling. No cloud upload or production writes."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / ".local-tools/backup-python"))
import backup_database as backup

DIRECTORY = WORKSPACE / ".lusar-backups"
TASK_NAME = "LUSAR-Encrypted-Database-Backup"


def protect(value, *, decrypt=False):
    """Windows CurrentUser DPAPI; never portable plaintext credentials."""
    if os.name != "nt":
        raise backup.BackupError("Local credential storage requires Windows DPAPI.")
    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]
    source = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
    blob = Blob(len(value), source)
    result = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(blob), None, None, None, None, 1, ctypes.byref(result)):
        raise backup.BackupError("Windows could not protect or unlock the local backup credential.")
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel.LocalFree(result.data)


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def hours_since(value, now=None):
    if not value:
        return float("inf")
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        raise backup.BackupError("Backup timestamps require a timezone.")
    age = ((now or datetime.now(timezone.utc)) - timestamp).total_seconds() / 3600
    if age < -1:
        raise backup.BackupError("Backup timestamp is in the future.")
    return max(0, age)


def register_task():
    # Names, paths and SID only. No password or connection string enters arguments.
    sid_text = backup.run(["whoami", "/user", "/fo", "csv", "/nh"]).decode(errors="replace")
    sid = re.search(r"S-1-5-[0-9-]+", sid_text)[0]
    env = os.environ.copy()
    env.update(LUSAR_BACKUP_PYTHON=str(Path(sys.executable).with_name("pythonw.exe")),
               LUSAR_BACKUP_SCRIPT=str(Path(__file__).resolve()), LUSAR_BACKUP_SID=sid)
    command = r'''
$ErrorActionPreference = 'Stop'
$taskName = 'LUSAR-Encrypted-Database-Backup'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and ($existing.Actions.Arguments -notlike ('*' + $env:LUSAR_BACKUP_SCRIPT + '*'))) { throw 'Task name belongs to another program.' }
$action = New-ScheduledTaskAction -Execute $env:LUSAR_BACKUP_PYTHON -Argument ('"' + $env:LUSAR_BACKUP_SCRIPT + '" run')
$daily = New-ScheduledTaskTrigger -Daily -At '09:00'
$login = New-ScheduledTaskTrigger -AtLogOn -User $env:LUSAR_BACKUP_SID
$principal = New-ScheduledTaskPrincipal -UserId $env:LUSAR_BACKUP_SID -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($daily,$login) -Principal $principal -Settings $settings -Description 'Encrypted local LUSAR database backup; requires this PC and signed-in Windows user; no cloud uploads.' -Force | Out-Null
$check = Get-ScheduledTask -TaskName $taskName
if ($check.State -eq 'Disabled' -or $check.Actions.Execute -ne $env:LUSAR_BACKUP_PYTHON) { throw 'Task verification failed.' }
'''
    backup.run(["pwsh.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command], env=env, timeout=60)


def enroll():
    from backup_windows import private_input
    directory = backup.private_directory(DIRECTORY)
    if not (directory / "recovery-identity.key").is_file():
        raise backup.BackupError("Complete the first encrypted backup before enabling the schedule.")
    url = private_input(heading="Подключение для ежедневной копии на этом ПК", action="Включить ежедневную копию")
    backup.connection_environment(url)
    protected = protect(url.encode("utf-8"))
    secret_path = directory / "connection.dpapi"
    secret_path.write_bytes(protected)
    url = None
    register_task()
    last = read_json(directory / "last-local-run.json", {})
    if last.get("state") == "restore_verified":
        manifest = read_json(Path(last["manifest"]))
        (directory / "last-restore.json").write_text(json.dumps({"createdUTC": manifest["restoredUTC"], "manifest": last["manifest"]}), encoding="utf-8")
        (directory / "last-success.json").write_text(json.dumps({"createdUTC": manifest["createdUTC"], "archive": last["archive"],
                                                               "manifest": last["manifest"], "sha256": manifest["sha256"]}), encoding="utf-8")
    (directory / "local-schedule.json").write_text(json.dumps({"task": TASK_NAME, "enabled": True, "time": "09:00 local time and next login",
        "requiresSignedInUser": True, "requiresPoweredPC": True, "credentialProtection": "Windows DPAPI CurrentUser", "cloudUploads": False}, indent=2), encoding="utf-8")


def prune(directory, *, days, keep=2):
    """Remove only our expired encrypted archive/manifest pairs inside this folder."""
    root = directory.resolve()
    allowed = DIRECTORY.resolve()
    if root.parent != allowed or root.name not in {"daily", "monthly"}:
        raise backup.BackupError("Retention is restricted to LUSAR's dedicated daily/monthly folders.")
    pairs = []
    for archive in root.glob("lusar-*.dump.age"):
        if not re.fullmatch(r"lusar-[0-9]{8}T[0-9]{12}Z\.dump\.age", archive.name):
            continue
        manifest_path = archive.with_suffix(".json")
        if archive.is_symlink() or manifest_path.is_symlink() or archive.resolve().parent != root:
            continue
        manifest = read_json(manifest_path, {})
        if manifest.get("archiveListValidated") and manifest.get("sha256") and manifest.get("encryption") == "age-X25519":
            pairs.append((manifest["createdUTC"], archive, manifest_path))
    for stamp, archive, manifest_path in sorted(pairs, reverse=True)[keep:]:
        if hours_since(stamp) > days * 24:
            archive.unlink()
            manifest_path.unlink()


def run_daily(*, force=False):
    directory = backup.private_directory(DIRECTORY)
    latest = read_json(directory / "last-success.json", {})
    if not force and hours_since(latest.get("createdUTC")) < 20:
        return {"state": "fresh", "backupAgeHours": round(hours_since(latest["createdUTC"]), 2)}
    secret_path = directory / "connection.dpapi"
    if not secret_path.is_file():
        raise backup.BackupError("Local automatic backup credentials have not been enrolled.")
    url = protect(secret_path.read_bytes(), decrypt=True).decode("utf-8")
    tools_root = WORKSPACE / ".local-tools"
    os.environ["LUSAR_BACKUP_CA_FILE"] = str(directory / "trusted-roots.pem")
    tools = backup.binaries(tools_root / "postgresql-18.7/pgsql/bin")
    age = tools_root / "age-1.3.2/age/age.exe"
    archive, manifest_path, manifest = backup.create_backup(url, directory / "daily", tools=tools, age=age,
                                                         recipient=(directory / "recipient.txt").read_text(encoding="utf-8").strip())
    url = None
    restored = read_json(directory / "last-restore.json", {})
    if hours_since(restored.get("createdUTC")) > 30 * 24:
        manifest = backup.restore_locally(archive, manifest_path, tools=tools, age=age, identity=directory / "recovery-identity.key")
        (directory / "last-restore.json").write_text(json.dumps({"createdUTC": manifest["restoredUTC"], "manifest": str(manifest_path)}), encoding="utf-8")
    latest = {"createdUTC": manifest["createdUTC"], "archive": str(archive), "manifest": str(manifest_path), "sha256": manifest["sha256"]}
    (directory / "last-success.json").write_text(json.dumps(latest, indent=2), encoding="utf-8")
    if datetime.now().day == 1:
        monthly = backup.private_directory(directory / "monthly")
        shutil.copy2(archive, monthly / archive.name)
        shutil.copy2(manifest_path, monthly / manifest_path.name)
    for name, days, keep in (("daily", 30, 2), ("monthly", 365, 1)):
        if (directory / name).is_dir():
            prune(directory / name, days=days, keep=keep)
    return {"state": "verified", "createdUTC": latest["createdUTC"], "archive": str(archive)}


def status():
    latest = read_json(DIRECTORY / "last-success.json", {})
    restore = read_json(DIRECTORY / "last-restore.json", {})
    return {"backupAgeHours": round(hours_since(latest["createdUTC"]), 2) if latest.get("createdUTC") else None,
            "backupFresh": hours_since(latest.get("createdUTC")) <= 30,
            "restoreFresh": hours_since(restore.get("createdUTC")) <= 35 * 24,
            "schedule": read_json(DIRECTORY / "local-schedule.json", {"enabled": False}),
            "lastError": read_json(DIRECTORY / "last-error.json"), "cloudUploads": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["enroll", "run", "prechange", "status"])
    args = parser.parse_args()
    try:
        if args.mode == "enroll":
            enroll()
            result = {"state": "schedule_enrolled"}
        elif args.mode == "status":
            result = status()
        else:
            result = run_daily(force=args.mode == "prechange")
        if args.mode != "status" and (DIRECTORY / "last-error.json").is_file():
            (DIRECTORY / "last-error.json").unlink()
        if sys.stdout:
            print(json.dumps(result, indent=2))
    except Exception as error:
        backup.private_directory(DIRECTORY)
        (DIRECTORY / "last-error.json").write_text(json.dumps({"createdUTC": datetime.now(timezone.utc).isoformat(),
            "state": "failed", "errorType": type(error).__name__}), encoding="utf-8")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("LUSAR — резервирование", "Автоматическая копия не подтверждена. Проверьте состояние резервирования LUSAR. Данные подключения не выводились.")
            root.destroy()
        except Exception:
            pass
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
