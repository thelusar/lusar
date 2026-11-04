"""Build the LUSAR navigation preview from the public storefront snapshot."""
import html
import json
import re
from pathlib import Path
from urllib.parse import quote, urlencode
from xml.etree import ElementTree
from loyalty import FIRST_ORDER_PERCENT, LOYALTY_TIERS
from sync_catalog import validate

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist"
PUBLIC_ORIGIN = "https://lusar.am"
SERVICE_HOURS = "09:30–19:00"
indexable = []
data = json.loads((ROOT.parent / "storefront.json").read_text(encoding="utf-8-sig"))
validate(data)
categories = {item["id"]: item for item in data["categories"]}
brands = {}
brand_registry = json.loads((ROOT / "brands.json").read_text(encoding="utf-8"))
brand_ids = {}
brand_paths = set()
for brand_id, entry in brand_registry.items():
    if len(brand_id) != 16 or any(character not in "0123456789abcdef" for character in brand_id):
        raise ValueError(f"Invalid permanent brand ID: {brand_id}")
    path = entry["path"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", path) or path in brand_paths or path in brand_registry:
        raise ValueError(f"Invalid or conflicting public brand path: {path}")
    brand_paths.add(path)
    for alias in [entry["name"], *entry["aliases"]]:
        key = alias.strip().casefold()
        previous = brand_ids.setdefault(key, brand_id)
        if not key or previous != brand_id:
            raise ValueError(f"Conflicting brand alias: {alias}")
product_brand_ids = {}
for item in data["products"]:
    brand = item["brand"].strip()
    if brand:
        brand_id = brand_ids.get(brand.casefold())
        if brand_id:
            product_brand_ids[item["id"]] = brand_id
            brands.setdefault(brand_id, {"name": brand_registry[brand_id]["name"], "products": []})["products"].append(item)

def link(path, title):
    return f'<a href="/{path.strip("/")}">{html.escape(title)}</a>'

def write(path, title, body, draft=False, *, description="", image="", structured_data=None):
    target = OUT / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    robots = '<meta name="robots" content="noindex">' if draft else ""
    canonical = ""
    if not draft:
        url = PUBLIC_ORIGIN + "/" + path.strip("/")
        canonical = f'<link rel="canonical" href="{html.escape(url, quote=True)}">'
        indexable.append(url)
    metadata = ""
    if description:
        escaped = html.escape(description, quote=True)
        metadata += f'<meta name="description" content="{escaped}"><meta property="og:description" content="{escaped}">'
    if image and not draft:
        metadata += (f'<meta property="og:type" content="website"><meta property="og:url" content="{html.escape(url, quote=True)}">'
                     f'<meta property="og:title" content="{html.escape(title, quote=True)}">'
                     f'<meta property="og:image" content="{html.escape(image, quote=True)}">')
    if structured_data and not draft:
        serialized = json.dumps(structured_data, ensure_ascii=False).replace("<", "\\u003c")
        metadata += f'<script type="application/ld+json">{serialized}</script>'
    target.write_text(f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{robots}{canonical}{metadata}<title>{html.escape(title)} — LUSAR</title><script src="/theme.js"></script><link rel="stylesheet" href="/site.css"></head>
<body><a class="skip-link" href="#main">К содержанию</a><header>{link("", "LUSAR")}<nav aria-label="Основная навигация">{link("catalog/", "Каталог")} {link("ai/", "Lusar AI")} {link("search", "Поиск")} {link("compare", "Сравнение")}
{link("favorites/", "Избранное")} {link("cart/", "Корзина")} {link("account/", "Кабинет")}</nav>
<button id="theme-toggle" type="button" aria-pressed="false" hidden>Светлая тема</button></header>
<main id="main" tabindex="-1"{' class="home"' if not path else ''}>{f"<h1>{html.escape(title)}</h1>" if path else ""}{body}</main>
<footer>{' '.join(link(path + "/", name) for path, name in FOOTER)}
<button type="button" id="cookie-settings" hidden>Настройки cookie</button></footer>
<section id="cookie-panel" class="cookie-panel" aria-labelledby="cookie-heading" hidden>
  <h2 id="cookie-heading" tabindex="-1">Настройки cookie</h2>
  <p>Браузер хранит настройки сайта и корзину. Сбор статистики можно разрешить или отключить отдельно.</p>
  <p>{link("legal/cookies", "Подробнее о cookie")}</p>
  <button type="button" data-cookie-choice="essential">Только необходимые</button>
  <button type="button" data-cookie-choice="analytics">Разрешить статистику</button>
  <p id="cookie-status" role="status"></p>
</section>
{'<dialog id="first-order-promo" aria-labelledby="promo-heading"><h2 id="promo-heading">10% на первый заказ</h2><p>Зарегистрируйтесь и получите скидку на первую покупку.</p><p>' + link("offers/", "Посмотреть условия") + '</p><form method="dialog"><button>Закрыть</button></form></dialog>' if path.rstrip("/") == "catalog" or path.startswith("catalog/product/") else ""}
<script src="/analytics.js" defer></script><script src="/cart.js" defer></script><script src="/cookie-settings.js" defer></script></body></html>""", encoding="utf-8")

FOOTER = [
    ("contacts", "Контакты"), ("about", "О нас"), ("brands", "Бренды"),
    ("partners", "Наши партнёры"), ("journal", "Статьи"), ("news", "Новости"),
    ("offers", "Акции"), ("delivery", "Доставка"), ("payment", "Оплата"),
    ("returns", "Гарантия и возврат"), ("faq", "FAQ"), ("support", "Поддержка"),
    ("legal", "Правовая информация"), ("sitemap", "Карта сайта"),
]
EXTRA = [
    ("rooms", "Подобрать по комнате"), ("ai", "Lusar AI"), ("favorites", "Избранное"),
    ("cart", "Корзина"), ("checkout", "Оформление заявки"), ("checkout/received", "Подтверждение заявки"),
    ("account", "Личный кабинет"), ("account/orders", "Заказы"), ("account/addresses", "Адреса"),
    ("account/projects", "Мои проекты"), ("account/loyalty", "Скидки и промокоды"),
    ("account/settings", "Настройки аккаунта"), ("account/notifications", "Уведомления"),
    ("account/sign-in", "Вход"), ("account/register", "Регистрация"),
    ("account/recovery", "Восстановление доступа"), ("order-status", "Статус заявки"),
    ("about/founder", "David Matevosyan"), ("stores", "Магазины"),
    ("projects", "Реализованные проекты"), ("professionals", "Дизайнерам и бизнесу"),
    ("professionals/request", "Запрос на проект"), ("services", "Услуги LUSAR"),
    ("journal/guides", "Как выбрать свет"), ("compare", "Сравнение"),
    ("search", "Поиск"), ("selection", "Подборка"),
    ("legal/terms", "Условия продажи"), ("legal/privacy", "Конфиденциальность"),
    ("legal/cookies", "Политика cookie"), ("legal/loyalty", "Условия акций и скидок"),
    ("legal/ai", "Условия использования Lusar AI и аккаунта"),
]
ROOMS = {
    "living-room": ("Гостиная", "Начните с общего света. Добавьте бра рядом с креслом или диваном, если нужен отдельный свет для чтения.",
                    ("chandeliers", "pendants", "sconces")),
    "bedroom": ("Спальня", "Разделите общий свет и свет у кровати. Проверьте, удобно ли пользоваться выключателем, когда вы уже легли.",
                ("chandeliers", "sconces")),
    "kitchen": ("Кухня и столовая", "Подвес поможет выделить обеденный стол. Для рабочей поверхности предусмотрите отдельный свет и проверьте, где будут падать тени.",
                ("pendants", "chandeliers")),
    "workspace": ("Рабочая зона", "Учитывайте положение экрана и рабочей поверхности. Проверьте, не отражается ли источник света в мониторе.",
                  ("pendants", "sconces")),
    "outdoors": ("Улица и терраса", "Отдельно продумайте свет у входа, на дорожке и в зоне отдыха. Проверьте, рассчитана ли модель на условия установки.",
                 ("outdoor", "floodlights")),
}

def listing(items):
    return '<ul class="tiles">' + ''.join(f"<li>{link(path, title)}</li>" for path, title in items) + "</ul>"

def category_path(key):
    return "catalog/category/" + quote(key) + "/"

def product_path(item):
    return "catalog/product/" + quote(item["id"]) + "/"

def brand_path(key):
    return "brands/" + brand_registry[key]["path"] + "/"

def display_price(item):
    return "Цена по запросу" if item["price"] is None else f'{item["price"]:,} ֏'.replace(",", " ")


def product_grid(items):
    if not items:
        return "<p>В этой категории пока нет опубликованных товаров.</p>"
    cards = []
    for item in items:
        photo = ""
        if item["images"]:
            url = html.escape(item["images"][0]["url"], quote=True)
            photo = f'<img loading="lazy" decoding="async" src="{url}" alt="">'
        cards.append(
            f'<li data-price="{item["price"] if item["price"] is not None else ""}"><a href="/{product_path(item).strip("/")}">{photo}'
            f'<span class="tile-name">{html.escape(item["name"])}</span>'
            f'<span class="tile-sku">{html.escape(item["sku"])}</span>'
            f'<span class="tile-price">{html.escape(display_price(item))}</span></a></li>'
        )
    return (
        '<form id="product-filters" class="product-filters" hidden>'
        '<label>Цена до, ֏ <input name="maximum" type="number" min="0" step="any"></label>'
        '<label>Сортировка <select name="sort"><option value="default">Как в каталоге</option>'
        '<option value="low">Сначала дешевле</option><option value="high">Сначала дороже</option></select></label>'
        '<button type="reset">Сбросить</button></form>'
        '<p id="product-filter-count" role="status"></p><ul class="tiles product-tiles">' +
        "".join(cards) + '</ul><script src="/product-filters.js" defer></script>'
    )

write("", "Свет, который меняет пространство", """
<section class="home-hero" aria-labelledby="home-title">
<figure class="light-scene">
  <img id="scene-image" src="/scenes/lusar-hero.webp" width="1536" height="1024"
       fetchpriority="high" alt="Тёплый свет подвеса и мягкая подсветка вокруг обеденного стола">
  <figcaption>
    <div id="scene-controls" role="group" aria-label="Сценарий освещения" hidden>
      <button type="button" data-scene="day" aria-pressed="false">Дневной</button>
      <button type="button" data-scene="warm" aria-pressed="true">Тёплый</button>
      <button type="button" data-scene="evening" aria-pressed="false">Вечерний</button>
    </div>
    <p id="scene-caption" role="status">Подвес освещает стол, а подсветка добавляет глубину стенам.</p>
  </figcaption>
</figure>
<div class="hero-copy">
  <p class="eyebrow">LUSAR / Освещение</p>
  <h1 id="home-title">Свет, который меняет пространство</h1>
  <p class="lead">Люстры, бра и архитектурный свет для дома и проектов.</p>
  <div class="hero-actions"><a href="/catalog">Смотреть каталог</a><a href="/ai">Подобрать свет с Lusar AI</a></div>
</div>
</section>
<script src="/scenes.js" defer></script>
""" + '<section class="home-collection"><p class="eyebrow">Каталог</p><h2>Выберите свой свет</h2>' +
      '<p>Начните с типа светильника или подберите освещение под комнату.</p>' +
      listing([(category_path(key), category["name"]) for key, category in categories.items()]) +
      '<p>' + link("rooms", "Подобрать по комнате →") + '</p></section>' +
      '<section class="home-collection"><p class="eyebrow">Коллекция LUSAR</p><h2>Светильники в каталоге</h2>' +
      product_grid(data["products"][:4]) + '</section>')
write("catalog", "Каталог освещения",
      "<h2>По типу светильника</h2>" +
      listing([(category_path(key), item["name"]) for key, item in categories.items()]) +
      '<p>' + link("rooms/", "Подобрать по комнате") + ' · ' + link("brands", "Смотреть бренды") + '</p>')
for key, category in categories.items():
    children = [(category_path(child), item["name"]) for child, item in categories.items() if item.get("parentId") == key]
    products = [item for item in data["products"] if item["categoryId"] == key]
    body = f'<p>{link("catalog", "Все категории")}</p>'
    if children:
        body += "<h2>Подкатегории</h2>" + listing(children)
    if products or not children:
        body += product_grid(products)
    write(category_path(key), category["name"], body, draft=not (products or children))
for item in data["products"]:
    photos = ""
    if item["images"]:
        name = html.escape(item["name"], quote=True)
        first_url = html.escape(item["images"][0]["url"], quote=True)
        thumbnails = "".join(
            f'<button type="button" data-photo="{html.escape(photo["url"], quote=True)}" '
            f'aria-pressed="{str(index == 1).lower()}" aria-label="Фото {index}">'
            f'<img loading="lazy" src="{html.escape(photo["url"], quote=True)}" alt=""></button>'
            for index, photo in enumerate(item["images"], 1)
        ) if len(item["images"]) > 1 else ""
        photos = (
            f'<section class="product-gallery" aria-label="Фотографии товара">'
            f'<a class="product-photo" id="product-photo-link" href="{first_url}" aria-label="Увеличить фото">'
            f'<img id="product-photo" src="{first_url}" alt="{name}" fetchpriority="high"></a>'
            f'<div class="photo-thumbnails">{thumbnails}</div>'
            f'<dialog id="product-photo-dialog" aria-label="Увеличенное фото товара">'
            '<form method="dialog"><button>Закрыть</button></form>'
            f'<img id="product-photo-large" alt="{name}"></dialog></section>'
            '<script src="/product-gallery.js" defer></script>'
        )
    specs = "".join(f'<dt>{html.escape(a["label"])}</dt><dd>{html.escape(a["value"])} {html.escape(a["unit"])}</dd>' for a in item["attributes"])
    price = display_price(item)
    brand_id = product_brand_ids.get(item["id"])
    brand_link = f'<p>Бренд: {link(brand_path(brand_id), brands[brand_id]["name"])}</p>' if brand_id else ""
    if not brand_id and item["brand"].strip():
        brand_link = f'<p>Бренд: {html.escape(item["brand"].strip())}</p>'
    brand_name = brands[brand_id]["name"] if brand_id else item["brand"].strip()
    photo_urls = [photo["url"] for photo in item["images"]]
    product_url = PUBLIC_ORIGIN + "/" + product_path(item).strip("/")
    structured_data = {
        "@context": "https://schema.org", "@type": "Product", "url": product_url,
        "name": item["name"], "sku": item["sku"],
    }
    if photo_urls:
        structured_data["image"] = photo_urls
    if item["description"].strip():
        structured_data["description"] = item["description"]
    if brand_name:
        structured_data["brand"] = {"@type": "Brand", "name": brand_name}
    if item["price"] is not None:
        structured_data["offers"] = {"@type": "Offer", "url": product_url,
                                     "price": item["price"], "priceCurrency": "AMD"}
    write(product_path(item), item["name"],
          f'<p>{link("catalog", "Каталог")} · {link(category_path(item["categoryId"]), categories[item["categoryId"]]["name"])}</p>'
          f'<p>Артикул {html.escape(item["sku"])}</p>{brand_link}<p class="lead">{price}</p>'
          '<p>Наличие уточнит менеджер.</p>'
          f'{photos}<p>{html.escape(item["description"])}</p>'
          f'<dl>{specs}</dl><button type="button" data-add="{html.escape(item["id"], quote=True)}">Добавить в корзину</button>'
          f' <button type="button" data-favorite="{html.escape(item["id"], quote=True)}" aria-pressed="false">В избранное</button>'
          '<p id="favorite-status" role="status"></p>'
          f'<button type="button" data-compare="{html.escape(item["id"], quote=True)}" aria-pressed="false">Сравнить</button>'
          f'<p id="compare-status" role="status"></p><p>{link("compare", "Открыть сравнение")}</p>'
          f'<p role="status" id="cart-status"></p><p id="cart-next" hidden>{link("cart/", "Перейти в корзину")}</p>'
          f'<p>{link("ai?product=" + quote(item["id"], safe=""), "Примерить в моей комнате")} · '
          f'{link("support?product=" + quote(item["id"], safe=""), "Уточнить по товару")}</p>',
          description=" ".join(item["description"].split())[:160],
          image=photo_urls[0] if photo_urls else "", structured_data=structured_data)

for path, title in FOOTER + EXTRA:
    if path in {"ai", "cart", "checkout", "checkout/received", "payment", "sitemap", "account/loyalty", "offers", "search", "favorites", "compare", "brands", "rooms", "order-status", "legal/cookies", "faq", "support", "contacts", "stores", "about"}:
        continue
    children = [(p + "/", name) for p, name in EXTRA if p.rpartition("/")[0] == path]
    write(path, title, '<p>Страница в разработке</p>' + (listing(children) if children else ""), draft=True)
write("payment", "Оплата", "<p>Оформите заявку на сайте. Менеджер подтвердит сумму и согласует оплату в магазине, по чеку или при получении.</p>")
store_path = "stores/yerevan-arshakunyats"
store_address = "Ереван, проспект Аршакуняц, 210/1"
d50_path = "stores/yerevan-smbat-zoravar"
d50_address = "Ереван, улица Смбата Зоравара, 11/3"
store_phone = '<a href="tel:+37477123451">+374 77 123451</a>'
store_source = '<a href="https://www.spyur.am/ru/companies/luys-plus-shop/52299/">Карточка магазина в «Спюре»</a>'
maps_query = urlencode({"api": 1, "query": store_address})
yandex_query = urlencode({"text": store_address})
store_routes = (
    f'<a href="https://www.google.com/maps/search/?{html.escape(maps_query, quote=True)}">Найти адрес в Google Картах</a> · '
    f'<a href="https://yandex.com/maps/?{html.escape(yandex_query, quote=True)}">Найти адрес в Яндекс Картах</a>'
)
write("contacts", "Контакты LUSAR",
      f'<p>Общий телефон магазинов: {store_phone}</p>'
      f'<p>Магазины открыты ежедневно, {SERVICE_HOURS}. Часы связи с менеджером по заявкам: {SERVICE_HOURS}.</p>' +
      listing([(store_path, store_address), (d50_path, d50_address + ", павильон D50")]))
write("stores", "Магазины LUSAR", listing([(store_path, store_address), (d50_path, d50_address + ", павильон D50")]))
write(store_path, "Магазин LUSAR в Ереване",
      f'<address>{store_address}. Территория ярмарки «Еранкюни», Шенгавит.</address>'
      f'<p>Телефон: {store_phone}</p><p>Ежедневно, {SERVICE_HOURS}.</p>'
      f'<p>{store_routes}</p><p>{store_source}</p>')
d50_google = html.escape(urlencode({"api": 1, "query": d50_address}), quote=True)
d50_yandex = html.escape(urlencode({"text": d50_address}), quote=True)
write(d50_path, "LUSAR на улице Смбата Зоравара",
      f'<address>{d50_address}, павильон D50. Шенгавит, рядом с метро «Сасунци Давид».</address>'
      f'<p>Телефон: {store_phone}</p><p>Ежедневно, {SERVICE_HOURS}.</p>'
      f'<p><a href="https://www.google.com/maps/search/?{d50_google}">Найти адрес в Google Картах</a> · '
      f'<a href="https://yandex.com/maps/?{d50_yandex}">Найти адрес в Яндекс Картах</a> · '
      '<a href="https://2gis.am/ru/yerevan/firm/70000001110752412">Карточка магазина в 2ГИС</a></p>')
write("about", "О LUSAR",
      '<p>LUSAR — новое название LUYS+. В каталоге представлены светильники для дома, интерьера и улицы.</p>'
      '<p>' + link("about/founder", "David Matevosyan") + ' · ' + link("stores", "Магазины") + '</p>')
FAQ = [
    ("Можно ли оформить заявку без регистрации?", "Да. Добавьте товары в корзину, укажите имя и телефон. Email и адрес можно оставить пустыми."),
    ("Что происходит после отправки заявки?", f"Вы получите номер и приватную ссылку для проверки статуса. Менеджер подтвердит наличие, итоговую сумму и способ получения. Часы связи: {SERVICE_HOURS}."),
    ("Как оплатить заказ?", "Оплатить можно в магазине, по чеку от менеджера или при получении. Доступный вариант менеджер согласует при подтверждении заказа."),
    ("Можно ли узнать наличие по сайту?", "Пока наличие уточняет менеджер. При обращении укажите артикул из карточки товара."),
    ("Как действует скидка 10% на первый заказ?", "Пока акция активна, она доступна зарегистрированным покупателям без выполненных заказов. Отменённая заявка не лишает права на скидку. Скидка применяется отдельно от промокода и скидки кабинета."),
    ("Почему скидка по промокоду меньше его номинала?", "Промокод уменьшает стоимость товаров максимум на 20%. Например, при заказе на 10 000 ֏ код на 5 000 ֏ даст скидку 2 000 ֏."),
]
write("faq", "Частые вопросы",
      "".join(f'<details><summary>{html.escape(question)}</summary><p>{html.escape(answer)}</p></details>'
              for question, answer in FAQ) +
      '<p>' + link("payment", "Подробнее об оплате") + ' · ' + link("support", "Поддержка") + '</p>')
write("support", "Поддержка и сервис", f"""
<p id="support-product" hidden>Вопрос по товару <a id="support-product-link"></a></p>
<p>Если вопрос связан с заказом, сохраните его номер. Если нужна информация о светильнике, укажите артикул.</p>
<p>Часы связи с менеджером: {SERVICE_HOURS}.</p>
<p>Позвонить в LUSAR: {store_phone}.</p>
<p>WhatsApp и Telegram-бот в разработке.</p>
<script src="/support.js" defer></script>
""" + '<p>' + link("contacts", "Телефон и адрес") + ' · ' + link("order-status", "Проверить статус заявки") + ' · ' + link("faq", "Частые вопросы") + '</p>', draft=True)
write("legal/cookies", "Политика cookie", """
<p>Страница в разработке.</p>
<p>В текущей сборке настройки темы, корзина и избранное сохраняются в браузере.
Выбор статистики можно изменить через «Настройки cookie» в подвале.</p>
""", draft=True)
write("ai", "Lusar AI", """
<p id="ai-mode">Подбор освещения по фотографии комнаты.</p>
<p id="ai-product" hidden><a id="ai-product-link"></a></p>
<p>Визуализация и подбор в разработке. Здесь можно проверить, как загрузится фотография. Она остаётся в браузере.</p>
<label>Фото комнаты <input id="ai-photo" type="file" accept="image/jpeg,image/png,image/webp"></label>
<p>JPEG, PNG или WebP, до 10 МБ.</p>
<img id="ai-photo-preview" class="ai-photo-preview" alt="Предпросмотр фотографии комнаты" hidden>
<p id="ai-photo-status" role="status"></p>
<script src="/ai-preview.js" defer></script>
""", draft=True)
write("rooms", "Подобрать свет по комнате",
      "<p>Выберите помещение, чтобы посмотреть идеи по освещению и перейти в подходящие категории.</p>" +
      listing([(f"rooms/{key}", title) for key, (title, _, _) in ROOMS.items()]))
for key, (title, tip, related) in ROOMS.items():
    write(f"rooms/{key}", title,
          f'<p>{link("rooms", "Все помещения")}</p><p class="lead">{html.escape(tip)}</p><h2>Что посмотреть в каталоге</h2>' +
          listing([(category_path(category), categories[category]["name"]) for category in related if category in categories]))
write("brands", "Бренды", listing([(brand_path(key), brand["name"]) for key, brand in sorted(brands.items())])
      if brands else "<p>Страница в разработке</p>", draft=not brands)
for key, brand in brands.items():
    write(brand_path(key), brand["name"], f'<p>{link("brands", "Все бренды")}</p><h2>Товары бренда</h2>' +
          product_grid(brand["products"]))
write("search", "Поиск по каталогу", """
<form id="catalog-search" action="/search" role="search">
  <label>Название, артикул или характеристика <input type="search" name="q" maxlength="120"></label>
  <button>Найти</button>
</form>
<p id="search-status" role="status"></p>
<ul id="search-results" class="tiles"></ul>
<script src="/search.js" defer></script>
""", draft=True)
write("offers", "Акции",
      "<h2>10% на первый заказ</h2><p>Предложение доступно всем зарегистрированным покупателям без выполненных заказов. "
      "Если заказ отменён, скидка остаётся доступной. Минимальной суммы нет. "
      "Скидка применяется отдельно от промокодов и скидки кабинета.</p>")
loyalty_rows = "".join(
    f'<tr><td>{("От " + f"{threshold:,}".replace(",", " ") + " ֏") if threshold else "До 50 000 ֏"}</td><td>{discount}%</td></tr>'
    for threshold, discount in LOYALTY_TIERS
)
write("account/loyalty", "Скидки и промокоды",
      f"<p>Пока акция действует, всем зарегистрированным покупателям без выполненных заказов доступна скидка "
      f"{FIRST_ORDER_PERCENT}% на первый заказ. Она применяется отдельно от других скидок и промокодов.</p>"
      "<p>Накопления бессрочные. Учитываются полученные и оплаченные товары по сумме после скидок, без доставки. "
      "При возврате накопленная сумма пересчитывается.</p>"
      '<table><caption>Уровни программы лояльности</caption><thead><tr><th scope="col">Накоплено</th>'
      f'<th scope="col">Скидка</th></tr></thead><tbody>{loyalty_rows}</tbody></table>', draft=True)
write("cart", "Корзина", '<div id="cart-items"></div><p id="cart-summary" aria-live="polite"></p><p>' + link("offers/", "10% на первый заказ · условия акции") +
      '</p><p id="checkout-link" hidden>' +
      link("checkout/", "Оформить заявку") + '</p><p>' + link("catalog/", "Продолжить покупки") + '</p>', draft=True)
write("favorites", "Избранное", '<ul id="favorite-items" class="tiles"></ul><p id="favorite-status" role="status"></p><p>' +
      link("catalog", "Открыть каталог") + "</p>", draft=True)
write("compare", "Сравнение светильников", '<p id="compare-status" role="status"></p>'
      '<div id="compare-table" class="comparison-scroll" role="region" aria-label="Таблица сравнения" tabindex="0"></div>'
      '<p>' + link("catalog", "Открыть каталог") + '</p>', draft=True)
write("checkout", "Оформление заявки", """
<p>Менеджер уточнит наличие, итоговую сумму и способ оплаты.</p>
<div id="cart-items"></div><p id="cart-summary" aria-live="polite"></p>
<form id="checkout" hidden>
  <label>Имя <input name="name" autocomplete="name" required maxlength="120"></label>
  <label>Телефон <input name="phone" type="tel" autocomplete="tel" required maxlength="40"></label>
  <label>Email (необязательно) <input name="email" type="email" autocomplete="email" maxlength="254"></label>
  <label>Адрес (необязательно) <input name="address" autocomplete="street-address" maxlength="300"></label>
  <label>Промокод <input name="promo" autocomplete="off" maxlength="32"></label>
  <p id="promo-total" aria-live="polite"></p>
  <button class="primary-action" type="submit">Отправить заявку</button>
</form>
<p id="checkout-status" role="status"></p>
<p><a id="order-status-link" hidden>Сохранить ссылку на статус заявки</a></p>
""", draft=True)
write("checkout/received", "Подтверждение заявки", f"""
<p id="receipt-number" role="status">Здесь появится номер после отправки заявки.</p>
<section id="receipt-details" hidden>
  <p>Менеджер свяжется с вами, чтобы подтвердить наличие, итоговую сумму и способ получения.</p>
  <p>Часы связи с менеджером: {SERVICE_HOURS}.</p>
  <p>Если хотите уточнить заказ, позвоните по номеру {store_phone} и назовите номер заявки.</p>
  <p><a id="receipt-tracking" hidden>Проверить статус заявки</a></p>
</section>
<script src="/receipt.js" defer></script>
""" + '<p>' + link("catalog", "Вернуться в каталог") + ' · ' + link("support", "Поддержка") + '</p>', draft=True)
write("order-status", "Статус заявки", """
<meta name="referrer" content="no-referrer">
<p>Откройте приватную ссылку, выданную после оформления заявки.</p>
<p id="guest-order-status" role="status"></p>
<script src="/order-status.js" defer></script>
""", draft=True)
write("sitemap", "Карта сайта", listing([("", "Главная"), ("catalog/", "Каталог")] +
      [(p + "/", name) for p, name in FOOTER + EXTRA if p != "sitemap"] +
      [(f"rooms/{key}", title) for key, (title, _, _) in ROOMS.items()] +
      [(store_path, store_address), (d50_path, d50_address + ", павильон D50")]))
write("404", "Страница не найдена", listing([("catalog/", "Вернуться в каталог")]), draft=True)
(OUT / "404.html").write_bytes((OUT / "404/index.html").read_bytes())
(OUT / "catalog.html").write_text(
    '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="robots" content="noindex">'
    '<title>Каталог LUSAR</title><script src="/legacy-catalog.js" defer></script>'
    '<p><a href="/catalog">Перейти в каталог LUSAR</a></p></html>', encoding="utf-8"
)
(OUT / "legacy-catalog.js").write_text(
    "const productPaths = " + json.dumps({item["id"]: "/" + product_path(item).rstrip("/") for item in data["products"]}) +
    ";\nconst id = new URLSearchParams(location.search).get('product');\n"
    "location.replace(!id ? '/catalog' : Object.hasOwn(productPaths, id) ? productPaths[id] : '/catalog/unavailable');\n",
    encoding="utf-8"
)
write("catalog/unavailable", "Товар сейчас недоступен",
      "<p>Возможно, модель снята с продажи. Посмотрите актуальные товары в каталоге.</p>" +
      listing([("catalog/", "Открыть каталог")]), draft=True)
sitemap = ElementTree.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
for url in sorted(set(indexable)):
    ElementTree.SubElement(ElementTree.SubElement(sitemap, "url"), "loc").text = url
ElementTree.ElementTree(sitemap).write(OUT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
(OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {PUBLIC_ORIGIN}/sitemap.xml\n", encoding="utf-8")
(OUT / "site.css").write_bytes((ROOT / "site.css").read_bytes())
(OUT / "theme.js").write_bytes((ROOT / "theme.js").read_bytes())
(OUT / "cookie-settings.js").write_bytes((ROOT / "cookie-settings.js").read_bytes())
(OUT / "analytics.js").write_bytes((ROOT / "analytics.js").read_bytes())
(OUT / "scenes.js").write_bytes((ROOT / "scenes.js").read_bytes())
(OUT / "order-status.js").write_bytes((ROOT / "order-status.js").read_bytes())
(OUT / "receipt.js").write_bytes((ROOT / "receipt.js").read_bytes())
(OUT / "product-gallery.js").write_bytes((ROOT / "product-gallery.js").read_bytes())
(OUT / "product-filters.js").write_bytes((ROOT / "product-filters.js").read_bytes())
(OUT / "ai-preview.js").write_text(
    "const aiProducts = " + json.dumps({
        item["id"]: {"name": item["name"], "path": "/" + product_path(item).rstrip("/")}
        for item in data["products"]
    }, ensure_ascii=False) + ";\n" + (ROOT / "ai-preview.js").read_text(encoding="utf-8"), encoding="utf-8"
)
(OUT / "scenes").mkdir(exist_ok=True)
for name in ("lusar-hero.webp", "lusar-scene-day.webp", "lusar-scene-evening.webp"):
    (OUT / "scenes" / name).write_bytes((ROOT / "scenes" / name).read_bytes())
search_index = [
    {"name": item["name"], "path": "/" + product_path(item).rstrip("/"), "sku": item["sku"],
     "keywords": " ".join([item["brand"], categories[item["categoryId"]]["name"],
                          brand_registry.get(product_brand_ids.get(item["id"]), {}).get("name", "")] +
                         [f'{a["label"]} {a["value"]} {a["unit"]}' for a in item["attributes"]])}
    for item in data["products"]
] + [
    {"name": category["name"], "path": "/" + category_path(key).rstrip("/"), "sku": "", "keywords": ""}
    for key, category in categories.items()
] + [
    {"name": brand["name"], "path": "/" + brand_path(key).rstrip("/"), "sku": "",
     "keywords": " ".join(["бренд", *brand_registry[key]["aliases"]])}
    for key, brand in brands.items()
] + [
    {"name": title, "path": "/rooms/" + key, "sku": "", "keywords": tip}
    for key, (title, tip, _) in ROOMS.items()
] + [
    {"name": question, "path": "/faq", "sku": "", "keywords": answer}
    for question, answer in FAQ
]
(OUT / "search.js").write_text(
    "const searchIndex = " + json.dumps(search_index, ensure_ascii=False) + ";\n" +
    (ROOT / "search.js").read_text(encoding="utf-8"), encoding="utf-8"
)
(OUT / "cart.js").write_text(
    "const products = " + json.dumps({
        item["id"]: {"name": item["name"], "price": item["price"], "path": "/" + product_path(item).rstrip("/"),
                     "sku": item["sku"], "attributes": item["attributes"]}
        for item in data["products"]
    }, ensure_ascii=False) + ";\nconst promotions = " +
    (ROOT / "promotions.json").read_text(encoding="utf-8") + ";\nconst serviceHours = " +
    json.dumps(SERVICE_HOURS, ensure_ascii=False) + ";\n" +
    (ROOT / "cart.js").read_text(encoding="utf-8") + "\n" +
    (ROOT / "favorites.js").read_text(encoding="utf-8") + "\n" +
    (ROOT / "compare.js").read_text(encoding="utf-8"), encoding="utf-8"
)
(OUT / "support.js").write_text(
    "const supportProducts = " + json.dumps({
        item["id"]: {"name": item["name"], "sku": item["sku"], "path": "/" + product_path(item).rstrip("/")}
        for item in data["products"]
    }, ensure_ascii=False) + ";\n" + (ROOT / "support.js").read_text(encoding="utf-8"), encoding="utf-8"
)
for directory, current_ids in (
    (OUT / "catalog/product", {item["id"] for item in data["products"]}),
    (OUT / "catalog/category", set(categories)),
    (OUT / "brands", {brand_registry[key]["path"] for key in brands}),
):
    for page in directory.glob("*/index.html"):
        if page.parent.name not in current_ids:
            page.unlink()
