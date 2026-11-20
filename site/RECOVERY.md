# LUSAR data recovery and launch readiness

Checked in Render Dashboard on 20 November 2026 (Asia/Yerevan):

- Web service `lusar-staging`: Free, Oregon, branch `lusar-next`, health path `/healthz`.
- Database `lusar-integration`: PostgreSQL 18, Free, 1 GB, about 6.64% used.
- Dashboard warning: expiry **4 December 2026**. Do not treat any subsequent grace period as safe operating time.
- Recovery page explicitly says both PITR and exports are unavailable on Free.
- No actual backup or restore has been verified. Git contains code and a catalogue snapshot, **not** orders, accounts, sessions or staff history.
- External database access allows `0.0.0.0/0`. This still requires credentials and TLS. Restrict it to the operator's approved backup access after agreeing the access route; no network rules were changed during this audit.

## Required owner decision before the deadline

Approve a durable database plan or a migration destination, and an off-site backup location/retention policy. Upgrading the workspace alone does not upgrade the database. No paid plan has been changed by this work. A paid web instance is also required to remove Free cold starts; this is separate from preserving the database.

## Create a backup now, without changing source data

1. Use a trusted administrator workstation with PostgreSQL **18** client tools. Obtain the external database connection from Render and supply it as `DATABASE_URL` in the local process environment. Do not put it in Git, command arguments, screenshots, or chat.
2. Run `python site/backup_database.py`. It makes a consistent custom-format `pg_dump` export and verifies the archive catalogue with `pg_restore --list`. The default location is `.lusar-backups` beside, outside, the checkout. A SHA256 manifest distinguishes successful archives from partial exports. Errors suppress raw provider output to avoid leaking credentials.
3. Keep this directory private with restricted OS access and encrypted storage; backups contain customer data and session material. Copy successful archives to the owner's approved encrypted off-site storage. Do not upload to public file hosting or GitHub.
4. Make at least a daily backup and one immediately before database changes. Automation and retention need an owner-approved storage destination. This document does not mean automatic backups are configured.

## Prove recovery in isolation

1. Prepare a NEW, empty PostgreSQL 18 database, isolated from the production site and Telegram/AI workers. Do not restore into the current `lusar-integration` database.
2. Verify the archive SHA256 against its JSON manifest, then run `pg_restore --list <archive>`.
3. Supply the recovery database connection using standard `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGSSLMODE` environment variables. Run `pg_restore --no-owner --no-acl --exit-on-error --single-transaction --dbname <empty-database-name> <archive>`. Do not use `--clean` against production.
4. With read-only queries, compare table counts, migration versions, order numbers, totals and notification queue state against the source. Check constraints. Do not run notification workers on the restored database: an old queue can send duplicate notices.
5. Revoke restored customer sessions/login flows in the recovery copy before exposing it to users. Validate login, customer isolation, staff roles, order details and discounts with approved test accounts. Keep production untouched.
6. Record the archive ID, recovery database, time and verification results. Only a successful rehearsal justifies marking `restoreTested` true.

## Incident cutover (separate approval)

Stop accepting new writes or put the site into a controlled maintenance state. Take a final source backup if accessible. Reconcile orders/notifications after the backup timestamp, obtain approval to change `DATABASE_URL`, redeploy and verify `/healthz`, authentication, catalogue and staff access. Resume notification delivery only after pending notices are reconciled. Keep the original database for rollback; never delete it as part of an initial recovery attempt.

## Cold starts and monitoring

Render Free web instances sleep after 15 minutes without inbound traffic and may take roughly a minute to wake. Sleeping `/robots.txt` can be served by Render with `Disallow: /`. Persistent PostgreSQL quotas survive web process restarts. `/healthz` now performs a real database read and returns 503 when storage is unavailable; it also reports catalogue freshness and AI bot transport registration state. Transport registration is not a live Telegram delivery receipt. Monitor service availability, catalogue `synchronized`, notification failures and the backup age independently.

Official references checked 20 November 2026: [Free limits](https://render.com/docs/free), [backups and recovery](https://render.com/docs/postgresql-backups).
