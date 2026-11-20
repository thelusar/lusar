# LUSAR data recovery and launch readiness

## Verified state — 20 November 2026, Asia/Yerevan

- Production: `https://lusar.am`; Render web service `lusar-staging`, Free, Oregon, branch `lusar-next`, health path `/healthz`.
- Database `lusar-integration`: PostgreSQL 18, Free, 1 GB, approximately 6.64% used. Dashboard expiry: **4 December 2026**. Do not rely on any later grace period for normal operation.
- A **real production export**, encrypted with age-X25519, was created at 04:11 UTC. `pg_restore --list` succeeded; the encrypted archive is 25,691 bytes. Its SHA256 starts `fa19c71ce03121c7`; the full hash is in the private manifest.
- The actual archive was decrypted and restored into a fresh PostgreSQL 18 cluster bound exclusively to `127.0.0.1`. All 11 user tables, row counts, aggregate row hashes, migrations and validated constraints matched the same source snapshot. The cluster was stopped and temporary plaintext removed. A second verification completed at 04:21 UTC.
- No public recovery connection, application startup, Telegram notification worker or paid AI request was involved. Production was read-only during export. This is a storage recovery rehearsal; it does **not** claim a tested public application cutover.
- Protected directory **outside Git**: `C:\Users\Sova\Documents\ChatGPT\Lusar\.lusar-backups`. Archive: `lusar-20261120T041040036492Z.dump.age`; manifest: same stem ending `.dump.json`; private decryption identity: `recovery-identity.key`. NTFS access is restricted to the Windows user and SYSTEM. Never print or commit the identity or archive contents.
- The export excludes PostgreSQL cluster-global roles and external configuration. The owner is configured by `LUSAR_STAFF_ADMIN_ID` in Render; an empty `staff_roles` table does not mean the owner has been lost. Render/Auth0/Telegram/OpenAI secrets are not in this archive. Recovery also requires owner access to those accounts/configuration.

## Owner decisions

On 20 November the owner chose **manual copies on this PC only**: no paid upgrades, no cloud/Google Drive upload, no Windows scheduled task, no DPAPI-saved connection. None of these actions was performed. The connection was entered in a masked local window and was not saved. `site/backup_local.py` and `ops/backups` are opt-in preparations, not enabled infrastructure. No backup-age alarm, notification destination, cloud retention or periodic restore schedule is active. Existing manual archives are retained without automatic deletion.

This protects the captured snapshot but not later orders until another manual export. Loss of the PC can lose both archive and colocated key. Database expiry and web cold starts remain unresolved by the owner's decision.

## Make another manual copy on this prepared PC

1. In Render open `lusar-integration` → **Info** → **Connections** → **External Database URL** → **Copy**. Direct [database Info page](https://dashboard.render.com/d/dpg-dblhn46gekts738eq1q0-a/info). Never send the URL to chat.
2. Open `site/backup_windows.cmd`, or run from the checkout:

   ```powershell
   python site/backup_windows.py
   ```

3. In the masked local window click **Вставить**, then **Создать и проверить копию**. A read-only repeatable-read snapshot is exported, encrypted, checked and restored locally. External TLS verifies the certificate and hostname. The connection stays in process memory only.
4. Wait for success. `last-local-run.json` must say `restore_verified`. The new manifest must include `restoreTested: true`, matching hashes/constraints, `temporaryClusterStopped: true` and `temporaryDataRemoved: true`. File existence alone is not proof. A failed restore preserves an already completed encrypted archive but does not mark success.
5. Repeat before database changes and after important new orders until automation is approved. Retain the archive, manifest and identity; never put them in GitHub/public hosting.

PostgreSQL 18.7, age 1.3.2 and isolated Python dependencies are installed under `.local-tools` beside the checkout. Binaries matched official checksums. No global database service or PATH change was installed. A different PC needs trusted tools/dependencies and the securely transferred private identity; source code alone cannot decrypt this archive.

## Recheck an existing archive without production access

```powershell
python site/verify_backup_restore.py 'C:\Users\Sova\Documents\ChatGPT\Lusar\.lusar-backups\lusar-20261120T041040036492Z.dump.age'
```

The helper uses the matching manifest and local identity; it accepts no production restore URL. It initializes a temporary password-protected loopback cluster, checks encrypted/decrypted SHA256 and archive structure, restores with `--no-owner --no-acl --exit-on-error --single-transaction`, compares all user-schema table hashes/migrations/constraints, stops the cluster and removes plaintext. Only then does it record success. Rechecking an old archive does not create a fresh production backup.

## Durable option prepared, not purchased

The existing database supports an in-place upgrade retaining data and connection configuration. Minimum displayed compute: `0.1c-256mb`, **$6/month**. Keep the existing 1 GB allocation, **$0.30/month** storage: database baseline **$6.30/month**. This is a durability starting point, not a capacity guarantee for future traffic. Upgrading PostgreSQL can interrupt access for several minutes; first make and verify a fresh export. Do not create a replacement database or accidentally choose a larger default disk.

Minimum always-on web compute shown: `0.5c-512mb`, **$7/month**. Combined baseline: **$13.30/month**, before tax, overages, OpenAI, domain and account-specific integrations. No purchase was authorized; active `render.yaml` still specifies `plan: free`.

Paid PostgreSQL offers PITR: Hobby workspace 3 days, Pro+ 7 days. Generated Render logical exports retain 7 days. Free has neither. PITR does not replace independent archives. An optional separate Render backup Cron costs at least **$1/month**, plus any storage/monitoring; it was not created. See [opt-in backup design](../ops/backups/README.md).

Neon Free also has limits/scale-to-zero. Paid always-awake compute at 0.25 CU × 730 hours × $0.106/CU-hour plus 1 GB at $0.35 is approximately $19.70/month before recovery/other usage, so it is not an obvious saving over this Render upgrade. No alternative account or migration was created.

## Security and incident cutover

External access still permits `0.0.0.0/0`; credentials and TLS are required. Rules were not changed. Establish the operator's stable approved outbound IP/VPN and test that route before replacing this broad rule. Otherwise manual recovery can be locked out. Render private-network access is independent of external IP rules; a future approved in-region backup job can use it.

Production recovery/cutover needs separate approval. Stop writes or use maintenance mode, capture a final source backup if available, reconcile orders/notifications since the snapshot, and restore into a separately approved database. Revoke restored sessions/login flows before public access; verify login, customer isolation, staff permissions and order values with approved accounts. Approve `DATABASE_URL` changes and redeploy. Resume notifications only after reconciling old queues. Keep the source for rollback; never perform a destructive restore against the active database.

## Availability and checks

Free web sleeps after 15 idle minutes and may take roughly a minute to wake. Render may serve sleeping `/robots.txt` with `Disallow: /`. Paid web removes that sleep policy; artificial keep-alive traffic is not the durable solution. Webhook registration alone is not a Telegram delivery receipt. No real customer order or paid generation was made during this check.

`/healthz` already reads the database and returns 503 on storage failure, with catalogue and bot registration status. AI quotas remain persistent: shared 20 attempts/hour; Telegram 10 photo attempts/user/hour, 30 seconds apart. Provider failures count; unavailable quota storage fails closed. OpenAI currency budgets, Auth0 entitlements and domain renewal need account-specific review; the infrastructure baseline is not an all-inclusive operating bill.

```powershell
python -m unittest discover -s site -p 'test_*.py'
python -m unittest discover -s ops/backups -p 'test_*.py'
python site/check_backup_recovery.py
```

The native test uses synthetic data and temporary PostgreSQL 18 servers. It checks concurrent writes after snapshot export, encryption, restore hashes/constraints, corruption rejection and cleanup. Cloud tests use an in-memory storage double; no actual cloud upload or Docker build is claimed.

Official sources checked 20 November: [Free limits](https://render.com/docs/free), [backup retention](https://render.com/docs/postgresql-backups), [compute plans](https://render.com/docs/compute-plans), [connections/upgrades](https://render.com/docs/postgresql-creating-connecting), [storage pricing](https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses), [Cron](https://render.com/docs/cronjobs), [Neon pricing](https://neon.com/pricing), [Neon compute rate](https://neon.com/blog/major-compute-price-reduction-on-neon).
