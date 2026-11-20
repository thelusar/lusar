# LUSAR storefront

Production: **https://lusar.am**, Render `lusar-staging`, branch `lusar-next`. Auth0, PostgreSQL and catalogue sync are active. The Render hostname remains password protected. On 20 November 2026 the live catalogue contained 61 products; `storefront.json` is a deterministic local test snapshot, not the current live inventory. A real encrypted production backup and isolated PostgreSQL 18 restore were verified on 20 November. See [RECOVERY.md](RECOVERY.md) for the evidence, manual backup instructions and the still-unresolved database expiry on 4 December. Paid upgrades, off-site storage and automatic scheduling were explicitly deferred by the owner.

Run from the repository root with Python 3.12:

```powershell
python site/build.py
python site/serve.py
```

Open `http://127.0.0.1:8080/`. The preview serves clean URLs, including the redirects from the existing catalog, and stores test orders in a local SQLite database outside the public directory.

For the local manager view without Auth0, set `LUSAR_LOCAL_MANAGER_PASSWORD` before starting the loopback preview, then open `/manager/orders/` with username `manager`. Use test data only.

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

The account pages use server-side customer sessions and Auth0 Universal Login for Google and email registration. Passwords never enter LUSAR. Production is configured; without provider configuration a separate preview displays an unavailable sign-in notice and guest checkout remains available. See [ACCOUNTS-SETUP.md](ACCOUNTS-SETUP.md) for recovery/setup reference.

`check_accounts.py` verifies signed identity claims, state/PKCE, CSRF, session revocation, customer isolation, first-order reservation, loyalty/returns, address ownership and optimistic shopping-state versions. `check_account_ui.py` exercises actual account pages and checkout in Chrome using a local signed identity provider, an isolated database and synthetic orders, including three widths, three languages and both themes. Neither test verifies delivery through real Google, Auth0 or email.

## Render staging

The existing Blueprint from `thelusar/lusar` deploys `lusar-next`; do not create a duplicate service. The root `render.yaml` defines the service. Its Render URL requires the preview password and remains noindexed. The configured exact production hostname `lusar.am` is public. See [DOMAIN-SETUP.md](DOMAIN-SETUP.md) for configuration and rollback reference; activation has already happened.

### Staff access

Before deploying the staff panel, sign in to the staging storefront as the intended owner, open `/api/account/me`, and put the value of `profile.id` in `LUSAR_STAFF_ADMIN_ID` in Render. The owner can open `/manager/orders/` and follow **Доступ сотрудников**. Ask each employee to sign in with their own Auth0 identity, open the order panel, and pass their account code to the owner. Assign **Менеджер** for orders or **Администратор** for orders and access management. Use the account code from the exact sign-in method the employee will use. Changing a role or revoking access applies to existing sessions. Only a Render administrator can change which account is the initial owner.

The shared staging password opens the test site. The order panel requires an individual account with a staff role. Changes to status, payment and returns appear in **Журнал заказа**, with the account that performed them. Earlier history remains in the database. Check access in separate browser sessions for a customer, manager and administrator before using the panel.

## Interactive homepage and editorial storefront

`hero.html`, `scenes.js` and `storefront.css` provide five independent light circuits over a room with a stone table and an Ararat view. Hotspots visibly select one or several circuits. The glass panel controls brightness, approximate temperature and group power. Morning, day and evening presets include artificial light; global power restores the previous scene, including circuits that were already off. Interaction is local and makes no AI requests.

The two aligned WebP room frames weigh about 187 KiB together. Masks isolate fixtures and light pools. This is an illustrative preview rather than a physical lighting calculation; the depicted fixtures are not linked to catalogue SKUs. The image coordinate plane remains uncropped on mobile. Controls appear once the illuminated frame loads, and motion respects reduced-motion preferences.

The glass lighting controls span the bottom of the hero. The curtain slider starts at 0% closed (fully open), with 100% fully closed. It moves a perspective-clipped fabric texture across the window and dims daylight independently of artificial light. Touch, keyboard, three languages and reduced motion are supported. No AI call is made by this interaction.

`editorial.json` contains 20 distinct Armenia-focused articles in Russian, Armenian and English. `editorial/` holds their 20 individual AI-generated WebP illustrations; each article identifies its illustration as generated. Articles have descriptions, canonical URLs, Article structured data, search entries and sitemap entries. `storefront_design.py` renders the journal, room planning pages, offers and footer. Full legal pages still need the operator's missing details before launch.

`photo-surfaces.json` stores measured edge colours for the current 46 catalogue photographs. The build continues these colours around contained images without changing or cropping the fixture. New photographs fall back to a neutral surface until their edge colours are added.

`Happy` is case-insensitive and gives a preliminary 10% birthday discount without a minimum spend. A staff member must confirm eligibility before recording payment. Confirmation is stored on the order and in its staff journal; no document image or date of birth is collected. Existing first-order, loyalty and single-code combination rules remain in effect.

Run `python site/build.py`, then `python site/check_hero.py` and `python site/check_storefront.py`. The latter verifies the journal, loading of all illustrations, 180 responsive language/theme states, AI actions within the desktop viewport, aggregate bag quantity and birthday confirmation/payment. `check_checkout.py`, `check_accounts.py`, `check_catalog.py`, `check_cart.py` and `check_ai.py` cover the existing flows. AI checks simulate the provider API and do not incur paid generation calls. Image prompts and output paths are saved in `visual-prompts.json`.

## PostgreSQL preparation

`postgres/001_orders.sql` is the initial migration for the separate integration database. `002_accounts.sql` adds customer records, sessions, shopping state and order ownership. `003_staff.sql` adds staff roles and the order audit trail. With `DATABASE_URL` set on Render, staging applies pending migrations at startup. Without the variable, staging uses temporary SQLite and its data is lost on restart. Keep the connection URL in Render's environment settings.

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

Lusar AI uses the active published catalogue for photo recommendations and room mockups with up to two product references. The public website and `LusarAiBot` share 20 AI attempts per rolling hour. Telegram allows 10 photo attempts per rolling hour per user, 30 seconds apart. Render stores these quotas in PostgreSQL (`005_ai_attempts.sql`) so restarts do not reset them. Attempts are charged before provider access, including failures. Quota storage failure blocks generation. These limits bound attempts, not currency spending; OpenAI project budgets/model pricing still need owner review. Local simulated previews retain in-memory fallback only when persistent storage is not configured.

Run `python -m unittest discover -s site -p 'test_*.py'` for host routing, health, public bot, persistent quotas and backup connection handling. `python site/check_launch.py` verifies indexable metadata/schema/internal links and 108 layout states for the completed launch pages. No paid AI requests or real customer orders are made by these checks.
