"""Owner-approved public business data; no catalogue or order configuration."""
import html
import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit

CONFIG = json.loads(Path(__file__).with_name('business.json').read_text(encoding='utf-8'))


def phone():
    return f'<a class="contact-phone" href="tel:{CONFIG["phone"]}">{CONFIG["phoneDisplay"]}</a>'


def contact(t):
    number = CONFIG['phone']
    email = CONFIG['email']
    return (phone() + f'<p><a href="mailto:{email}">{email}</a></p>' +
            '<p>' + t('Ежедневно', 'Ամեն օր', 'Daily') + ' · ' + CONFIG['hours'] + '</p>' +
            f'<div class="map-links"><a href="https://wa.me/{number[1:]}">WhatsApp</a>' +
            f'<a href="https://t.me/{number}">Telegram</a><span>Viber</span></div>')


def seller(t):
    return ('<p><span>' + t('Продавец', 'Վաճառող', 'Seller') + '</span>: ' + CONFIG['seller'] + ' · <span>' +
            t('Налоговый номер', 'ՀՎՀՀ', 'Tax ID') + '</span>: ' + CONFIG['taxId'] + '</p><address>' +
            t(*CONFIG['legalAddress']) + '</address>')


def maps(t):
    query = html.escape(urlencode({'api': 1, 'query': CONFIG['address'][2]}), quote=True)
    yandex = html.escape(urlencode({'text': CONFIG['address'][2]}), quote=True)
    return (f'<div class="map-links"><a href="https://www.google.com/maps/search/?{query}">Google Maps</a>'
            f'<a href="https://yandex.com/maps/?{yandex}">Yandex Maps</a></div>')


def socials(t):
    items = []
    for label, url in CONFIG['socialUrls'].items():
        if not url:
            continue
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError('Social URLs must be complete HTTPS addresses')
        items.append('<a class="social-link" href="' + html.escape(url, quote=True) + '">' +
                     '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/></svg>' + html.escape(label) + '</a>')
    return '<div class="map-links social-links">' + ''.join(items) + '</div>' if items else ''


def response_note(t):
    return '<p>' + t('Обычно отвечаем в течение 15 минут в рабочее время.',
                    'Աշխատանքային ժամերին սովորաբար պատասխանում ենք 15 րոպեի ընթացքում։',
                    'We usually reply within 15 minutes during opening hours.') + '</p>'
