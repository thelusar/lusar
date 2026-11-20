"""No provider calls: quotas survive process replacement and concurrent callers."""
import importlib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import ai_limits
import lusar_ai
import order_storage
from ai_telegram import AIBot


class PersistentQuotaTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "test.sqlite"
        self.storage = patch.object(order_storage, "DATABASE_URL", "")
        self.storage.start()
        order_storage.initialize(self.path)
        ai_limits.configure(self.path)

    def tearDown(self):
        ai_limits.DATABASE = None
        self.storage.stop()
        self.directory.cleanup()

    def test_global_limit_is_atomic_and_survives_module_reload(self):
        with ThreadPoolExecutor(8) as pool:
            allowed = list(pool.map(lambda _: ai_limits.reserve("global", 20), range(30)))
        self.assertEqual(sum(allowed), 20)
        importlib.reload(ai_limits)
        ai_limits.configure(self.path)
        self.assertFalse(ai_limits.reserve("global", 20))

    def test_telegram_limits_survive_new_bot_and_expire(self):
        def bot():
            return AIBot("synthetic-token", "https://example.test", set(), public=True)
        with patch("ai_limits.time.time", return_value=10000) as clock:
            self.assertTrue(bot().photo_allowed(42))
            self.assertFalse(bot().photo_allowed(42))
            for index in range(1, 10):
                clock.return_value = 10000 + 30 * index
                self.assertTrue(bot().photo_allowed(42))
            clock.return_value = 10300
            self.assertFalse(bot().photo_allowed(42))
            self.assertTrue(bot().photo_allowed(43))
            clock.return_value = 13600
            self.assertTrue(bot().photo_allowed(42))
        with order_storage.connect(self.path) as db:
            scopes = [row[0] for row in db.execute("SELECT scope FROM ai_attempts")]
        self.assertTrue(all(scope.startswith("telegram:") and len(scope) == 73 for scope in scopes))

    def test_storage_failure_blocks_paid_request_and_releases_slot(self):
        ai_limits.configure(Path(self.directory.name) / "missing" / "database.sqlite")
        product = lusar_ai.catalog_data()["products"][0]["id"]
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic"}), \
                patch.object(lusar_ai, "render_room") as provider:
            for _ in range(3):
                with self.assertRaises(lusar_ai.AIError) as error:
                    lusar_ai.analyze(b"\xff\xd8\xfftest", "", product)
                self.assertEqual(error.exception.status, 503)
            provider.assert_not_called()

    def test_failed_provider_attempt_stays_charged(self):
        product = lusar_ai.catalog_data()["products"][0]["id"]
        with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic"}), \
                patch.object(lusar_ai, "render_room", side_effect=lusar_ai.AIError(502, "Simulated")):
            with self.assertRaises(lusar_ai.AIError):
                lusar_ai.analyze(b"\xff\xd8\xfftest", "", product)
        with order_storage.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM ai_attempts WHERE scope = 'global'").fetchone()[0], 1)

    def test_health_checks_storage_instead_of_configuration(self):
        self.assertTrue(order_storage.healthy(self.path))
        self.assertFalse(order_storage.healthy(self.path.parent / "absent.sqlite"))


if __name__ == "__main__":
    unittest.main()
