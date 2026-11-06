"""Build the LUSAR navigation preview from the public storefront snapshot."""
import html
import json
import os
import re
import warnings
from pathlib import Path
from urllib.parse import quote, urlencode
from xml.etree import ElementTree
from loyalty import FIRST_ORDER_PERCENT, LOYALTY_TIERS
from sync_catalog import validate, revision

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ.get("LUSAR_BUILD_DIR", ROOT / "dist"))
PUBLIC_ORIGIN = "https://lusar.am"
SERVICE_HOURS = "09:30–19:00"
ANALYTICS_IDS = {
    "google-analytics": os.environ.get("LUSAR_GA4_ID", "").strip(),
    "yandex-metrica": os.environ.get("LUSAR_YANDEX_METRICA_ID", "").strip(),
}
AI_TELEGRAM_USERNAME = os.environ.get("LUSAR_AI_TELEGRAM_USERNAME", "").strip()
AI_TELEGRAM_USERNAME = re.sub(r"^(?:https?://)?(?:www\.)?t\.me/", "", AI_TELEGRAM_USERNAME, flags=re.IGNORECASE)
AI_TELEGRAM_USERNAME = AI_TELEGRAM_USERNAME.removeprefix("@").removesuffix("/")
if AI_TELEGRAM_USERNAME and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,28}bot", AI_TELEGRAM_USERNAME, flags=re.IGNORECASE):
    warnings.warn("Invalid LUSAR_AI_TELEGRAM_USERNAME; Telegram link omitted.")
    AI_TELEGRAM_USERNAME = ""
for provider, pattern in (("google-analytics", r"G-[A-Z0-9]+"), ("yandex-metrica", r"[1-9][0-9]{0,11}")):
    if ANALYTICS_IDS[provider] and not re.fullmatch(pattern, ANALYTICS_IDS[provider]):
        raise ValueError(f"Invalid analytics ID: {provider}")
indexable = []
data = json.loads(Path(os.environ.get("LUSAR_CATALOG_PATH", ROOT.parent / "storefront.json")).read_text(encoding="utf-8-sig"))
validate(data)
CATALOG_REVISION = revision(data)
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

NAV_ICONS = {
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/>',
    "favorites": '<path d="M12 20 4.8 13a4.6 4.6 0 0 1 6.5-6.5l.7.7.7-.7a4.6 4.6 0 0 1 6.5 6.5Z"/>',
    "cart": '<path d="M5 8h14l1 13H4Zm4 1V6a3 3 0 0 1 6 0v3"/>',
    "account": '<circle cx="12" cy="8" r="3.2"/><path d="M5 20v-1a7 7 0 0 1 14 0v1"/>',
    "theme": '<circle cx="12" cy="12" r="4"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2"/>',
    "moon": '<path d="M20.4 15.1A8.9 8.9 0 0 1 8.9 3.6a8.9 8.9 0 1 0 11.5 11.5Z"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "spark": '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>',
    "upload": '<path d="M12 16V4m-4 4 4-4 4 4M4 15v5h16v-5"/>',
    "overview": '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>',
    "orders": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6m-6 4h6m-6 4h3"/>',
    "pin": '<path d="M19 10c0 5-7 10-7 10s-7-5-7-10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
    "logout": '<path d="M11 4H5v16h6m2-12 4 4-4 4m-4-4h8"/>',
    "check": '<path d="m5 12 4 4 10-10"/>',
}


def nav_icon(name):
    return ('<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" '
            'stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            + NAV_ICONS[name] + "</svg>")


def nav_dropdown(title, items, path, overview):
    return ('<details class="nav-dropdown"><summary>' + html.escape(title) +
            '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">'
            '<path d="m2 4 4 4 4-4" fill="none" stroke="currentColor"/></svg></summary>'
            '<div class="nav-panel"><ul>' +
            "".join(f"<li>{link(url, label)}</li>" for url, label in items) +
            f'</ul><p>{link(path, overview)}</p></div></details>')


def wordmark():
    return ('<a class="wordmark" href="/" aria-label="LUSAR — главная">'
            '<svg viewBox="0 0 32 32" width="27" height="27" fill="none" stroke="currentColor" '
            'stroke-width=".9" aria-hidden="true"><path d="M16 1v30M1 16h30M5.4 5.4l21.2 21.2M5.4 26.6L26.6 5.4"/>'
            '<circle cx="16" cy="16" r="4"/></svg><span>LUSAR</span></a>')


def header_markup():
    shortcuts = (("search", "Поиск"), ("favorites", "Избранное"),
                 ("account", "Личный кабинет"), ("cart", "Корзина"))
    tools = "".join(f'<a class="icon-link" href="/{key}" aria-label="{title}" title="{title}">{nav_icon(key)}</a>'
                    for key, title in shortcuts)
    catalog_links = [(category_path(key), category["name"]) for key, category in categories.items()
                     if not category.get("parentId")]
    catalog_links.append(("compare", "Сравнение"))
    room_links = [("rooms/" + key, name) for key, (name, *_) in ROOMS.items()]
    return ('<header class="site-header"><div class="header-inner">'
            + wordmark() +
            '<nav class="main-nav" id="main-nav" aria-label="Основная навигация">' +
            nav_dropdown("Каталог", catalog_links, "catalog", "Весь каталог →") +
            nav_dropdown("По комнатам", room_links, "rooms", "Все комнаты →") + link("ai", "Lusar AI") +
            link("contacts", "Контакты") +
            '<a class="mobile-shortcut" href="/favorites">' + nav_icon("favorites") + '<span>Избранное</span></a>' +
            '<a class="mobile-shortcut" href="/account">' + nav_icon("account") + '<span>Личный кабинет</span></a>' +
            '</nav><nav class="header-tools" aria-label="Поиск и покупки">' + tools +
            '<div class="language-control" hidden><span id="language-display" aria-hidden="true">RU</span>'
            '<select id="language" aria-label="Язык сайта">'
            '<option value="ru" lang="ru">Русский</option><option value="hy" lang="hy">Հայերեն</option>'
            '<option value="en" lang="en">English</option></select></div>'
            '<button class="icon-link" id="theme-toggle" type="button" aria-label="Светлая тема" '
            'aria-pressed="false" hidden><span class="theme-sun">' + nav_icon("theme") +
            '</span><span class="theme-moon">' + nav_icon("moon") + '</span></button>'
            '<button class="icon-link menu-toggle" id="menu-toggle" type="button" aria-label="Меню" '
            'aria-controls="main-nav" aria-expanded="false" hidden>' + nav_icon("menu") +
            '</button></nav></div></header><script src="/site-nav.js" defer></script>')


def footer_markup():
    groups = "".join(f'<section class="footer-group"><h2>{title}</h2><ul>' +
                     "".join(f"<li>{link(path, label)}</li>" for path, label in items) +
                     "</ul></section>" for title, items in FOOTER_GROUPS)
    return ('<footer class="site-footer"><div class="footer-main"><div class="footer-brand">' +
            wordmark() + '<p>Светильники для дома и проектов.</p></div>' + groups +
            '</div><div class="footer-bottom"><span>© LUSAR</span>' +
            "".join(link(path, label) for path, label in FOOTER_LEGAL) +
            '<button type="button" id="cookie-settings" hidden>Настройки cookie</button></div></footer>')


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
    analytics = ""
    if path not in {"ai", "order-status"} and not (path == "account" or path.startswith("account/")):
        attrs = "".join(f' data-{provider}="{value}"' for provider, value in ANALYTICS_IDS.items() if value)
        if attrs:
            analytics = ' data-analytics-enabled="true"' + attrs
    cart_script = ('<script src="/cart.js" defer></script>'
                   if path in {"catalog", "cart", "checkout", "favorites", "compare"} or path.startswith("catalog/product/") or "data-add=" in body
                   else "")
    page_class = {"": "home", "catalog": "catalog-page", "ai": "ai-page", "cart": "cart-page", "checkout": "checkout-page",
                  "checkout/received": "receipt-page", "favorites": "wishlist-page", "order-status": "tracking-page"}.get(path, "content-page")
    if 'id="account-member"' in body:
        page_class = "account-page"
    if path.startswith("catalog/category/"):
        page_class = "catalog-page category-page"
    if path.startswith("catalog/product/"):
        page_class = "product-page"
    page_heading = "" if path in {"", "catalog", "ai", "cart", "checkout", "checkout/received", "favorites", "order-status"} or page_class in {"product-page", "account-page"} else f"<h1>{html.escape(title)}</h1>"
    target.write_text(f"""<!doctype html>
<html lang="ru" data-catalog-revision="{CATALOG_REVISION}"{analytics}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="/favicon.svg" type="image/svg+xml">
{robots}{canonical}{metadata}<title>{html.escape(title)} — LUSAR</title><script src="/theme.js"></script><script src="/locale.js" defer></script><script src="/account-session.js" defer></script><link rel="stylesheet" href="/site.css"></head>
<body><a class="skip-link" href="#main">К содержанию</a>{header_markup()}
<main id="main" tabindex="-1" class="{page_class}">{page_heading}{body}</main>
{footer_markup()}
<section id="cookie-panel" class="cookie-panel" aria-labelledby="cookie-heading" hidden>
  <h2 id="cookie-heading" tabindex="-1">Настройки cookie</h2>
  <p>Браузер хранит настройки сайта и корзину. Сбор статистики можно разрешить или отключить отдельно.</p>
  <p>{link("legal/cookies", "Подробнее о cookie")}</p>
  <button type="button" data-cookie-choice="essential">Только необходимые</button>
  <button type="button" data-cookie-choice="analytics">Разрешить статистику</button>
  <p id="cookie-status" role="status"></p>
</section>
{'<dialog id="first-order-promo" aria-labelledby="promo-heading"><h2 id="promo-heading">10% на первый заказ</h2><p>Зарегистрируйтесь и получите скидку на первую покупку.</p><p>' + link("offers/", "Посмотреть условия") + '</p><form method="dialog"><button>Закрыть</button></form></dialog>' if path.rstrip("/") == "catalog" or path.startswith("catalog/product/") else ""}
<script src="/analytics.js" defer></script>{cart_script}<script src="/cookie-settings.js" defer></script><script src="/catalog-live.js" defer></script></body></html>""".replace('src="/cart.js"', f'src="/cart.js?catalog={CATALOG_REVISION}&amp;orders=3"')
        .replace('src="/search.js"', f'src="/search.js?catalog={CATALOG_REVISION}"')
        .replace('src="/ai-preview.js"', f'src="/ai-preview.js?catalog={CATALOG_REVISION}"')
        .replace('src="/support.js"', f'src="/support.js?catalog={CATALOG_REVISION}"'), encoding="utf-8")

FOOTER_GROUPS = (
    ("Выбор света", (("catalog", "Каталог"), ("rooms", "По комнатам"), ("brands", "Бренды"),
                     ("journal", "Статьи"), ("offers", "Акции"))),
    ("Покупателям", (("delivery", "Доставка"), ("payment", "Оплата"), ("returns", "Гарантия и возврат"),
                     ("faq", "Частые вопросы"), ("support", "Поддержка"))),
    ("О LUSAR", (("about", "О нас"), ("contacts", "Контакты"), ("partners", "Наши партнёры"), ("news", "Новости"))),
)
FOOTER_LEGAL = (("legal", "Правовая информация"), ("sitemap", "Карта сайта"))
FOOTER = [item for _, items in FOOTER_GROUPS for item in items if item[0] not in {"catalog", "rooms"}] + list(FOOTER_LEGAL)
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
    ("legal/terms", "Публичная оферта и условия продажи"), ("legal/privacy", "Конфиденциальность"),
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


def product_grid(items, *, filters=True):
    if not items:
        return "<p>В этой категории пока нет опубликованных товаров.</p>"
    cards = []
    for item in items:
        photo = ""
        if item["images"]:
            url = html.escape(item["images"][min(1, len(item["images"]) - 1)]["url"], quote=True)
            photo = f'<img loading="lazy" decoding="async" src="{url}" alt="" width="640" height="640">'
        attributes = {a["label"]: a["value"].strip() for a in item["attributes"]}
        keywords = " ".join([item["name"], item["sku"], item["brand"], categories[item["categoryId"]]["name"]] +
                            [f'{a["label"]} {a["value"]} {a["unit"]}' for a in item["attributes"]])
        metadata = {"price": item["price"] if item["price"] is not None else "", "category": item["categoryId"],
                    "search": keywords, "socket": attributes.get("Цоколь", ""),
                    "temperature": attributes.get("Цветовая температура", "")}
        attrs = " ".join(f'data-{key}="{html.escape(str(value), quote=True)}"' for key, value in metadata.items())
        identity = html.escape(item["id"], quote=True)
        actions = ('<div class="card-actions">'
                   f'<button type="button" data-favorite="{identity}" aria-label="В избранное" aria-pressed="false">'
                   + nav_icon("favorites") + '</button>'
                   f'<button type="button" data-add="{identity}" aria-label="Добавить в корзину">'
                   + nav_icon("cart") + '</button></div>') if filters else ""
        cards.append(
            f'<li {attrs}><a href="/{product_path(item).strip("/")}">'
            f'<span class="product-thumb">{photo}<span class="card-arrow" aria-hidden="true">↗</span></span>'
            f'<span class="tile-name" data-locale-source>{html.escape(item["name"])}</span>'
            f'<span class="tile-meta"><span class="tile-sku">{html.escape(item["sku"])}</span>'
            f'<span class="tile-price">{html.escape(display_price(item))}</span></span></a>{actions}</li>'
        )
    grid = '<ul class="tiles product-tiles">' + "".join(cards) + '</ul>'
    if not filters:
        return grid

    def select(name, label, choices):
        if len(choices) < 2:
            return ""
        options = ''.join(f'<option value="{html.escape(value, quote=True)}">{html.escape(title)}</option>'
                          for value, title in choices)
        return (f'<label>{label}<select name="{name}"><option value="">Все</option>' + options + '</select></label>')

    category_ids = {item["categoryId"] for item in items}
    category_filter = select("category", "Тип светильника", [(key, value["name"]) for key, value in categories.items() if key in category_ids])
    facets = ""
    for name, label, attribute in (("socket", "Цоколь", "Цоколь"), ("temperature", "Температура света", "Цветовая температура")):
        values = sorted({a["value"].strip() for item in items for a in item["attributes"] if a["label"] == attribute and a["value"].strip()})
        facets += select(name, label, [(value, value + (" K" if name == "temperature" else "")) for value in values])
    return (
        '<form id="product-filters" class="product-filters" role="search" aria-label="Подбор светильников" hidden>'
        '<div class="catalog-toolbar"><label class="catalog-search"><span class="visually-hidden">Поиск по каталогу</span>'
        '<span>' + nav_icon("search") + '<input name="q" type="search" placeholder="Название или артикул" autocomplete="off"></span></label>'
        '<label><span class="visually-hidden">Сортировка</span><select name="sort"><option value="default">Как в каталоге</option>'
        '<option value="low">Сначала дешевле</option><option value="high">Сначала дороже</option></select></label></div>'
        '<details class="catalog-filter-panel"><summary>Фильтры<span aria-hidden="true">＋</span></summary><div class="catalog-filter-fields">'
        + category_filter + '<label>Цена от, ֏ <input name="minimum" type="number" min="0" step="any" inputmode="decimal"></label>'
        '<label>Цена до, ֏ <input name="maximum" type="number" min="0" step="any" inputmode="decimal"></label>' + facets +
        '</div></details><div class="catalog-result-bar"><p id="product-filter-count" role="status"></p>'
        '<button type="reset" class="text-button">Сбросить фильтры</button></div></form>'
        '<div class="catalog-shopping-feedback"><button type="button" data-dismiss-shopping aria-label="Закрыть уведомление">×</button>'
        '<p id="cart-status" role="status"></p><p id="favorite-status" role="status"></p>'
        '<p id="cart-next" hidden>' + link("cart", "Перейти в корзину") + '</p></div>' + grid +
        '<section class="catalog-empty" id="catalog-empty" hidden><h2>Ничего не найдено</h2>'
        '<p>Попробуйте изменить запрос или сбросить фильтры.</p><button type="reset" form="product-filters">Сбросить фильтры</button></section>'
        '<script src="/product-filters.js" defer></script>'
    )


def category_navigation(active=""):
    links = '<a href="/catalog"' + (' aria-current="page"' if not active else '') + '>Все светильники</a>'
    links += ''.join(f'<a href="/{category_path(key).strip("/")}"' +
                     (' aria-current="page"' if key == active else '') + f'>{html.escape(category["name"])}</a>'
                     for key, category in categories.items())
    return '<nav class="catalog-categories" aria-label="Категории">' + links + '</nav>'


products_with_photos = {}
for item in data["products"]:
    if item["images"]:
        products_with_photos.setdefault(item["categoryId"], []).append(item)


def category_cards(keys, *, eager=False):
    short_names = {"pendants": "Подвесы", "outdoor": "Уличный свет"}
    loading = "eager" if eager else "lazy"
    cards = []
    for key in keys:
        category = categories[key]
        products = products_with_photos.get(key)
        photo = ""
        if products:
            url = html.escape(products[0]["images"][0]["url"], quote=True)
            photo = f'<img loading="{loading}" decoding="async" src="{url}" alt="">'
        label = html.escape(short_names.get(key, category["name"]))
        cards.append(
            f'<li><a href="/{category_path(key).strip("/")}"><span class="category-photo">{photo}</span>'
            f'<span class="category-label">{label}<span aria-hidden="true">↗</span></span></a></li>'
        )
    return '<ul class="category-cards">' + "".join(cards) + '</ul>'


home_categories = [key for key in ("chandeliers", "pendants", "sconces", "outdoor") if key in categories]
featured_products = [products[1] if len(products) > 1 else products[0]
                     for key in home_categories if (products := products_with_photos.get(key))]

write("", "Свет для жизни", """
<section class="home-hero" aria-labelledby="home-title">
<div class="hero-copy">
  <h1 id="home-title">Свет для жизни</h1>
  <p class="lead">Светильники для дома и проектов.</p>
  <div class="hero-actions"><a class="button-link" href="/catalog">Открыть каталог <span aria-hidden="true">↗</span></a>
  <a href="/ai">Примерить с Lusar AI</a></div>
</div>
<figure class="light-scene">
  <img id="scene-image" src="/scenes/lusar-hero.webp" width="1536" height="1024"
       fetchpriority="high" alt="Тёплый свет подвеса и мягкая подсветка вокруг обеденного стола">
  <figcaption>
    <div id="scene-controls" role="group" aria-label="Сценарий освещения" hidden>
      <button type="button" data-scene="day" aria-pressed="false">День</button>
      <button type="button" data-scene="warm" aria-pressed="true">Тёплый</button>
      <button type="button" data-scene="evening" aria-pressed="false">Вечер</button>
    </div>
    <p id="scene-caption" role="status">Тёплый свет над столом</p>
  </figcaption>
</figure>
</section>
<script src="/scenes.js" defer></script>
""" + '<section class="home-collection"><div class="section-heading"><h2>Выберите свой свет</h2>' +
      link("rooms", "По комнатам →") + '</div>' +
      category_cards(home_categories) +
      '</section><section class="home-collection"><div class="section-heading"><h2>Из каталога</h2>' +
      link("catalog", "Все светильники →") + '</div>' +
      product_grid(featured_products or data["products"][:4], filters=False) + '</section>' +
      '<section class="home-rooms"><div class="section-heading"><h2>Свет по комнатам</h2>' +
      link("rooms", "Все комнаты →") + '</div><ul>' +
      "".join(f'<li><a href="/rooms/{key}"><span class="room-number" aria-hidden="true">{index:02}</span>'
              f'<span>{html.escape(name)}</span><span aria-hidden="true">↗</span></a></li>'
              for index, (key, (name, *_)) in enumerate(ROOMS.items(), 1)) +
      '</ul></section><section class="home-ai"><div class="home-ai-photo">'
      '<img src="/scenes/ai-interior.jpg" alt="" width="1536" height="1024" loading="lazy" decoding="async">'
      '<span class="image-caption">Пример интерьера</span></div><div class="home-ai-copy">'
      '<span class="eyebrow">' + nav_icon("spark") + ' Lusar AI</span><h2>Ваш интерьер. Новый свет.</h2>'
      '<p>Загрузите фото комнаты и примерьте светильники из каталога.</p>'
      '<a class="button-link" href="/ai">Начать примерку <span aria-hidden="true">↗</span></a>'
      '</div></section>',
      description="Светильники LUSAR для дома и проектов. Каталог освещения и примерка светильников в вашем интерьере с Lusar AI.")
write("catalog", "Каталог освещения",
      '<div class="section-heading catalog-heading"><h1>Каталог освещения</h1><nav aria-label="Подбор света">' +
      link("rooms", "По комнатам") + link("brands", "Бренды") + '</nav></div>' + category_navigation() +
      '<section class="catalog-products" id="catalog-products" aria-label="Все светильники">' +
      product_grid(sorted(data["products"], key=lambda item: list(categories).index(item["categoryId"]))) + '</section>',
      description="Каталог LUSAR. Люстры, подвесные и настенные светильники, прожекторы и уличное освещение. Цены в армянских драмах.")
for key, category in categories.items():
    children = [(category_path(child), item["name"]) for child, item in categories.items() if item.get("parentId") == key]
    products = [item for item in data["products"] if item["categoryId"] == key]
    body = category_navigation(key)
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
            '<div class="gallery-navigation" hidden><button type="button" data-gallery-step="-1" aria-label="Предыдущее фото">←</button>'
            f'<span id="gallery-counter" aria-live="polite">1 / {len(item["images"])}</span>'
            '<button type="button" data-gallery-step="1" aria-label="Следующее фото">→</button></div>'
            f'<div class="photo-thumbnails">{thumbnails}</div>'
            f'<dialog id="product-photo-dialog" aria-label="Увеличенное фото товара">'
            '<form method="dialog"><button>Закрыть</button></form>'
            f'<img id="product-photo-large" alt="{name}">'
            '<div class="gallery-modal-navigation" hidden><button type="button" data-gallery-step="-1" aria-label="Предыдущее фото">←</button>'
            '<span class="gallery-modal-counter"></span><button type="button" data-gallery-step="1" aria-label="Следующее фото">→</button></div>'
            '</dialog></section>'
            '<script src="/product-gallery.js" defer></script>'
        )
    specs = "".join(f'<dt>{html.escape(a["label"])}</dt><dd>{html.escape(a["value"])} {html.escape(a["unit"])}</dd>' for a in item["attributes"])
    price = display_price(item)
    highlights = [a for a in item["attributes"] if a["label"] in {"Цоколь", "Мощность", "Цветовая температура", "Защита IP", "Диаметр"}][:3]
    highlights_html = '<dl class="product-highlights">' + ''.join(
        f'<div><dt>{html.escape(a["label"])}</dt><dd>{html.escape(a["value"])} {html.escape(a["unit"])}</dd></div>' for a in highlights) + '</dl>' if highlights else ''
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
    related = [candidate for candidate in data["products"] if candidate["categoryId"] == item["categoryId"] and candidate["id"] != item["id"]][:4]
    related_section = ('<section class="related-products"><div class="section-heading"><h2>В этой категории</h2>' +
                       link(category_path(item["categoryId"]), "Все модели →") + '</div>' + product_grid(related, filters=False) + '</section>') if related else ""
    write(product_path(item), item["name"],
          f'<nav class="breadcrumbs" aria-label="Навигация по каталогу">{link("catalog", "Каталог")} <span aria-hidden="true">/</span> '
          f'{link(category_path(item["categoryId"]), categories[item["categoryId"]]["name"])}</nav>'
          f'<section class="product-layout">{photos}<div class="product-info">'
          f'<p class="eyebrow">Артикул {html.escape(item["sku"])}</p>'
          f'<h1 data-locale-source>{html.escape(item["name"])}</h1><p class="product-price">{price}</p>'
          '<p class="availability"><span aria-hidden="true"></span>Наличие уточнит менеджер.</p>' + highlights_html +
          f'<div class="product-actions"><button class="primary-action" type="button" data-add="{html.escape(item["id"], quote=True)}">Добавить в корзину</button>'
          f'<button type="button" data-favorite="{html.escape(item["id"], quote=True)}" aria-pressed="false">{nav_icon("favorites")}<span>В избранное</span></button></div>'
          '<p id="favorite-status" role="status"></p>'
          '<div class="product-secondary-actions">'
          f'<button class="text-button" type="button" data-compare="{html.escape(item["id"], quote=True)}" aria-pressed="false">Сравнить</button>'
          f'{link("compare", "Открыть сравнение")}</div><p id="compare-status" role="status"></p>'
          f'<p role="status" id="cart-status"></p><p id="cart-next" hidden>{link("cart/", "Перейти в корзину")}</p>'
          '<div class="product-ai-note">' + nav_icon("spark") +
          f'<div>{link("ai?product=" + quote(item["id"], safe=""), "Примерить в моей комнате")}'
          '<p>Посмотрите, как светильник впишется в ваш интерьер.</p></div></div>'
          f'<p>{link("support?product=" + quote(item["id"], safe=""), "Уточнить по товару")}</p>'
          '</div></section><div class="product-details"><section><h2>О светильнике</h2>'
          f'<p data-locale-source>{html.escape(item["description"])}</p>{brand_link}</section>'
          f'<section><h2>Характеристики</h2><dl>{specs}</dl></section></div>' + related_section,
          description=" ".join(item["description"].split())[:160],
          image=photo_urls[0] if photo_urls else "", structured_data=structured_data)

for path, title in FOOTER + EXTRA:
    if path in {"ai", "cart", "checkout", "checkout/received", "payment", "sitemap", "account/loyalty", "offers", "search", "favorites", "compare", "brands", "rooms", "order-status", "legal/cookies", "faq", "support", "contacts", "stores", "about"}:
        continue
    children = [(p + "/", name) for p, name in EXTRA if p.rpartition("/")[0] == path]
    write(path, title, '<p>Страница в разработке</p>' + (listing(children) if children else ""), draft=True)
write("payment", "Оплата", '<p class="lead">Выберите удобный способ оплаты при подтверждении заказа.</p>'
      '<div class="info-cards"><section><span class="eyebrow">01</span><h2>В магазине</h2>'
      '<p>После подтверждения заказа менеджером.</p></section><section><span class="eyebrow">02</span>'
      '<h2>По чеку менеджера</h2><p>Менеджер пришлёт данные для оплаты.</p></section>'
      '<section><span class="eyebrow">03</span><h2>При получении</h2>'
      '<p>Способ оплаты согласует менеджер.</p></section></div>')
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
      '<p class="lead">Ждём вас в наших магазинах в Ереване.</p><div class="contact-layout">'
      '<div class="info-cards"><section><span class="eyebrow">01 · LUSAR</span><h2>Аршакуняц</h2>'
      f'<address>{store_address}</address><p>Ярмарка «Еранкюни»</p>{link(store_path, "Как добраться →")}</section>'
      '<section><span class="eyebrow">02 · LUSAR</span><h2>Смбата Зоравара</h2>'
      f'<address>{d50_address}</address><p>Павильон D50</p>{link(d50_path, "Как добраться →")}</section></div>'
      '<aside class="contact-aside"><p class="eyebrow">На связи</p>' + store_phone +
      f'<p>Ежедневно · {SERVICE_HOURS}</p><p>{link("order-status", "Проверить статус заявки")}</p></aside></div>')
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
      '<div class="faq-layout"><aside><p class="lead">Поможем с заказом и выбором света.</p>' +
      link("support", "Задать вопрос →") + '</aside><div class="faq-list">' +
      "".join(f'<details><summary>{html.escape(question)}</summary><p>{html.escape(answer)}</p></details>'
              for question, answer in FAQ) + '</div></div><p>' +
      link("payment", "Подробнее об оплате") + ' · ' + link("support", "Поддержка") + '</p>')
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
<p>В текущей сборке настройки темы и языка, корзина и избранное сохраняются в браузере.
Выбор статистики можно изменить через «Настройки cookie» в подвале.</p>
""", draft=True)
write("ai", "Lusar AI", (ROOT / "ai-page.html").read_text(encoding="utf-8")
      .replace("<!-- spark-icon -->", nav_icon("spark")).replace("<!-- upload-icon -->", nav_icon("upload")) +
      (f'<p class="ai-telegram"><a href="https://t.me/{AI_TELEGRAM_USERNAME}">Открыть Lusar AI в Telegram</a></p>'
       if AI_TELEGRAM_USERNAME else ""), draft=True)
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
ACCOUNT_VIEWS = {"account": ("Личный кабинет", "overview"), "account/orders": ("Мои заказы", "orders"),
                 "account/addresses": ("Профиль", "settings"), "account/loyalty": ("Мои скидки", "loyalty"),
                 "account/settings": ("Профиль", "settings"), "account/sign-in": ("Вход в LUSAR", "sign-in"),
                 "account/register": ("Регистрация", "register"), "account/recovery": ("Восстановление доступа", "recovery")}
for account_path, (account_title, account_view) in ACCOUNT_VIEWS.items():
    account_body = (ROOT / "account-page.html").read_text(encoding="utf-8").replace("{{title}}", html.escape(account_title)).replace("{{view}}", account_view)
    account_body = re.sub(r"{{icon:([a-z]+)}}", lambda match: nav_icon(match[1]), account_body)
    write(account_path, account_title, account_body, draft=True)


def order_steps(current):
    steps = []
    for index, (icon, name) in enumerate((("cart", "Корзина"), ("account", "Контакты"), ("check", "Подтверждение")), 1):
        state = ' aria-current="step"' if index == current else ' data-complete' if index < current else ''
        content = '<span class="order-step-icon">' + nav_icon(icon) + f'</span><span>{name}</span>'
        content = f'<a href="/cart">{content}</a>' if current == 2 and index == 1 else f'<span>{content}</span>'
        steps.append(f'<li{state}>{content}</li>')
    return '<nav class="order-steps" aria-label="Этапы заявки"><ol>' + "".join(steps) + '</ol></nav>'


def order_summary(checkout=False):
    promo_form = ' form="checkout"' if checkout else ''
    action = ('<button id="checkout-submit" class="primary-action" type="submit" form="checkout">Отправить заявку <span aria-hidden="true">↗</span></button>'
              if checkout else '<p id="checkout-link" hidden><a class="button-link" href="/checkout">К оформлению <span aria-hidden="true">→</span></a></p>')
    return ('<aside id="order-summary" class="order-summary" aria-labelledby="order-summary-heading">'
            '<h2 id="order-summary-heading">' + nav_icon("cart") + 'Ваш заказ</h2><dl class="order-totals">'
            '<div><dt>Товары</dt><dd id="order-subtotal">—</dd></div>'
            '<div id="order-account-discount-row" hidden><dt>Скидка кабинета</dt><dd id="order-account-discount">—</dd></div>'
            '<div id="order-first-discount-row" hidden><dt>Скидка на первый заказ</dt><dd id="order-first-discount">—</dd></div>'
            '<div id="order-discount-row" hidden><dt>Скидка по промокоду</dt><dd id="order-discount">—</dd></div></dl>'
            '<div id="account-checkout-benefits" class="account-checkout-benefits" hidden><label for="discount-mode">Выберите скидку</label>'
            '<select id="discount-mode" name="discountMode" form="checkout"><option value="none">Только промокод</option>'
            '<option value="first">10% на первый заказ</option><option value="loyalty">Скидка кабинета и промокод</option></select>'
            '<p id="account-checkout-level"></p></div>'
            '<details class="order-promo"><summary>Промокод <span aria-hidden="true">＋</span></summary>'
            '<label class="visually-hidden" for="order-promo">Промокод</label>'
            f'<input id="order-promo" name="promo"{promo_form} autocomplete="off" maxlength="32" placeholder="Введите промокод" aria-describedby="promo-total">'
            '<p id="promo-total" role="status"></p></details>'
            '<p id="cart-summary" role="status"></p><div class="order-summary-actions">'
            '<div class="order-grand-total"><span>Предварительный итог</span><strong id="order-total">—</strong></div>' + action + '</div>' +
            '<div class="order-payment-info"><p class="order-payment-note">Оплата после подтверждения.</p>'
            '<p class="order-summary-note">Наличие, доставку и итоговую сумму уточнит менеджер.</p>'
            '<a class="order-payment-link" href="/payment">Способы оплаты</a></div></aside>')


def empty_bag():
    return ('<section id="cart-empty" class="cart-empty" hidden><div class="empty-state-copy">'
            '<h2>Корзина пока пуста</h2><p>Вернитесь к выбору света или откройте сохранённые модели.</p>'
            '<div class="empty-state-actions"><a class="button-link" href="/catalog" data-continue-shopping>Продолжить покупки <span aria-hidden="true">→</span></a>'
            '<a class="cart-continue" href="/favorites">Избранное →</a></div></div>'
            '<div class="empty-state-orbit" aria-hidden="true"><span>' + nav_icon("cart") + '</span></div></section>')


write("cart", "Корзина", '<div class="order-page-heading"><h1>Корзина</h1><p id="cart-count"></p>'
      '<div class="order-flow-links cart-return-links">'
      '<a class="cart-continue" href="/catalog" data-continue-shopping>← Продолжить покупки</a>'
      '<a class="cart-continue" href="/favorites">Избранное →</a></div></div>' + order_steps(1) +
      '<div class="order-flow-layout" id="order-flow"><section class="cart-content" aria-label="Товары в корзине">'
      '<div id="cart-items"></div><p id="cart-message" role="status"></p></section>' + order_summary() + '</div>' + empty_bag(), draft=True)
write("favorites", "Избранное", '<div class="order-page-heading"><h1>Избранное</h1>'
      '<a class="cart-continue" href="/cart">Перейти в корзину →</a></div>'
      '<ul id="favorite-items" class="wishlist-grid" aria-label="Избранное"></ul><p id="favorite-status" role="status"></p>'
      '<p id="cart-status" role="status"></p><p id="cart-next" hidden><a href="/cart">Перейти в корзину →</a></p>'
      '<section id="wishlist-empty" class="cart-empty" hidden><div class="empty-state-copy">'
      '<h2>В избранном пока нет товаров.</h2><p>Сохраняйте светильники, к которым хотите вернуться.</p>'
      '<div class="empty-state-actions"><a class="button-link" href="/catalog">Открыть каталог ↗</a></div></div>'
      '<div class="empty-state-orbit" aria-hidden="true"><span>' + nav_icon("favorites") + '</span></div></section>', draft=True)
write("compare", "Сравнение светильников", '<p id="compare-status" role="status"></p>'
      '<div id="compare-table" class="comparison-scroll" role="region" aria-label="Таблица сравнения" tabindex="0"></div>'
      '<p>' + link("catalog", "Открыть каталог") + '</p>', draft=True)
write("checkout", "Оформление заявки", """
<div class="order-page-heading"><h1>Оформление заявки</h1><p id="checkout-account-mode">Без регистрации</p></div>
""" + order_steps(2) + """
<div class="order-flow-layout" id="order-flow">
<section class="checkout-content">
<form id="checkout" hidden>
  <div class="checkout-form-heading"><span class="eyebrow">01</span><h2>Как с вами связаться</h2></div>
  <p class="checkout-form-note">Укажите имя и телефон. Остальное — по желанию.</p>
  <a id="checkout-sign-in" href="/auth/start?return=/checkout" hidden>Войти и использовать скидку кабинета</a>
  <div class="checkout-fields">
    <label>Имя <input name="name" autocomplete="name" required maxlength="120" placeholder="Ваше имя"></label>
    <label>Телефон <input name="phone" type="tel" autocomplete="tel" inputmode="tel" required maxlength="40" placeholder="+374" aria-describedby="phone-help"></label>
  </div>
  <p id="phone-help" class="visually-hidden">Позвоним, чтобы подтвердить заявку.</p>
  <details class="checkout-optional"><summary>Email и адрес (необязательно)<span aria-hidden="true">＋</span></summary>
    <div class="checkout-fields">
      <label>Email (необязательно) <input name="email" type="email" autocomplete="email" maxlength="254" placeholder="name@example.com"></label>
      <label>Адрес (необязательно) <input name="address" autocomplete="street-address" maxlength="300" placeholder="Город, улица, дом"></label>
    </div>
  </details>
</form>
<details class="checkout-review" open><summary class="checkout-form-heading"><span class="eyebrow">02</span><span>Товары в заявке</span><span class="review-toggle" aria-hidden="true">＋</span></summary>
<div id="cart-items"></div><p id="cart-message" role="status"></p></details>
</section>
""" + order_summary(checkout=True) + '</div>' + empty_bag() +
      '<p id="checkout-status" class="checkout-status" role="status" tabindex="-1"></p>'
      '<section class="checkout-success" id="checkout-success" hidden><h2>Заявка принята</h2>'
      '<p id="checkout-success-number"></p><p>Менеджер свяжется с вами в ближайшее время.</p>'
      f'<p>Часы связи с менеджером: {SERVICE_HOURS}.</p>'
      '<p><a id="order-status-link" hidden>Проверить статус заявки</a></p>'
      '<a href="/catalog">Вернуться в каталог</a></section>', draft=True)
write("checkout/received", "Подтверждение заявки", '<div id="receipt-steps" hidden>' + order_steps(3) + '</div>' + f"""
<section class="receipt-card">
<span class="receipt-symbol" aria-hidden="true" hidden>{nav_icon("check")}</span>
<h1 id="receipt-title">Подтверждение заявки</h1>
<p id="receipt-label" class="receipt-order-label" hidden>Номер заявки</p>
<p id="receipt-number" class="receipt-number" role="status">Здесь появится номер после отправки заявки.</p>
<div id="receipt-details" hidden>
  <p>Менеджер свяжется с вами, чтобы подтвердить наличие, итоговую сумму и способ получения.</p>
  <div class="receipt-contact"><p><span>На связи</span> · <span class="receipt-hours">{SERVICE_HOURS}</span></p>{store_phone}</div>
  <p class="receipt-note">При звонке назовите номер заявки.</p>
  <p><a id="receipt-tracking" class="button-link" hidden>Проверить статус заявки <span aria-hidden="true">↗</span></a></p>
</div>
<div class="receipt-links"><a href="/catalog">Вернуться в каталог</a><a href="/contacts">Контакты</a></div>
</section>
<script src="/receipt.js?v=3" defer></script>
""", draft=True)
write("order-status", "Статус заявки", f"""
<meta name="referrer" content="no-referrer">
<section class="receipt-card tracking-card">
  <span class="receipt-symbol" aria-hidden="true">{nav_icon("orders")}</span>
  <h1>Статус заявки</h1>
  <p id="guest-order-status" role="status">Откройте приватную ссылку, выданную после оформления заявки.</p>
  <div class="receipt-links"><a href="/account/orders">Мои заказы</a><a href="/contacts">Контакты</a></div>
</section>
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
for asset in ("staff.css", "staff.js"):
    (OUT / asset).write_bytes((ROOT / asset).read_bytes())
(OUT / "theme.js").write_bytes((ROOT / "theme.js").read_bytes())
(OUT / "locale.js").write_bytes((ROOT / "locale.js").read_bytes())
(OUT / "cookie-settings.js").write_bytes((ROOT / "cookie-settings.js").read_bytes())
(OUT / "analytics.js").write_bytes((ROOT / "analytics.js").read_bytes())
(OUT / "scenes.js").write_bytes((ROOT / "scenes.js").read_bytes())
(OUT / "site-nav.js").write_bytes((ROOT / "site-nav.js").read_bytes())
(OUT / "catalog-live.js").write_bytes((ROOT / "catalog-live.js").read_bytes())
(OUT / "account-session.js").write_bytes((ROOT / "account-session.js").read_bytes())
(OUT / "account-page.js").write_bytes((ROOT / "account-page.js").read_bytes())
(OUT / "favicon.svg").write_bytes((ROOT / "favicon.svg").read_bytes())
(OUT / "order-status.js").write_bytes((ROOT / "order-status.js").read_bytes())
(OUT / "receipt.js").write_bytes((ROOT / "receipt.js").read_bytes())
(OUT / "product-gallery.js").write_bytes((ROOT / "product-gallery.js").read_bytes())
(OUT / "product-filters.js").write_bytes((ROOT / "product-filters.js").read_bytes())
(OUT / "ai-preview.js").write_text(
    "const aiProducts = " + json.dumps({
        item["id"]: {"name": item["name"], "path": "/" + product_path(item).rstrip("/"),
                     "image": item["images"][0]["url"] if item["images"] else ""}
        for item in data["products"]
    }, ensure_ascii=False) + ";\n" + (ROOT / "ai-preview.js").read_text(encoding="utf-8"), encoding="utf-8"
)
(OUT / "scenes").mkdir(exist_ok=True)
for name in ("lusar-hero.webp", "lusar-scene-day.webp", "lusar-scene-evening.webp", "ai-interior.jpg"):
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
                     "sku": item["sku"], "attributes": item["attributes"],
                     "image": item["images"][min(1, len(item["images"]) - 1)]["url"] if item["images"] else ""}
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
