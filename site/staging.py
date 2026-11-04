"""Password-gated test deployment. Accept synthetic data only."""
import base64
import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory

import serve


class StagingHandler(serve.Handler):
    def end_headers(self):
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def staging_authorized(self):
        if secrets.compare_digest(self.headers.get("Authorization", "").encode(), self.staging_auth):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="LUSAR staging"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self):
        if self.path == "/healthz":
            return self.reply(200, {"ok": True})
        if self.staging_authorized():
            super().do_GET()

    def do_HEAD(self):
        if self.staging_authorized():
            super().do_HEAD()

    def do_POST(self):
        if self.staging_authorized():
            super().do_POST()


def main():
    password = os.environ.get("LUSAR_STAGING_PASSWORD", "")
    if len(password) < 24:
        raise SystemExit("Set LUSAR_STAGING_PASSWORD to a generated secret of at least 24 characters.")
    os.environ["LUSAR_LOCAL_MANAGER_PASSWORD"] = password
    StagingHandler.staging_auth = b"Basic " + base64.b64encode(f"manager:{password}".encode())
    with TemporaryDirectory(prefix="lusar-staging-") as directory:
        serve.DATABASE = Path(directory) / "orders.sqlite"
        with serve.ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), StagingHandler) as server:
            server.serve_forever()


if __name__ == "__main__":
    main()
