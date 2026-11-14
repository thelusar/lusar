"""Verify compressed public delivery without caching customer responses."""
import gzip
import http.client
import re
import tempfile
import threading
import unittest
from pathlib import Path

import serve


class QuietHandler(serve.Handler):
    def log_message(self, *args):
        pass


class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(dir=serve.ROOT, ignore_cleanup_errors=True)
        cls.previous_database = serve.DATABASE
        serve.DATABASE = Path(cls.temporary.name) / 'orders.sqlite'
        cls.server = serve.ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        serve.DATABASE = cls.previous_database
        cls.temporary.cleanup()

    def request(self, path, encoding='gzip', method='GET'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        connection.request(method, path, headers={'Accept-Encoding': encoding})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_compressed_home_is_identical_and_not_cached(self):
        code, headers, body = self.request('/')
        self.assertEqual(code, 200)
        self.assertEqual(headers['Content-Encoding'], 'gzip')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        source = (serve.ROOT / 'dist/index.html').read_bytes()
        self.assertEqual(gzip.decompress(body), source)
        self.assertLess(len(body), len(source) // 2)

    def test_versioned_assets_can_be_reused_between_pages(self):
        markup = (serve.ROOT / 'dist/index.html').read_text(encoding='utf-8')
        paths = re.findall(r'(?:src|href)="(/[^"<>]+\.(?:css|js)\?[^"<>]+)"', markup)
        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            with self.subTest(path=path):
                code, headers, body = self.request(path.replace('&amp;', '&'))
                self.assertEqual(code, 200)
                self.assertIn('immutable', headers['Cache-Control'])
                self.assertEqual(headers['Vary'], 'Accept-Encoding')
                original = (serve.ROOT / 'dist' / path.split('?')[0].lstrip('/')).read_bytes()
                self.assertEqual(gzip.decompress(body) if headers.get('Content-Encoding') == 'gzip' else body, original)

    def test_no_gzip_and_head(self):
        code, headers, body = self.request('/catalog', 'gzip;q=0, identity')
        self.assertEqual(code, 200)
        self.assertNotIn('Content-Encoding', headers)
        self.assertEqual(headers['Vary'], 'Accept-Encoding')
        self.assertEqual(body, (serve.ROOT / 'dist/catalog/index.html').read_bytes())
        code, headers, body = self.request('/catalog', method='HEAD')
        self.assertEqual(code, 200)
        self.assertEqual(headers['Content-Encoding'], 'gzip')
        self.assertEqual(body, b'')
        self.assertGreater(int(headers['Content-Length']), 0)

    def test_account_api_and_missing_assets_are_not_immutable(self):
        code, headers, body = self.request('/api/account/me')
        self.assertEqual(code, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        code, headers, body = self.request('/missing.js?asset=0123456789abcdef')
        self.assertEqual(code, 404)
        self.assertNotIn('immutable', headers['Cache-Control'])


if __name__ == '__main__':
    unittest.main()
