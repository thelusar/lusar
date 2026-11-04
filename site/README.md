# LUSAR storefront preview

Run from the repository root with Python 3.12:

```powershell
python site/build.py
python site/serve.py
```

Open `http://127.0.0.1:8080/`. The preview serves clean URLs, including the redirects from the existing catalog, and stores test orders in a local SQLite database outside the public directory.

For the local manager view, set `LUSAR_LOCAL_MANAGER_PASSWORD` before starting the server, then open `/manager/orders/` with username `manager`. Use test data only. The preview server and its shared manager login are local development tools.

```powershell
python site/check_checkout.py
```

The check uses Edge by default. Pass `--browser` with a Chrome executable path to run it in Chrome. It creates a temporary database and checks the storefront and manager flow at mobile width.

The build reads the public catalog snapshot in `storefront.json`. Refresh with `python site/sync_catalog.py`, or validate a previously fetched public export with `python site/sync_catalog.py --input <path>`, then rebuild.

Production requires hosting for the order service, manager authentication, storage and redirects. GitHub Pages can serve the static output only. Telegram delivery, analytics, customer accounts and Lusar AI require production configuration or implementation. Keep credentials and databases out of Git.

## Render staging

In Render, create a Blueprint from `thelusar/lusar` and select `lusar-next`. The root `render.yaml` defines a free test service. Open its generated Render URL and sign in as `manager` using the generated `LUSAR_STAGING_PASSWORD` from the service's Environment settings. Use synthetic orders only. The preview is password protected and excluded from indexing. Leave the production domain connected to the existing site.

## PostgreSQL preparation

`postgres/001_orders.sql` is the initial migration for the separate integration database. With `DATABASE_URL` set on Render, staging applies it at startup and stores orders, status history and queued notifications in PostgreSQL. Without the variable, staging uses temporary SQLite and its data is lost on restart. Keep the connection URL in Render's environment settings.

To enable Telegram notices on staging, add `LUSAR_TELEGRAM_BOT_TOKEN`, `LUSAR_TELEGRAM_CHAT_ID` (the negative ID of the private staff group), and `LUSAR_MANAGER_ORIGIN` (the HTTPS staging origin) in Render's Environment settings and redeploy. Add the bot to the group with permission to post. Once enabled, staging sends pending notices while the service is running. Each message contains the order number and a link to the protected manager page. Telegram failures are retried and a notice may repeat if Telegram accepts it before the delivery is recorded in the database.
