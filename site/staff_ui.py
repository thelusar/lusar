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
    "chevron-right": '<path d="m9 6 6 6-6 6"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "transfer": '<path d="M8 20V4m-4 4 4-4 4 4m4-4v16m-4-4 4 4 4-4"/>',
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


def avatar(name, *, label=''):
    words = name.strip().split()
    initials = ''.join(word[0] for word in words[:2]) if len(words) > 1 else (words or ['L'])[0][:2]
    tone = sum(map(ord, name.casefold())) % 4
    accessible = f'role="img" aria-label="{escape(label, quote=True)}" title="{escape(label, quote=True)}"' if label else 'aria-hidden="true"'
    return f'<span class="staff-avatar" data-avatar="{tone}" {accessible}>{escape(initials.upper())}</span>'


def duration(minutes):
    if minutes is None:
        return 'Нет замеров'
    if minutes < 1:
        return '< 1 мин'
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f'{days} д {hours} ч'
    return f'{hours} ч {minutes} мин' if hours else f'{minutes} мин'


def team_sidebar(team, performance):
    if not team:
        return ''
    members = [(user_id, (name or '').strip() or email, role) for user_id, name, email, role in team]
    managers = [member for member in members if member[2] == 'manager']
    managers.sort(key=lambda member: -performance.get(member[0], (0, None))[0])
    avatars = ''.join(avatar(name, label=name) for _, name, _ in members[:5])
    overflow = f'<span class="staff-avatar staff-avatar-extra">+{len(members) - 5}</span>' if len(members) > 5 else ''
    activity = []
    for user_id, name, _ in managers:
        count, minutes = performance.get(user_id, (0, None))
        activity.append(f'<li><span>{escape(name)}<small>{escape(duration(minutes))}</small></span><strong>{count}</strong></li>')
    manager_rows = f'<ul>{"".join(activity)}</ul>' if activity else '<p>Менеджеров с доступом пока нет.</p>'
    return ('<details class="staff-rail-team" id="staff-team-summary" open>'
            f'<summary class="staff-rail-team-title"><strong>Команда</strong><span>{len(members)}</span>{icon("chevron")}</summary>'
            f'<div class="staff-avatar-stack">{avatars}{overflow}</div>'
            '<h3>Менеджеры за 30 дней</h3><p title="Время — медиана от поступления заявки до принятия">'
            'Принято заявок и типичное время ответа</p>'
            f'{manager_rows}<a href="/manager/access">Управление доступом {icon("chevron-right")}</a></details>')


def orders_chart(days, hourly, previous):
    period = len(days)
    total = sum(days.values())
    scale = max(1, (max(days.values()) + 2) // 3)
    height = 120
    points = [(round(600 * index / (period - 1), 1), round(height * (1 - value / (scale * 3)), 1))
              for index, value in enumerate(days.values())]
    line = f'M 0 {points[0][1]}'
    for (left, first), (right, second) in zip(points, points[1:]):
        middle = round((left + right) / 2, 1)
        line += f' C {middle} {first}, {middle} {second}, {right} {second}'
    axes = ''.join(f'<span>{scale * value}</span>' for value in (3, 2, 1, 0))
    labels = ''.join(f'<span>{day:%d.%m}</span>' for index, day in enumerate(days)
                     if period == 7 or index in {0, 7, 14, 21, 29})
    peak = max(hourly, key=hourly.get) if hourly else None
    peak_label = f'{peak:02d}:00–{peak:02d}:59 · заявок {hourly[peak]}' if peak is not None else 'Пока нет данных'
    delta = total - previous
    comparison = f'{delta:+d} к предыдущим {period} дням' if delta else 'Как в предыдущем периоде'
    return (f'<div class="staff-chart-period" data-chart-period="{period}"{" hidden" if period != 7 else ""}>'
            f'<div class="staff-chart-total"><strong>{total}</strong><div><span>Заявок за {period} дней</span>'
            f'<small>{comparison}</small></div></div><div class="staff-chart-layout">'
            f'<div class="staff-chart-axis" aria-hidden="true">{axes}</div>'
            '<div class="staff-chart-plot"><svg viewBox="0 0 600 120" preserveAspectRatio="none" aria-hidden="true">'
            f'<defs><linearGradient id="staff-chart-fill-{period}" x2="0" y2="1" gradientUnits="objectBoundingBox">'
            '<stop offset="0" stop-color="currentColor" stop-opacity=".34"/><stop offset="1" stop-color="currentColor" stop-opacity=".02"/>'
            f'</linearGradient></defs><path d="{line} L 600 120 H 0 Z" fill="url(#staff-chart-fill-{period})"/>'
            f'<path d="{line}" fill="none" stroke="currentColor" stroke-width="2" vector-effect="non-scaling-stroke"/>'
            f'</svg></div><div class="staff-chart-labels" aria-hidden="true">{labels}</div></div>'
            f'<div class="staff-chart-footer"><span>{icon("history")}<span>Самый активный час <strong>{peak_label}</strong></span></span>'
            f'<button type="button" class="staff-days-button" aria-haspopup="dialog" aria-controls="staff-days" hidden>'
            f'По дням {icon("arrow")}</button></div></div>')


def chart_days(days):
    period = len(days)
    rows = ''.join(f'<tr><td><time datetime="{day.isoformat()}">{day:%d.%m.%Y}</time></td><td>{count}</td></tr>'
                   for day, count in reversed(list(days.items())))
    return (f'<table class="staff-chart-data" data-days-period="{period}"{" hidden" if period != 7 else ""}>'
            f'<caption>Последние {period} дней · время Еревана</caption>'
            f'<thead><tr><th scope="col">Дата</th><th scope="col">Заявки</th></tr></thead><tbody>{rows}</tbody></table>')


def orders_overview(counts, dates, queue, analytics):
    today = datetime.now(YEREVAN).date()
    moments = [moment for value in dates if (moment := local_time(value))]
    charts = []
    daily_tables = []
    for period in (7, 30):
        days = {today - timedelta(days=offset): 0 for offset in range(period - 1, -1, -1)}
        hourly = {}
        start = next(iter(days))
        previous_start = start - timedelta(days=period)
        previous = 0
        for moment in moments:
            day = moment.date()
            if day in days:
                days[day] += 1
                hourly[moment.hour] = hourly.get(moment.hour, 0) + 1
            elif previous_start <= day < start:
                previous += 1
        charts.append(orders_chart(days, hourly, previous))
        daily_tables.append(chart_days(days))
    metrics = (
        ('new', 'Новые заявки', 'orders'),
        ('in_progress', 'В работе', 'history'),
        ('completed', 'Выполнено', 'check'),
        ('cancelled', 'Отменено', 'close'),
    )
    tiles = ''.join(
        f'<a class="staff-metric" data-tone="{tone}" href="?view=orders&amp;status={tone}">'
        f'<span class="staff-tile-icon">{icon(symbol)}</span><span>{label}</span><strong>{counts[tone]}</strong></a>'
        for tone, label, symbol in metrics
    )
    pending = ''.join(
        f'<li><a href="#{escape(number, quote=True)}">{avatar(name)}'
        f'<span><strong>{escape(name)}</strong><small>{escape(number)} · {moment:%d.%m} {moment:%H:%M}</small></span>'
        f'{icon("chevron-right")}</a></li>' for number, name, moment in queue
    )
    attention = f'<ul class="staff-queue">{pending}</ul>' if pending else (
        f'<div class="staff-queue-empty">{icon("check")}<span>Все новые заявки обработаны</span></div>')
    reports = ''.join(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
                      f'{escape(name)} {icon("arrow")}</a>' for name, url in analytics)
    visitor_note = 'Визиты и время на сайте доступны в отчётах.' if reports else 'Счётчики для этого окружения не настроены.'
    return ('<div id="staff-overview"><div class="staff-hero"><div class="staff-hero-content">'
            '<p class="staff-eyebrow">Рабочий кабинет</p><h1>Обзор заказов</h1></div>'
            '<div class="staff-hero-actions">'
            f'<a class="staff-button staff-primary" href="?view=orders&amp;status=new">К новым заявкам {icon("chevron-right")}</a>'
            f'<a class="staff-find-link" href="#orders-title">{icon("search")} Найти заказ</a></div>'
            '<div class="staff-hero-light" aria-hidden="true"></div></div>'
            f'<section class="staff-metrics" aria-label="Заказы по статусам">{tiles}</section>'
            '<div class="staff-overview-grid"><section class="staff-surface staff-chart" aria-labelledby="staff-chart-title">'
            '<div class="staff-section-head"><div><h2 id="staff-chart-title">Динамика заказов</h2>'
            '<p>По дням · время Еревана</p></div><div class="staff-period-switch" role="group" aria-label="Период графика" hidden>'
            '<button type="button" data-period="7" aria-pressed="true">7 дней</button>'
            '<button type="button" data-period="30" aria-pressed="false">30 дней</button></div></div>'
            f'{"".join(charts)}</section><div class="staff-surface staff-dashboard-side">'
            '<section class="staff-inbox" aria-labelledby="staff-queue-title"><div class="staff-section-head">'
            f'<h2 id="staff-queue-title">Требуют внимания</h2>{icon("orders")}</div>{attention}'
            '<a class="staff-inbox-link" href="?view=orders&amp;status=new">Все новые заявки →</a></section>'
            '<section class="staff-analytics" aria-labelledby="staff-analytics-title">'
            f'<div><h2 id="staff-analytics-title">Посещаемость</h2><p>{visitor_note}</p></div>'
            f'<div class="staff-report-links">{reports}</div></section></div></div>'
            '<dialog class="staff-days-dialog" id="staff-days" aria-labelledby="staff-days-title">'
            '<header><h2 id="staff-days-title">Заявки по дням</h2><form method="dialog">'
            f'<button class="staff-icon-button" aria-label="Закрыть данные по дням">{icon("close")}</button>'
            f'</form></header><div class="staff-days-scroll">{"".join(daily_tables)}</div></dialog></div>')


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


def layout(title, content, *, actor=None, active=None, role_label='', sidebar=''):
    brand = ('<a class="staff-brand" href="/manager/orders/">'
             '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" aria-hidden="true">'
             '<defs><linearGradient id="staff-gold" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse">'
             '<stop stop-color="#8d632c"/><stop offset=".27" stop-color="#e0ba73"/>'
             '<stop offset=".42" stop-color="#fff2ce"/><stop offset=".57" stop-color="#a77b3e"/>'
             '<stop offset=".76" stop-color="#d6ac64"/><stop offset="1" stop-color="#8b622f"/>'
             '</linearGradient></defs><g stroke="url(#staff-gold)" stroke-width="1.45" stroke-linecap="round">'
             '<path d="M12 2v6m0 8v6M2 12h6m8 0h6M5 5l4 4m6 6 4 4M5 19l4-4m6-6 4-4"/>'
             '<circle cx="12" cy="12" r="3.3"/></g><circle cx="12" cy="12" r="1.1" fill="url(#staff-gold)"/>'
             '</svg><span>LUSAR</span></a>')
    theme = (f'<button id="theme-toggle" class="staff-icon-button" type="button" aria-label="Светлая тема" '
             f'hidden>{icon("theme")}</button>')
    if not actor or not actor.role:
        return (f'<header class="staff-guest-bar">{brand}{theme}</header><main class="staff-gate">'
                f'<div class="staff-surface"><p class="staff-kicker">Рабочее пространство</p>'
                f'<h1>{escape(title)}</h1>{content}</div></main>')
    orders_current = ' aria-current="page"' if active == 'orders' else ''
    overview_current = ' aria-current="page"' if active == 'overview' else ''
    access_current = ' aria-current="page"' if active == 'access' else ''
    transfer_current = ' aria-current="page"' if active == 'transfer' else ''
    transfer = (f'<a href="/manager/orders-transfer"{transfer_current}>{icon("transfer")}Импорт и экспорт</a>'
                if actor.role == 'admin' else '')
    access = (f'<a href="/manager/access"{access_current}>{icon("team")}Сотрудники</a>'
              if actor.role == 'admin' else '')
    display_name = actor.name.strip() or actor.email
    profile = (f'<a class="staff-profile" href="/account" title="{escape(actor.email, quote=True)}">'
               f'{avatar(display_name)}<span><strong>{escape(display_name)}</strong><small>{escape(role_label)}</small></span>'
               f'{icon("chevron-right")}</a>') if actor.id else ''
    return (f'<a class="staff-skip" href="#staff-main">К содержанию</a><div class="staff-workspace">'
            f'<aside class="staff-sidebar"><div class="staff-brand-row">{brand}{theme}</div>{profile}'
            f'<p class="staff-kicker">Рабочие разделы</p>'
            f'<nav class="staff-section-nav" aria-label="Рабочие разделы"><a href="/manager/orders/"{overview_current}>{icon("overview")}Обзор</a>'
            f'<a href="/manager/orders/?view=orders"{orders_current}>{icon("orders")}Заказы</a>{transfer}{access}</nav>'
            f'<div class="staff-team-slot">{sidebar}</div>'
            f'<nav class="staff-sidebar-footer" aria-label="Личные ссылки">'
            f'<a href="/" aria-label="На сайт" title="На сайт">{icon("arrow")}<span>На сайт</span></a></nav></aside>'
            f'<main id="staff-main" class="staff-main" tabindex="-1">{content}</main></div>')
