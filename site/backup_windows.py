"""Interactive local backup: credentials are entered here, never in chat or arguments."""
import json
import os
import ssl
import sys
from pathlib import Path

import backup_database as backup


def private_input(*, heading="Вставьте External Database URL из Render", action="Создать и проверить копию"):
    import tkinter as tk
    from urllib.parse import urlsplit
    root = tk.Tk()
    root.title("LUSAR — безопасное подключение к базе")
    root.geometry("720x270")
    root.configure(bg="#151515")
    root.attributes("-topmost", True)
    tk.Label(root, text=heading, fg="#f1eee8", bg="#151515", font=("Segoe UI", 15)).pack(pady=(22, 8))
    tk.Label(root, text="Строка останется на этом ПК. В чат и репозиторий она не передаётся.", fg="#bababa", bg="#151515", font=("Segoe UI", 10)).pack()
    entry = tk.Entry(root, show="*", width=70, font=("Segoe UI", 13))
    entry.pack(padx=24, pady=18, fill="x")
    status = tk.Label(root, text="Нажмите «Вставить» или Ctrl+V", fg="#d9bc86", bg="#151515", font=("Segoe UI", 11))
    status.pack()
    result = {}
    def paste():
        try:
            value = root.clipboard_get().strip()
        except tk.TclError:
            status.configure(text="Буфер пуст. Нажмите Copy у External Database URL в Render.")
            return
        entry.delete(0, tk.END)
        entry.insert(0, value)
        status.configure(text="Строка вставлена и скрыта звёздочками.")
    def accept(_=None):
        value = entry.get().strip()
        try:
            parsed = urlsplit(value)
            valid = parsed.scheme in {"postgres", "postgresql"} and parsed.hostname and parsed.username and parsed.password
        except ValueError:
            valid = False
        if not valid:
            status.configure(text="Нужна полная строка postgres://… или postgresql://… из Render.")
            return
        result["url"] = value
        entry.delete(0, tk.END)
        root.destroy()
    buttons = tk.Frame(root, bg="#151515")
    buttons.pack(pady=16)
    tk.Button(buttons, text="Вставить", command=paste, font=("Segoe UI", 12), padx=22).pack(side="left", padx=8)
    tk.Button(buttons, text=action, command=accept, font=("Segoe UI", 12), bg="#d3b681", padx=18).pack(side="left", padx=8)
    root.bind("<Return>", accept)
    entry.focus_set()
    root.mainloop()
    if "url" not in result:
        raise backup.BackupError("Private input cancelled; no database connection opened.")
    return result.pop("url")


def main():
    workspace = Path(__file__).resolve().parents[2]
    tools_root = workspace / ".local-tools"
    sys.path.insert(0, str(tools_root / "backup-python"))
    directory = backup.private_directory(workspace / ".lusar-backups")
    identity = directory / "recovery-identity.key"
    age = tools_root / "age-1.3.2/age/age.exe"
    keygen = age.with_name("age-keygen.exe")
    pg = tools_root / "postgresql-18.7/pgsql/bin"
    backup.binaries(pg)
    if not identity.exists():
        backup.run([keygen, "--output", identity])
    recipient = backup.run([keygen, "-y", identity]).decode().strip()
    recipient_file = directory / "recipient.txt"
    recipient_file.write_text(recipient, encoding="utf-8")
    ca_file = directory / "trusted-roots.pem"
    roots = ssl.create_default_context().get_ca_certs(binary_form=True)
    ca_file.write_text("".join(ssl.DER_cert_to_PEM_cert(cert) for cert in roots), encoding="ascii")
    os.environ["LUSAR_BACKUP_CA_FILE"] = str(ca_file)
    print("LUSAR: encrypted backup and isolated PostgreSQL 18 restore", flush=True)
    print("In Render open lusar-integration > Info > External Database URL > Copy.", flush=True)
    print("Paste the URL at the hidden prompt below and press Enter. Do not send it to chat.", flush=True)
    print("Only a read-only production export is performed. The recovery server is local, temporary and private.", flush=True)
    status_path = directory / "last-local-run.json"
    status_path.write_text(json.dumps({"state": "awaiting_private_input"}), encoding="utf-8")
    url = private_input()
    try:
        status_path.write_text(json.dumps({"state": "exporting"}), encoding="utf-8")
        archive, manifest_path, manifest = backup.create_backup(url.strip(), directory, tools=backup.binaries(pg), age=age, recipient=recipient)
        url = None
        status_path.write_text(json.dumps({"state": "archive_verified", "archive": str(archive), "manifest": str(manifest_path)}), encoding="utf-8")
        print("Encrypted archive created and checked. Verifying local recovery...", flush=True)
        manifest = backup.restore_locally(archive, manifest_path, tools=backup.binaries(pg), age=age, identity=identity)
        status_path.write_text(json.dumps({"state": "restore_verified", "archive": str(archive), "manifest": str(manifest_path),
                                          "bytes": manifest["bytes"], "sha256": manifest["sha256"], "checks": manifest["restoreChecks"]}, indent=2), encoding="utf-8")
        print("SUCCESS: encrypted backup and recovery verified. Temporary recovery server stopped and data removed.", flush=True)
        print("Backup folder: " + str(directory), flush=True)
        print("Keep recovery-identity.key private. An offline recovery key copy is needed for disaster recovery.", flush=True)
    except Exception as error:
        # Preserve an already created encrypted archive if recovery fails.
        previous = json.loads(status_path.read_text(encoding="utf-8"))
        previous.update(state="failed", step=previous["state"], errorType=type(error).__name__)
        status_path.write_text(json.dumps(previous, indent=2), encoding="utf-8")
        print("The operation did not complete. Private error details and credentials were not printed.", flush=True)
        if isinstance(error, backup.BackupError):
            print(str(error), flush=True)
        raise SystemExit(1) from None
    finally:
        url = None


if __name__ == "__main__":
    main()
