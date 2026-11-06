"""Shared presentation for the staff workspace."""
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import parse_qs, urlsplit


ICONS = {
    "orders": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 9h6m-6 4h6m-6 4h4"/>',
    "box": '<path d="m3 8 9-5 9 5v9l-9 5-9-5V8zm0 0 9 5 9-5M12 13v9"/>',
    "payment": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h3"/>',
    "history": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "team": '<circle cx="9" cy="8" r="3"/><path d="M3 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2M16 5a3 3 0 0 1 0 6m2 3a4 4 0 0 1 3 4v2"/>',
    "account": '<circle cx="12" cy="8" r="3.5"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/>',
    "arrow": '<path d="M7 17 17 7M7 7h10v10"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "theme": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="5.5"/><path d="m15 15 4 4"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "overview": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "brand": '<circle cx="12" cy="12" r="3"/><path d="M12 1v22M1 12h22M4 4l16 16M4 20 20 4"/>',
}
YEREVAN = timezone(timedelta(hours=4))


def icon(name):
    return ('<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" '
            f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def amount(value):
    return 'Уточняется' if value is None else f'{value:,}'.replace(',', '\u202f') + '\u00a0֏'


def local_time(value):
    try:
        moment = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(YEREVAN)


def timestamp(value):
    moment = local_time(value)
    if moment is None:
        return f'<span>{escape(str(value))}</span>'
    return f'<time datetime="{moment.isoformat()}">{moment:%d.%m.%Y} · {moment:%H:%M}</time>'


def avatar(name):
    words = name.strip().split()
    initials = ''.join(word[0] for word in words[:2]) if len(words) > 1 else (words or ['L'])[0][:2]
    return f'<span class="staff-avatar" aria-hidden="true">{escape(initials.upper())}</span>'


def orders_overview(counts, dates, queue):
    today = datetime.now(YEREVAN).date()
    week = {today - timedelta(days=offset): 0 for offset in range(6, -1, -1)}
    for value in dates:
        moment = local_time(value)
        if moment and moment.date() in week:
            week[moment.date()] += 1
    metrics = (
        ('new', 'Новые заявки', 'orders', counts['new'], 'Ожидают обработки'),
        ('in_progress', 'В работе', 'history', counts['in_progress'], 'Подтверждённые заявки'),
        ('completed', 'Выполнено', 'check', counts['completed'], 'Завершённые заказы'),
        ('', 'За 7 дней', 'overview', sum(week.values()), 'Новые заявки за неделю'),
    )
    tiles = ''.join(
        f'<article class="staff-metric" data-tone="{tone}"><div><h2>{label}</h2>'
        f'<span class="staff-tile-icon">{icon(symbol)}</span></div><strong>{value}</strong><small>{caption}</small></article>'
        for tone, label, symbol, value, caption in metrics
    )
    maximum = max(week.values()) or 1
    columns = ''.join(
        f'<div class="staff-chart-day"><div class="staff-chart-track">'
        f'<meter min="0" max="{maximum}" value="{count}" aria-label="{day:%d.%m} · {count} заявок"></meter></div>'
        f'<span aria-hidden="true">{day:%d.%m}</span></div>' for day, count in week.items()
    )
    pending = ''.join(
        f'<li><a href="#{escape(number, quote=True)}">{avatar(name)}'
        f'<span><strong>{escape(name)}</strong><small>{escape(number)} · {moment:%H:%M}</small></span>{icon("arrow")}</a></li>'
        for number, name, moment in queue
    )
    attention = f'<ul class="staff-queue">{pending}</ul>' if pending else (
        f'<div class="staff-queue-empty">{icon("check")}<span>Все новые заявки обработаны</span></div>')
    return (f'<div id="staff-overview"><section class="staff-metrics" aria-label="Сводка заказов">{tiles}</section>'
            '<div class="staff-overview-grid"><section class="staff-surface staff-chart" aria-labelledby="staff-chart-title">'
            '<div class="staff-section-head"><div><h2 id="staff-chart-title">Динамика заявок</h2>'
            '<p>Заказы по дням · время Еревана</p></div></div>'
            f'<div class="staff-chart-columns">{columns}</div></section>'
            '<section class="staff-surface" aria-labelledby="staff-queue-title"><div class="staff-section-head">'
            '<div><h2 id="staff-queue-title">Требуют внимания</h2><p>Последние новые заявки</p></div>'
            f'</div>{attention}</section></div></div>')


def heading(title, description):
    return f'<div class="staff-heading"><h1>{escape(title)}</h1><p>{escape(description)}</p></div>'


def empty(title, message, icon_name):
    return (f'<div class="staff-empty">{icon(icon_name)}<h2>{escape(title)}</h2>'
            f'<p>{escape(message)}</p></div>')


def notice(handler, messages):
    key = parse_qs(urlsplit(handler.path).query).get('saved', [''])[0]
    if key not in messages:
        return ''
    return f'<p class="staff-notice" role="status">{icon("check")}{escape(messages[key])}</p>'


def layout(title, content, *, actor=None, active=None, role_label=''):
    brand = f'<a class="staff-brand" href="/manager/orders/">{icon("brand")}<span>LUSAR</span></a>'
    theme = (f'<button id="theme-toggle" class="staff-icon-button" type="button" aria-label="Светлая тема" '
             f'hidden>{icon("theme")}</button>')
    if not actor or not actor.role:
        return (f'<header class="staff-guest-bar">{brand}{theme}</header><main class="staff-gate">'
                f'<div class="staff-surface"><p class="staff-kicker">Рабочее пространство</p>'
                f'<h1>{escape(title)}</h1>{content}</div></main>')
    orders_current = ' aria-current="page"' if active == 'orders' else ''
    overview_current = ' aria-current="page"' if active == 'overview' else ''
    access_current = ' aria-current="page"' if active == 'access' else ''
    access = (f'<a href="/manager/access"{access_current}>{icon("team")}Сотрудники</a>'
              if actor.role == 'admin' else '')
    profile = f'<a href="/account">{icon("account")}Мой аккаунт</a>' if actor.id else ''
    display_name = actor.name.strip() or actor.email
    return (f'<a class="staff-skip" href="#staff-main">К содержанию</a><div class="staff-workspace">'
            f'<aside class="staff-sidebar">{brand}<p class="staff-kicker">Управление магазином</p>'
            f'<nav aria-label="Рабочие разделы"><a href="/manager/orders/"{overview_current}>{icon("overview")}Обзор</a>'
            f'<a href="/manager/orders/?view=orders"{orders_current}>{icon("orders")}Заказы</a>{access}</nav>'
            f'<nav class="staff-sidebar-footer" aria-label="Личные ссылки">{profile}'
            f'<a href="/">{icon("arrow")}На сайт</a></nav></aside>'
            f'<div class="staff-body"><header class="staff-topbar"><span>LUSAR <b aria-hidden="true">/</b> Рабочий кабинет</span>'
            f'<div class="staff-session">{theme}<div class="staff-profile" title="{escape(actor.email, quote=True)}">'
            f'{avatar(display_name)}<div><strong>{escape(display_name)}</strong>'
            f'<small>{escape(role_label)}</small></div></div></div></header>'
            f'<main id="staff-main" class="staff-main">{content}</main></div></div>')
