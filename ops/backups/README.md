# Opt-in encrypted backup infrastructure — NOT ENABLED

The owner chose manual backups on the existing PC on 20 November 2026. No paid service, cloud bucket/upload, alert URL, Windows task or saved production credential was enabled. Real backup and isolated recovery evidence remain outside Git: see [RECOVERY.md](../../site/RECOVERY.md). Do not apply these examples as part of ordinary deployment.

## Manual workflow

Open `site/backup_windows.cmd` on the prepared PC. The masked window accepts Render's External Database URL; no URL enters arguments, chat, Git or saved credentials. The helper exports a read-only repeatable-read snapshot, encrypts with age, verifies SHA256/`pg_restore --list`, restores in a fresh PostgreSQL 18 loopback cluster, compares user-table hashes/migrations/constraints, stops it and removes plaintext. The key stays in the protected local folder. `site/verify_backup_restore.py` rechecks an existing archive without production access.

`site/backup_local.py` is prepared but **not enrolled**. Only explicit `enroll` displays a credential window, protects the connection with Windows CurrentUser DPAPI and registers the task. It requires an on/signed-in PC, not 24/7. If approved, it exports daily, validates archives, rehearses recovery monthly, retains daily copies 30 days/monthly copies 365 days, preserves newest copies, reports local status and displays local failure dialogs. It uploads nothing. Manual top-level archives are excluded from pruning. No actual scheduled run has been verified.

## Cloud design if separately approved

- `Dockerfile`: PostgreSQL 18, age, Python/psycopg/S3; non-root backup-only process. No web/Telegram/AI workers or private recovery identity. Docker is unavailable on this PC: image **not built or tested on Render**.
- `render-backups.example.yaml`: separate opt-in Cron every six hours UTC, exporting when last success is ≥20 hours old; freshness fails at 30 hours. At least $1/month needs approval. Active root Blueprint unchanged.
- Configure the **existing internal database URL**, same Render region/workspace, `LUSAR_BACKUP_NETWORK=render-private`. Internal self-signed TLS uses `sslmode=require`; public/manual connections always use `verify-full`. Private mode requires `RENDER=true` and a `dpg-…` internal hostname.
- Dedicated private bucket/token limited to `lusar/`, read/write only. No unrelated bucket/admin access, plaintext or connection-string objects. Private decryption identity stays outside Render/S3. Each encrypted upload is downloaded again and SHA256 checked before recording success.
- `retention.example.json` is a **human-readable proposal**, not a provider API payload. After approval configure native policies: daily 30 days, prechange 90, monthly 365; optional prefix locks 7/7/30 days. Exempt mutable `lusar/control/` from locks/expiry. Validate provider lifecycle/lock interactions before applying. Nothing is configured yet.
- Required: `DATABASE_URL`, public `LUSAR_BACKUP_RECIPIENT`, `LUSAR_BACKUP_S3_ENDPOINT`, `LUSAR_BACKUP_S3_BUCKET`, `LUSAR_BACKUP_ACCESS_KEY_ID`, `LUSAR_BACKUP_SECRET_ACCESS_KEY`. Credentials belong in protected service settings, never Git.
- Optional admin-owned HTTPS `LUSAR_BACKUP_HEARTBEAT_URL`/`LUSAR_BACKUP_ALERT_WEBHOOK` receive generic status only. Not configured; no messages sent. External heartbeat monitoring is needed to detect a Cron that never runs at all.

| Runner mode | Behavior |
| --- | --- |
| `scheduled` | Export if needed; verify backup age and independent recovery evidence; send configured status. |
| `backup` | Force daily export. |
| `prechange` | Additional archive under `lusar/prechange/`, without replacing daily checkpoint. Requires current recovery evidence. |
| `watch` | Check backup ≤30 hours and independent recovery ≤35 days; no export. |
| `seed --archive … --manifest …` | Explicit upload of an approved encrypted local archive and recovery proof. Currently **not authorized**. |
| `record-restore --manifest …` | Record completed local recovery evidence matching the remote manifest hash. |

Public recipient can encrypt; never give the server the private identity. Monthly, an approved operator downloads the archive/manifest to a protected PC, verifies hashes, runs `verify_backup_restore.py`, then records successful evidence. No monthly task or remote restore service is active. Editing a success flag is not a rehearsal.

## Cost and validation

Existing database: $6 compute + $0.30 for current 1 GB = $6.30/month. Always-on web: $7. Baseline $13.30/month; optional Cron adds at least $1, making $14.30 before storage, monitoring, AI, taxes and excess usage. These are options, not incurred charges. Paid Hobby PITR retains 3 days, Pro+ 7 days; generated logical exports 7 days. Free still expires 4 December.

R2 Standard includes a limited free allowance: 10 GB-month, 1 million Class A/10 million Class B requests per month, then usage charges. No billing/account/bucket activation is authorized. Healthchecks has a free tier; no check created. Pricing does not guarantee zero total costs. References: [Render Cron](https://render.com/docs/cronjobs), [S3 pattern](https://render.com/docs/backup-postgresql-to-s3), [R2 pricing](https://developers.cloudflare.com/r2/pricing/), [R2 locks](https://developers.cloudflare.com/r2/buckets/bucket-locks/), [Healthchecks](https://healthchecks.io/pricing/).

`python -m unittest discover -s ops/backups -p 'test_*.py'` checks in-memory readback, encrypted-only uploads, stale/future timestamps, missing/expired/mismatched recovery proof, success ordering and secret-safe errors. `python site/check_backup_recovery.py` exercises native PostgreSQL 18 with synthetic data. Windows DPAPI/retention/status tests are included in the site suite. None claims actual cloud upload, task enrollment, Docker build or public cutover.
