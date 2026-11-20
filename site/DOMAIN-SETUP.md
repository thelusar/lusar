# Main domain activation

Status checked 20 November 2026: `lusar.am` is public, `www` redirects to it, certificates are issued, and Render deploys `lusar-next`. The numbered procedure below is a recovery reference, not pending DNS work. Do not repeat it on a working production domain.

The Render service continues to deploy `lusar-next`. Adding domains does not change DNS.

1. Add `lusar.am` in Render Custom Domains. Render also adds `www.lusar.am`, redirecting to the root domain.
2. Auth0 application URL allowlists must retain preview URLs and add:
   - Callback: `https://lusar.am/auth/callback`
   - Logout: `https://lusar.am/account/sign-in`
   - Web origin: `https://lusar.am`
3. Set Render `LUSAR_PUBLIC_ORIGIN=https://lusar.am` and `LUSAR_SITE_MODE=production`, then redeploy. Existing Auth0 settings, PostgreSQL, staff administrator and preview password remain required.
4. In Cloudflare replace the four GitHub Pages root A records with one DNS-only CNAME: `@` → `lusar-staging.onrender.com`. Change existing `www` CNAME to the same target. Preserve unrelated DNS records. Verify both domains and certificates in Render.
5. Check HTTPS, catalog, sign-in/return, guest checkout, staff access restrictions and AI origin validation. Check analytics with consent on the main domain.

Only the exact configured public hostname skips the preview password. The Render hostname stays password protected and noindexed. Staff/customer authentication remains mandatory. Private pages remain noindexed. No forwarded host header is trusted. A new hostname requires signing in again because cookies are host scoped.

Keep the Render subdomain enabled: Telegram webhooks currently use its URL and their own webhook secret. Moving those webhooks is separate from activating the website domain.

Public AI access was enabled on 15 November using `LUSAR_AI_TELEGRAM_ACCESS=public`. Default `private` retains the tester allowlist; an empty allowlist does not open access. Product links use `LUSAR_PUBLIC_ORIGIN`, while the webhook stays on `RENDER_EXTERNAL_URL`. Only private chats are processed. Limits: ten photo attempts/hour/user, 30 seconds apart, plus 20 shared AI attempts/hour and a bounded queue. After migration `005_ai_attempts.sql`, PostgreSQL preserves both quotas across process restarts. These are not a currency billing cap. Order notifications remain in the configured private staff chat. Rollback access: set it to `private`.

Rollback DNS to the four A addresses `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`, with `www` CNAME `thelusar.github.io`. Setting `LUSAR_SITE_MODE=staging` restores the preview gate on every hostname after redeploy.
