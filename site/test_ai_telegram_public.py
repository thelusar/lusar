import os
import unittest
from unittest.mock import MagicMock, patch

from ai_telegram import AIBot, WEBHOOK, start_bot


class PublicBotTests(unittest.TestCase):
    def bot(self, public=True):
        bot = AIBot('123:synthetic', 'https://preview.example', set(),
                    public=public, website_origin='https://lusar.am')
        bot.send = MagicMock()
        bot.request = MagicMock(return_value={'file_path': 'photos/room.jpg'})
        return bot

    def update(self, text=None, photo=False, kind='private', user=42):
        message = {'chat': {'type': kind, 'id': user}}
        if text:
            message['text'] = text
        if photo:
            message['photo'] = [{'file_id': 'photo', 'file_size': 20}]
        return {'update_id': 1, 'message': message}

    def test_new_client_can_start_public_bot(self):
        bot = self.bot()
        bot.process(self.update('/start'))
        self.assertIn('Пришлите фото', bot.send.call_args.args[1])
        self.assertNotIn('тестируется', bot.send.call_args.args[1])

    def test_private_default_denies_new_client_and_empty_allowlist(self):
        bot = self.bot(False)
        with patch('ai_telegram.analyze') as analyze:
            bot.process(self.update(photo=True))
            analyze.assert_not_called()
        bot.request.assert_not_called()
        bot.process(self.update('/start'))
        self.assertIn('тестируется', bot.send.call_args.args[1])

    def test_groups_never_process_photos(self):
        bot = self.bot()
        bot.process(self.update(photo=True, kind='group'))
        bot.request.assert_not_called()
        bot.send.assert_not_called()

    def test_public_photo_uses_main_domain_links_and_blocks_repeat_before_download(self):
        bot = self.bot()
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'photo'
        answer = {'advice': 'Advice', 'products': [{'name': 'Lamp', 'sku': '123',
                  'reason': 'Reason', 'path': '/catalog/product/lamp', 'inMockup': False}]}
        with patch('ai_telegram.urlopen', return_value=response) as download, \
                patch('ai_telegram.analyze', return_value=answer) as analyze:
            bot.process(self.update(photo=True))
            self.assertIn('https://lusar.am/catalog/product/lamp', bot.send.call_args.args[1])
            bot.process(self.update(photo=True))
            self.assertEqual(analyze.call_count, 1)
            self.assertEqual(download.call_count, 1)
            self.assertEqual(bot.request.call_count, 1)
        self.assertIn('трёх примерок', bot.send.call_args.args[1])

    def test_hour_limit_and_expiry_and_independent_clients(self):
        bot = self.bot()
        with patch('ai_telegram.monotonic', side_effect=[0, 30, 60, 90, 90, 3601]):
            self.assertTrue(bot.photo_allowed(42))
            self.assertTrue(bot.photo_allowed(42))
            self.assertTrue(bot.photo_allowed(42))
            self.assertFalse(bot.photo_allowed(42))
            self.assertTrue(bot.photo_allowed(43))
            self.assertTrue(bot.photo_allowed(42))

    def test_configuration_is_explicit_and_webhook_stays_on_render(self):
        env = {'LUSAR_AI_TELEGRAM_BOT_TOKEN': '123:synthetic',
               'RENDER_EXTERNAL_URL': 'https://preview.example', 'LUSAR_PUBLIC_ORIGIN': 'https://lusar.am'}
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(start_bot().public)
            os.environ['LUSAR_AI_TELEGRAM_ACCESS'] = 'public'
            bot = start_bot()
            self.assertTrue(bot.public)
            bot.request = MagicMock(return_value={})
            self.assertEqual(bot.connect(), 'webhook')
            self.assertEqual(bot.request.call_args.args[1]['url'], 'https://preview.example' + WEBHOOK)
            os.environ['LUSAR_AI_TELEGRAM_ACCESS'] = 'typo'
            self.assertIsNone(start_bot())

    def test_duplicate_update_is_queued_once(self):
        bot = self.bot()
        update = self.update(photo=True)
        self.assertTrue(bot.enqueue(update))
        self.assertTrue(bot.enqueue(update))
        self.assertEqual(bot.pending.qsize(), 1)


if __name__ == '__main__':
    unittest.main()
