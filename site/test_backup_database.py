import unittest
from backup_database import connection_environment


class BackupConnectionTests(unittest.TestCase):
    def test_credentials_use_environment_and_encrypted_connection(self):
        env = connection_environment("postgresql://user:p%40ss@db.example:5432/lusar?sslmode=require")
        self.assertEqual(env["PGPASSWORD"], "p@ss")
        self.assertEqual(env["PGDATABASE"], "lusar")
        self.assertEqual(env["PGHOST"], "db.example")
        self.assertEqual(env["PGSSLMODE"], "require")
        self.assertNotIn("DATABASE_URL", env)

    def test_unencrypted_and_invalid_connection_rejected(self):
        for value in ("", "https://example.test", "postgres://u:p@host/db?sslmode=disable"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                connection_environment(value)


if __name__ == "__main__":
    unittest.main()
