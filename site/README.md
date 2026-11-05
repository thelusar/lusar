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
python site/check_catalog.py
python site/check_cart.py
python site/check_catalog_sync.py
python site/check_accounts.py
python site/check_account_ui.py
```

The check uses Edge by default. Pass `--browser` with a Chrome executable path to run it in Chrome. It creates a temporary database and checks the storefront and manager flow at mobile width.

The catalog check exercises combined search and filters, filter URLs, quick add and wishlist persistence, photo navigation and zoom, and responsive layouts in all interface languages. It uses the local snapshot and makes no AI requests.

The cart check covers quantity editing, fixed and percentage promo calculations, optional contacts, retry idempotency, duplicate prevention, receipt rendering and preserving newly added items during submission. Its order API is simulated; the checkout check verifies saving an order in an isolated local database and the manager workflow.

For the plain local preview, the build reads `storefront.json`. Refresh it with `python site/sync_catalog.py`, or validate an exported public catalog with `python site/sync_catalog.py --input <path>`, then rebuild. These manual commands are not needed for runtime updates on Render.

## Automatic public catalog on Render

`staging.py` reads the panel's public `/api/storefront` feed at startup and every 30 seconds while the service is running. The free Render service sleeps when inactive; polling resumes when it wakes. No panel credentials or new environment variables are required.

A changed, validated export is built in a separate temporary directory. Only a successful build becomes active. Catalog, category, product, brand, search and public product data update together; existing requests retain their generation. Generated data scripts are versioned to match the page that requested them. Empty published catalogs are valid, so taking the last product out of publication removes it from the website too. Invalid exports, source failures and build failures preserve the last working generation.

Open catalog pages check the same-origin `/api/catalog` on entry, focus and every 30 seconds while visible. A new revision reloads catalog pages and preserves filters in the URL. Cart and checkout update their product data and totals in place, preserving contacts. Customer photo and support forms are excluded from automatic reloads. Lusar AI reads the active server catalog.

Every new order checks the public feed again, compares the displayed prices and rejects unpublished items or changed prices. If the feed cannot be checked, new orders return a retryable error; an identical retry of an already saved request still returns its original number. Existing saved orders keep the names, prices and quantities accepted at submission.

`/healthz` includes `catalog.revision`, `products`, `lastChecked`, `lastSuccess` and `synchronized`. A healthy web process with `synchronized: false` is serving its last working catalog and cannot confirm new orders until the feed recovers.

`check_catalog_sync.py` uses an isolated feed and database to verify updates, removal of all published products, malformed exports, failed builds, old-price rejection, saved-order stability and browser refresh without losing contacts. It does not edit the panel or send real customer notifications.

Production requires hosting for the order service, manager authentication, storage and redirects. GitHub Pages can serve the static output only. Telegram delivery, analytics, customer accounts and Lusar AI require production configuration. Keep credentials and databases out of Git.

## Customer accounts

The account pages use server-side customer sessions and Auth0 Universal Login for Google and email registration. Passwords never enter LUSAR. Without provider configuration the pages display an unavailable sign-in notice; guest checkout remains available. See [ACCOUNTS-SETUP.md](ACCOUNTS-SETUP.md) for exact callback URLs, Google connection, mail provider, Render variables, ownership and activation checks. The external provider is not activated by this code change.

`check_accounts.py` verifies signed identity claims, state/PKCE, CSRF, session revocation, customer isolation, first-order reservation, loyalty/returns, address ownership and optimistic shopping-state versions. `check_account_ui.py` exercises actual account pages and checkout in Chrome using a local signed identity provider, an isolated database and synthetic orders, including three widths, three languages and both themes. Neither test verifies delivery through real Google, Auth0 or email.

## Render staging

In Render, create a Blueprint from `thelusar/lusar` and select `lusar-next`. The root `render.yaml` defines a free test service. Open its generated Render URL and sign in as `manager` using the generated `LUSAR_STAGING_PASSWORD` from the service's Environment settings. Use synthetic orders only. The preview is password protected and excluded from indexing. Leave the production domain connected to the existing site.

## PostgreSQL preparation

`postgres/001_orders.sql` is the initial migration for the separate integration database; `002_accounts.sql` adds customer records, sessions, shopping state and order ownership. With `DATABASE_URL` set on Render, staging applies pending migrations at startup. Without the variable, staging uses temporary SQLite and its data is lost on restart. Keep the connection URL in Render's environment settings.

To enable Telegram notices on staging, add `LUSAR_TELEGRAM_BOT_TOKEN`, `LUSAR_TELEGRAM_CHAT_ID` (the negative ID of the private staff group), and `LUSAR_MANAGER_ORIGIN` (the HTTPS staging origin) in Render's Environment settings and redeploy. Add the bot to the group with permission to post. Once enabled, staging sends pending notices while the service is running. Each message contains the order number and a link to the protected manager page. Telegram failures are retried and a notice may repeat if Telegram accepts it before the delivery is recorded in the database.

## Staging analytics and Lusar AI

Add these values in Render's Environment settings and select **Save, rebuild, and deploy**:

| Variable | Value |
| --- | --- |
| `LUSAR_GA4_ID` | Measurement ID for the staging GA4 web stream (`G-…`). Turn off enhanced measurement in the test stream to check the explicit storefront events. |
| `LUSAR_YANDEX_METRICA_ID` | Numeric ID for a separate staging counter. Leave session replay and form analysis off. |
| `OPENAI_API_KEY` | Secret key for the OpenAI API project. Verify API billing and model access in that project. |
| `LUSAR_AI_TELEGRAM_BOT_TOKEN` | Token for the separate Lusar AI bot. |
| `LUSAR_AI_TELEGRAM_USERNAME` | Public username of the AI bot, without `@`. Enables a link from the Lusar AI page. |
| `LUSAR_AI_TELEGRAM_USER_IDS` | Comma-separated IDs of the Telegram accounts allowed to test photo recommendations. Start the AI bot to see your own ID. |

Analytics providers start after the visitor allows statistics. The storefront sends page views and `view_item`, `add_to_cart`, `begin_checkout`, and `generate_lead`. Configure the same event names as JavaScript goals in Metrica. View visits and events in GA4 Realtime and use Metrica's tag debugger to confirm goals.

The password-protected Lusar AI page uses the published catalog snapshot for photo recommendations and produces a room mockup using photos of up to two selected products as references. The product card opens mockup mode for that product. The Telegram bot registers its webhook on Render and sends both the room mockup and the catalog links. The preview shares a limit of 20 AI requests per hour per running instance. Keep this preview for invited testers and synthetic or test photos.
