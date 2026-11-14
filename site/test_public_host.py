"""Verify public-host routing without external services or customer data."""
import base64
import http.client
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import serve
import staging


class PublicHostTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            'LUSAR_AUTH0_DOMAIN': 'test.example', 'LUSAR_AUTH0_CLIENT_ID': 'test-client',
            'LUSAR_AUTH0_CLIENT_SECRET': 'synthetic-test-secret', 'LUSAR_PUBLIC_ORIGIN': 'https://lusar.am',
        }, clear=True)
        self.environment.start()
        self.directory = tempfile.TemporaryDirectory()
        self.database = patch.object(serve, 'DATABASE', Path(self.directory.name) / 'orders.sqlite')
        self.database.start()
        staging.StagingHandler.staging_auth = b'Basic ' + base64.b64encode(b'manager:test-preview-password')
        self.server = serve.ThreadingHTTPServer(('127.0.0.1', 0), staging.StagingHandler)
        self.server.public_origin = 'https://lusar.am'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.database.stop()
        self.directory.cleanup()
        self.environment.stop()

    def request(self, path='/', host='lusar.am', method='GET', **headers):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request(method, path, headers={'Host': host, **headers})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_public_storefront_is_accessible_and_indexable(self):
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertNotIn('X-Robots-Tag', headers)
        self.assertIn(b'LUSAR', body)

    def test_preview_and_unknown_hosts_still_require_password(self):
        for host in ['lusar-staging.onrender.com', 'other.example', 'lusar.am.evil.example', 'lusar.am:1234']:
            with self.subTest(host=host):
                status, headers, _ = self.request(host=host)
                self.assertEqual(status, 401)
                self.assertIn('noindex', headers['X-Robots-Tag'])
        status, _, _ = self.request(host='lusar-staging.onrender.com', Authorization=staging.StagingHandler.staging_auth.decode())
        self.assertEqual(status, 200)

    def test_default_mode_keeps_every_host_password_gated(self):
        self.server.public_origin = staging.public_origin()
        self.assertEqual(self.request()[0], 401)

    def test_private_pages_keep_noindex_and_staff_requires_login(self):
        status, headers, body = self.request('/manager/orders/')
        self.assertEqual(status, 401)
        self.assertIn('noindex', headers['X-Robots-Tag'])
        self.assertIn(b'/auth/start', body)
        self.assertEqual(self.request('/manager/orders/status', method='POST')[0], 403)
        self.assertEqual(self.request('/api/account/orders')[0], 401)

    def test_ai_rejects_foreign_origin_before_using_provider(self):
        self.assertEqual(self.request('/api/ai', method='POST', Origin='https://other.example')[0], 403)
        # A same-origin request reaches validation, without contacting OpenAI.
        self.assertEqual(self.request('/api/ai', method='POST', Origin='https://lusar.am')[0], 400)

    def test_head_follows_same_host_gate(self):
        self.assertEqual(self.request(method='HEAD')[0], 200)
        self.assertEqual(self.request(host='lusar-staging.onrender.com', method='HEAD')[0], 401)

    def test_production_fails_closed_without_required_configuration(self):
        with patch.dict(os.environ, {'LUSAR_SITE_MODE': 'production'}):
            with self.assertRaises(SystemExit):
                staging.public_origin()
        with patch.dict(os.environ, {'LUSAR_SITE_MODE': 'typo'}):
            with self.assertRaises(SystemExit):
                staging.public_origin()


if __name__ == '__main__':
    unittest.main()
