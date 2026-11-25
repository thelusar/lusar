"""Public business facts and retired URL regression checks; no live writes."""
import http.client
import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import business
import serve
from check_launch import Metadata


class BusinessPublicTests(unittest.TestCase):
    def test_public_pages_have_no_retired_contacts(self):
        retired = ('210/1', '11/3', '+37477123451', '+374 (77) 12-34-51', 'От LUYS+ к LUSAR')
        pages = list((serve.ROOT / 'dist').rglob('*.html'))
        self.assertGreater(len(pages), 50)
        for page in pages:
            text = page.read_text(encoding='utf-8')
            for value in retired:
                self.assertNotIn(value, text, str(page))

    def test_single_store_matches_owner_details(self):
        stores = []
        for page in (serve.ROOT / 'dist').rglob('*.html'):
            stores.extend(s for s in Metadata(page.read_text(encoding='utf-8')).schemas if s.get('@type') == 'Store')
        self.assertEqual(len(stores), 1)
        store = stores[0]
        self.assertEqual(store['telephone'], '+37498300990')
        self.assertEqual(store['legalName'], 'Luys+ LLC')
        self.assertEqual(store['taxID'], '02333832')
        self.assertIn('11/1', store['address']['streetAddress'])
        self.assertNotIn('sameAs', store)

    def test_empty_socials_and_future_url(self):
        translate = lambda ru, *args: ru
        self.assertTrue(all(url == '' for url in business.CONFIG['socialUrls'].values()))
        self.assertEqual(business.socials(translate), '')
        with patch.dict(business.CONFIG, socialUrls={'Instagram': 'https://example.com/profile'}):
            self.assertIn('href="https://example.com/profile"', business.socials(translate))
        for url in ('#', 'javascript:alert(1)', 'https://user:password@example.com'):
            with patch.dict(business.CONFIG, socialUrls={'Instagram': url}):
                with self.assertRaises(ValueError):
                    business.socials(translate)

    def test_retired_routes_redirect_without_indexing(self):
        class QuietHandler(serve.Handler):
            def log_message(self, *_):
                pass
        with serve.ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler) as server:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                for route, target in (('/stores/yerevan-arshakunyats', '/stores/yerevan-smbat-zoravar'), ('/about/founder', '/about')):
                    for suffix in ('', '/', '/index.html'):
                        connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
                        connection.request('HEAD', route + suffix)
                        response = connection.getresponse()
                        self.assertEqual(response.status, 301)
                        self.assertEqual(response.getheader('Location'), target)
                        connection.close()
                    self.assertNotIn('https://lusar.am' + route, (serve.ROOT / 'dist/sitemap.xml').read_text())
            finally:
                server.shutdown()


if __name__ == '__main__':
    unittest.main()
