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
            f'<a href="https://t.me/{number}">Telegram</a></div><p>' +
            t('Viber: добавьте номер магазина в контакты и откройте его в приложении. Telegram открывает контакт, если это разрешено настройками номера.',
              'Viber․ ավելացրեք խանութի համարը կոնտակտներում և բացեք հավելվածում։ Telegram-ը բացում է կոնտակտը, եթե համարի կարգավորումները թույլ են տալիս։',
              'Viber: save the store number to your contacts and open it in the app. Telegram can open the contact if the number’s privacy settings allow it.') + '</p>')


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
    return '<p>' + t('Обычно связываемся в течение 15 минут в рабочее время. Сложные и крупные заказы могут потребовать больше времени. Заявки вне рабочего времени обрабатываем после открытия магазина.',
                    'Աշխատանքային ժամերին սովորաբար կապվում ենք 15 րոպեի ընթացքում։ Բարդ և խոշոր պատվերները կարող են ավելի շատ ժամանակ պահանջել։ Ոչ աշխատանքային ժամերին ստացված հայտերը մշակում ենք խանութի բացվելուց հետո։',
                    'We usually contact you within 15 minutes during opening hours. Complex and large orders may take longer. Requests sent outside opening hours are handled when the store reopens.') + '</p>'
