#!/usr/bin/env python3
"""
Generates the full Technical Specification (ТЗ/СТПО) PDF for the Decision Hub project.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "ТЗ_Decision_Hub.pdf")

# ── Register TTF fonts with Cyrillic support ─────────────────────────────────
_FONT_DIR = "/System/Library/Fonts/Supplemental"
pdfmetrics.registerFont(TTFont("Arial",           f"{_FONT_DIR}/Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold",      f"{_FONT_DIR}/Arial Bold.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic",    f"{_FONT_DIR}/Arial Italic.ttf"))
pdfmetrics.registerFont(TTFont("Arial-BoldItalic",f"{_FONT_DIR}/Arial Bold Italic.ttf"))
pdfmetrics.registerFont(TTFont("CourierNew",      f"{_FONT_DIR}/Courier New.ttf"))
pdfmetrics.registerFont(TTFont("CourierNew-Bold", f"{_FONT_DIR}/Courier New Bold.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Arial", normal="Arial", bold="Arial-Bold",
                   italic="Arial-Italic", boldItalic="Arial-BoldItalic")

# ── Colors ──────────────────────────────────────────────────────────────────
C_DARK    = colors.HexColor("#1a1a2e")
C_BLUE    = colors.HexColor("#16213e")
C_ACCENT  = colors.HexColor("#0f3460")
C_LIGHT   = colors.HexColor("#e94560")
C_TABLE_H = colors.HexColor("#0f3460")
C_TABLE_R = colors.HexColor("#f0f4f8")
C_TABLE_A = colors.HexColor("#dce8f5")
C_BORDER  = colors.HexColor("#b0c4de")
C_CODE_BG = colors.HexColor("#f5f5f5")
C_WARN    = colors.HexColor("#fff3cd")
C_WARN_B  = colors.HexColor("#ffc107")
C_TEXT    = colors.HexColor("#1a1a2e")

# ── Styles ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    base = kw.pop("base", "Normal")
    s = ParagraphStyle(name, parent=styles[base], **kw)
    return s

H1 = S("H1", fontSize=22, leading=28, textColor=C_DARK, spaceAfter=6, spaceBefore=18,
        fontName="Arial-Bold")
H2 = S("H2", fontSize=16, leading=22, textColor=C_ACCENT, spaceAfter=4, spaceBefore=14,
        fontName="Arial-Bold", borderPad=4)
H3 = S("H3", fontSize=13, leading=18, textColor=C_DARK, spaceAfter=3, spaceBefore=10,
        fontName="Arial-Bold")
H4 = S("H4", fontSize=11, leading=15, textColor=C_ACCENT, spaceAfter=2, spaceBefore=8,
        fontName="Arial-Bold")
BODY = S("BODY", fontSize=10, leading=15, textColor=C_TEXT, spaceAfter=4,
         alignment=TA_JUSTIFY, fontName="Arial")
BODY_L = S("BODY_L", fontSize=10, leading=15, textColor=C_TEXT, spaceAfter=4,
           alignment=TA_LEFT, fontName="Arial")
MONO = S("MONO", fontSize=8.5, leading=13, textColor=colors.HexColor("#2d2d2d"),
         fontName="CourierNew", backColor=C_CODE_BG, spaceAfter=4,
         leftIndent=8, rightIndent=8, borderPad=6)
BULLET = S("BULLET", fontSize=10, leading=15, textColor=C_TEXT, spaceAfter=2,
           leftIndent=16, fontName="Arial", bulletIndent=6)
CAPTION = S("CAPTION", fontSize=8, leading=11, textColor=colors.grey,
            alignment=TA_CENTER, fontName="Arial-Italic")
COVER_TITLE = S("COVER_TITLE", fontSize=32, leading=40, textColor=colors.white,
                alignment=TA_CENTER, fontName="Arial-Bold")
COVER_SUB = S("COVER_SUB", fontSize=14, leading=20, textColor=colors.HexColor("#aaccff"),
               alignment=TA_CENTER, fontName="Arial")
COVER_META = S("COVER_META", fontSize=10, leading=14, textColor=colors.HexColor("#ccddff"),
                alignment=TA_CENTER, fontName="Arial")
TOC_H = S("TOC_H", fontSize=11, leading=16, textColor=C_ACCENT, fontName="Arial-Bold",
           spaceAfter=2)
TOC_E = S("TOC_E", fontSize=10, leading=14, textColor=C_TEXT, fontName="Arial",
           leftIndent=12, spaceAfter=1)
TOC_E2 = S("TOC_E2", fontSize=9.5, leading=13, textColor=colors.HexColor("#555555"),
            fontName="Arial", leftIndent=28, spaceAfter=1)
LABEL = S("LABEL", fontSize=9, leading=12, textColor=colors.HexColor("#555555"),
          fontName="Arial-Italic")
WARN = S("WARN", fontSize=10, leading=14, textColor=colors.HexColor("#7d5a00"),
         fontName="Arial", backColor=C_WARN, leftIndent=10, borderPad=8)


def hr():
    return HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=6, spaceBefore=6)

def thin_hr():
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd"),
                      spaceAfter=4, spaceBefore=4)

def sp(h=6):
    return Spacer(1, h)

def p(text, style=BODY):
    return Paragraph(text, style)

def h1(text): return Paragraph(text, H1)
def h2(text): return Paragraph(text, H2)
def h3(text): return Paragraph(text, H3)
def h4(text): return Paragraph(text, H4)
def mono(text): return Paragraph(text.replace(" ", "&nbsp;").replace("\n", "<br/>"), MONO)
def bullet(text): return Paragraph(f"• &nbsp;{text}", BULLET)
def warn(text): return Paragraph(f"⚠ {text}", WARN)
def label(text): return Paragraph(text, LABEL)


def make_table(headers, rows, col_widths=None, stripe=True):
    data = [[Paragraph(str(h), S("TH", fontSize=9, fontName="Arial-Bold",
                                  textColor=colors.white, leading=12)) for h in headers]]
    for i, row in enumerate(rows):
        bg = C_TABLE_A if (stripe and i % 2 == 0) else colors.white
        data.append([Paragraph(str(c), S(f"TD{i}", fontSize=9, fontName="Arial",
                                          textColor=C_TEXT, leading=13)) for c in row])
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_TABLE_H),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_TABLE_A, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(style)
    return t


def cover_page(story):
    # Dark cover background via a table
    cover_data = [[""]]
    cover_table = Table(cover_data, colWidths=[17*cm], rowHeights=[3*cm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
    ]))

    header_data = [[
        Paragraph("ТЕХНИЧЕСКОЕ ЗАДАНИЕ", S("CT1", fontSize=11, fontName="Arial-Bold",
                                            textColor=colors.HexColor("#aaccff"), alignment=TA_CENTER)),
    ]]
    ht = Table(header_data, colWidths=[17*cm])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    title_data = [[
        Paragraph("Decision Hub", S("CT2", fontSize=38, fontName="Arial-Bold",
                                     textColor=colors.white, alignment=TA_CENTER, leading=46)),
    ]]
    tt = Table(title_data, colWidths=[17*cm])
    tt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 30),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    sub_data = [[
        Paragraph("Централизованный движок бизнес-решений<br/>для банковских операций",
                  S("CT3", fontSize=14, fontName="Arial", textColor=colors.HexColor("#88bbff"),
                     alignment=TA_CENTER, leading=20)),
    ]]
    st = Table(sub_data, colWidths=[17*cm])
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 30),
    ]))

    meta_rows = [
        ["Документ:", "Спецификация требований к программному обеспечению (СТПО)"],
        ["Версия:", "1.0"],
        ["Статус:", "Финальный"],
        ["Дата:", "2026-03-26"],
        ["Аудитория:", "Разработчики, системные аналитики, архитекторы"],
        ["Кодовое имя:", "decision-hub-sandbox"],
    ]
    meta_data = [[
        Paragraph(r[0], S(f"ML{i}", fontSize=9, fontName="Arial-Bold",
                          textColor=colors.HexColor("#aaccff"))),
        Paragraph(r[1], S(f"MR{i}", fontSize=9, fontName="Arial",
                          textColor=colors.white)),
    ] for i, r in enumerate(meta_rows)]
    mt = Table(meta_data, colWidths=[4*cm, 13*cm])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_BLUE),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#334477")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))

    story += [ht, tt, st, sp(10), mt, PageBreak()]


def toc_page(story):
    story.append(h1("Содержание"))
    story.append(hr())
    story.append(sp(4))

    toc = [
        ("1.", "Введение и назначение системы", None),
        ("1.1", "Контекст и проблематика", None),
        ("1.2", "Цели проекта", None),
        ("1.3", "Термины и определения", None),
        ("2.", "Архитектура системы", None),
        ("2.1", "Высокоуровневая схема", None),
        ("2.2", "Граница ответственности сервисов", None),
        ("2.3", "Принципы проектирования", None),
        ("3.", "Требования к базе данных", None),
        ("3.1", "Схема таблиц: payment-service", None),
        ("3.2", "Схема таблиц: decision-hub", None),
        ("3.3", "Схема таблиц: ledger-mock", None),
        ("4.", "Требования к сервисам", None),
        ("4.1", "api-gateway (:8000)", None),
        ("4.2", "payment-service (:8001)", None),
        ("4.3", "decision-hub (:8002)", None),
        ("4.4", "ledger-mock (:8003)", None),
        ("5.", "API-контракты", None),
        ("5.1", "POST /api/p2p/transfer", None),
        ("5.2", "POST /api/p2p/transfer-legacy", None),
        ("5.3", "POST /decision/evaluate", None),
        ("5.4", "GET /decision/rules + PATCH /decision/rules/{rule_id}", None),
        ("5.5", "GET /decision/audit/{decision_id}", None),
        ("5.6", "POST /ledger/posting", None),
        ("6.", "Логика принятия решений", None),
        ("6.1", "Правила в seed-данных", None),
        ("6.2", "Стратегия вычисления", None),
        ("6.3", "Типы условий", None),
        ("7.", "Нефункциональные требования", None),
        ("7.1", "Идемпотентность", None),
        ("7.2", "Структурированное логирование", None),
        ("7.3", "Propagation X-Correlation-Id", None),
        ("8.", "Статус-машина перевода", None),
        ("9.", "Shared-библиотека", None),
        ("10.", "Конфигурация и деплой", None),
        ("10.1", "Переменные окружения", None),
        ("10.2", "Docker Compose", None),
        ("10.3", "Alembic-миграции", None),
        ("11.", "Структура репозитория", None),
        ("12.", "Демо-сценарии (4 шт.)", None),
        ("13.", "Антипаттерн AS-IS vs TO-BE", None),
        ("14.", "Критерии приёмки", None),
    ]

    for num, title, _ in toc:
        is_top = num.endswith(".") and len(num) <= 3
        indent = 0 if is_top else 16
        fn = "Arial-Bold" if is_top else "Arial"
        fs = 11 if is_top else 10
        tc = C_ACCENT if is_top else C_TEXT
        story.append(Paragraph(
            f'{num}&nbsp;&nbsp;{title}',
            S(f"toc_{num}", fontSize=fs, leading=16, fontName=fn,
              textColor=tc, leftIndent=indent, spaceAfter=2)
        ))

    story.append(PageBreak())


def section_1(story):
    story.append(h1("1. Введение и назначение системы"))
    story.append(hr())

    story.append(h2("1.1 Контекст и проблематика"))
    story.append(p(
        "В большинстве банков бизнес-логика принятия решений (лимиты, AML-проверки, "
        "антифрод) рассеяна по десяткам сервисов в виде хардкодированных условий: "
        "<font name='CourierNew' size='9'>if amount &gt; 10_000_000: reject</font>. "
        "Это приводит к системным проблемам:"
    ))
    for item in [
        "Нет объяснимости: невозможно ответить на вопрос «какое именно правило сработало?»",
        "Нет владельца: правило AML живёт в коде инженера — не в компетенции комплаенс-отдела",
        "Нет версионирования: изменение порога — это коммит, PR, деплой, CAB-согласование",
        "Дублирование: каждый сервис реализует одни и те же проверки независимо",
        "Нет аудита: решение принято, но записи нет — регулятор спросит, ответить нечем",
        "Тестирование сложно: правило нельзя проверить без поднятия всего сервиса",
    ]:
        story.append(bullet(item))

    story.append(sp(8))
    story.append(p(
        "Настоящая спецификация описывает архитектуру <b>Decision Hub</b> — "
        "централизованного движка решений, который решает все перечисленные проблемы. "
        "Система реализуется как production-like sandbox для обучения системных "
        "аналитиков думать на уровне инженеров."
    ))

    story.append(h2("1.2 Цели проекта"))
    goals = [
        ["#", "Цель", "Метрика успеха"],
        ["1", "Вынести решения из кода сервисов в данные", "PATCH правила без деплоя — за < 1 сек"],
        ["2", "Обеспечить объяснимость каждого решения", "Каждый reject содержит rule_id + owner + reason_code"],
        ["3", "Создать неизменяемый аудит-трейл", "100% решений записаны в decision_audit"],
        ["4", "Исключить дублирование проводки (идемпотентность)", "Повтор запроса с тем же ключом → один posting"],
        ["5", "Явная статус-машина перевода", "Все переходы логируются с correlation_id"],
        ["6", "Сравнить AS-IS и TO-BE архитектуру", "endpoint /p2p/transfer-legacy демонстрирует антипаттерн"],
    ]
    story.append(make_table(goals[0], goals[1:], col_widths=[1*cm, 8*cm, 8*cm]))

    story.append(h2("1.3 Термины и определения"))
    terms = [
        ["Термин", "Определение"],
        ["Decision Hub", "Сервис, владеющий правилами и их вычислением. Не знает о переводах."],
        ["Rule (правило)", "Запись в БД: условие + действие + владелец. Меняется без деплоя."],
        ["REJECT", "Решение, блокирующее операцию. Первый REJECT останавливает обработку."],
        ["CHALLENGE", "Мягкий флаг: операция разрешена, но требует ручной проверки. Накапливается."],
        ["APPROVE", "Решение без ограничений: все правила проверены, ни одно не сработало."],
        ["Idempotency-Key", "Клиентский UUID в заголовке. Гарантирует, что повтор не создаст второй перевод."],
        ["X-Correlation-Id", "UUID, сгенерированный api-gateway. Сквозной ID для трассировки через все сервисы."],
        ["decision_audit", "Неизменяемая таблица. Каждое вычисление пишет snapshot контекста и результат."],
        ["Ledger Posting", "Факт проводки денег. DECIDED ≠ POSTED: они независимые события."],
        ["AS-IS", "Антипаттерн: решения внутри сервиса в виде if-else. Намеренно реализован для сравнения."],
        ["TO-BE", "Целевая архитектура: сервис делегирует решение Decision Hub."],
    ]
    story.append(make_table(terms[0], terms[1:], col_widths=[4*cm, 13*cm]))
    story.append(PageBreak())


def section_2(story):
    story.append(h1("2. Архитектура системы"))
    story.append(hr())

    story.append(h2("2.1 Высокоуровневая схема"))
    story.append(p("Система состоит из 4 сервисов и одного экземпляра PostgreSQL 16:"))
    story.append(sp(4))

    arch = (
        "Client (curl / mobile app)\n"
        "       │\n"
        "       ▼\n"
        "api-gateway     :8000   ─── X-Correlation-Id injection, routing, NO business logic\n"
        "       │\n"
        "       ▼\n"
        "payment-service :8001   ─── transfer lifecycle, idempotency, status machine\n"
        "       │                        │\n"
        "       ▼                        ▼\n"
        "decision-hub    :8002   ledger-mock  :8003\n"
        "rules as data,          posting simulation,\n"
        "audit trail,            fail-on-demand\n"
        "explainability\n"
        "\n"
        "─────────────── PostgreSQL 16 ──────────────────\n"
        "payment_transfers   payment_idempotency\n"
        "decision_rules      decision_audit\n"
        "ledger_postings"
    )
    story.append(mono(arch))

    story.append(h2("2.2 Граница ответственности сервисов"))
    resp = [
        ["Сервис", "Владеет", "НЕ владеет"],
        ["api-gateway", "Context propagation, routing, rate-limit headers", "Любая бизнес-логика"],
        ["payment-service", "Сущность Transfer, переходы статусов, идемпотентность", "Логика решений"],
        ["decision-hub", "Правила, движок вычисления, аудит-трейл", "Состояние перевода"],
        ["ledger-mock", "Симуляция проводки денег", "Решения, статус перевода"],
    ]
    story.append(make_table(resp[0], resp[1:], col_widths=[4*cm, 7*cm, 6*cm]))

    story.append(h2("2.3 Принципы проектирования"))
    principles = [
        ("<b>API-first:</b> OpenAPI-контракты написаны до кода и являются единственным источником правды об интерфейсе.",),
        ("<b>Ownership over integration:</b> сервис либо владеет данными, либо запрашивает решение — никогда оба сразу.",),
        ("<b>Rules as data:</b> бизнес-правила хранятся в базе данных, не в коде. Изменение — PATCH-запрос, не деплой.",),
        ("<b>Explicit state machine:</b> все переходы статусов перевода явные, логируются, не имеют неявных путей.",),
        ("<b>Immutable audit:</b> каждое решение записывается в decision_audit с полным snapshot контекста. Запись не обновляется.",),
        ("<b>Idempotency by design:</b> повторный запрос с тем же Idempotency-Key возвращает кэшированный ответ — клиент не может отличить retry от оригинала.",),
        ("<b>Structured logging everywhere:</b> каждая строка лога — JSON-объект с обязательными полями service, correlation_id, event.",),
    ]
    for pr in principles:
        story.append(bullet(pr[0]))
    story.append(PageBreak())


def section_3(story):
    story.append(h1("3. Требования к базе данных"))
    story.append(hr())
    story.append(p(
        "Все сервисы используют один инстанс PostgreSQL 16. Схема разделена по "
        "префиксам таблиц, чтобы явно показать владение данными. Миграции управляются "
        "Alembic (per-service, каждый сервис мигрирует свои таблицы при старте)."
    ))

    story.append(h2("3.1 Таблицы payment-service"))

    story.append(h3("payment_transfers"))
    pt = [
        ["Колонка", "Тип", "Ограничение", "Описание"],
        ["id", "UUID", "PK", "Идентификатор перевода"],
        ["idempotency_key", "VARCHAR", "UNIQUE NOT NULL", "Клиентский ключ идемпотентности"],
        ["client_id", "VARCHAR", "NOT NULL", "Идентификатор отправителя"],
        ["receiver_id", "VARCHAR", "NOT NULL", "Идентификатор получателя"],
        ["amount", "NUMERIC(18,2)", "NOT NULL", "Сумма перевода"],
        ["currency", "VARCHAR(3)", "NOT NULL", "Валюта (ISO 4217: KZT, USD...)"],
        ["country", "VARCHAR(2)", "NOT NULL", "Страна назначения (ISO 3166-1 alpha-2)"],
        ["device_trust", "VARCHAR", "NOT NULL", "Уровень доверия устройству: HIGH | MEDIUM | LOW"],
        ["daily_sum", "NUMERIC(18,2)", "NOT NULL", "Сумма переводов за сегодня до текущего"],
        ["status", "VARCHAR", "NOT NULL", "NEW | DECIDED | POSTED | REJECTED | FAILED"],
        ["decision_id", "UUID", "NULLABLE", "Ссылка на decision_audit.decision_id"],
        ["correlation_id", "VARCHAR", "NULLABLE", "X-Correlation-Id от api-gateway"],
        ["created_at", "TIMESTAMPTZ", "NOT NULL", "Время создания записи"],
        ["updated_at", "TIMESTAMPTZ", "NOT NULL", "Время последнего обновления"],
    ]
    story.append(make_table(pt[0], pt[1:], col_widths=[4*cm, 3.5*cm, 3.5*cm, 6*cm]))

    story.append(sp(8))
    story.append(h3("payment_idempotency"))
    pi = [
        ["Колонка", "Тип", "Ограничение", "Описание"],
        ["idempotency_key", "VARCHAR", "PK", "Тот же ключ, что в заголовке Idempotency-Key"],
        ["transfer_id", "UUID", "NOT NULL", "Ссылка на payment_transfers.id"],
        ["response_snapshot", "JSONB", "NOT NULL", "Полный HTTP-ответ первого запроса (кэш для replay)"],
        ["created_at", "TIMESTAMPTZ", "NOT NULL", "Время первого запроса"],
    ]
    story.append(make_table(pi[0], pi[1:], col_widths=[4.5*cm, 3*cm, 3*cm, 6.5*cm]))
    story.append(p(
        "<b>Зачем отдельная таблица идемпотентности?</b> Хранение полного response_snapshot "
        "позволяет вернуть клиенту ровно тот же ответ при повторе — включая transfer_id, "
        "статус, decision-данные. Уникальный ключ по idempotency_key исключает race condition "
        "при параллельных запросах."
    ))

    story.append(h2("3.2 Таблицы decision-hub"))

    story.append(h3("decision_rules"))
    dr = [
        ["Колонка", "Тип", "Ограничение", "Описание"],
        ["rule_id", "VARCHAR", "PK", "Человекочитаемый идентификатор: LIMIT_DAILY, AML_102..."],
        ["version", "VARCHAR", "NOT NULL", "Семантическая версия правила: 1.0, 2.1..."],
        ["priority", "INTEGER", "NOT NULL", "Порядок вычисления (меньше = раньше). 1 = высший."],
        ["active", "BOOLEAN", "NOT NULL", "Активно ли правило. False = исключено из вычисления."],
        ["condition_type", "VARCHAR", "NOT NULL", "THRESHOLD | BLOCKLIST | COMPOSITE"],
        ["condition_params", "JSONB", "NOT NULL", "Параметры условия (зависят от condition_type)"],
        ["action", "VARCHAR", "NOT NULL", "Что делать при срабатывании: REJECT | CHALLENGE | APPROVE"],
        ["reason_code", "VARCHAR", "NOT NULL", "Машиночитаемый код причины: AML_COUNTRY_BLOCKED"],
        ["owner", "VARCHAR", "NOT NULL", "Команда-владелец: compliance | risk | fincontrol"],
        ["updated_at", "TIMESTAMPTZ", "NOT NULL", "Время последнего изменения правила"],
    ]
    story.append(make_table(dr[0], dr[1:], col_widths=[3.5*cm, 2.5*cm, 2.5*cm, 8.5*cm]))

    story.append(sp(8))
    story.append(h3("decision_audit"))
    da = [
        ["Колонка", "Тип", "Ограничение", "Описание"],
        ["id", "UUID", "PK", "Внутренний идентификатор записи"],
        ["decision_id", "UUID", "NOT NULL, INDEX", "Внешний идентификатор решения. По нему делают GET /audit/{id}"],
        ["transfer_context", "JSONB", "NOT NULL", "Полный snapshot входных данных (amount, country, device_trust...)"],
        ["rules_checked", "JSONB", "NOT NULL", "Список [{rule_id, matched, action, priority}] всех проверенных правил"],
        ["rules_matched", "JSONB", "NOT NULL", "Только сработавшие правила [{rule_id, reason_code, owner, action}]"],
        ["final_decision", "VARCHAR", "NOT NULL", "APPROVE | REJECT | CHALLENGE"],
        ["risk_score", "NUMERIC(4,2)", "NULLABLE", "Числовой сигнал риска 0.0–1.0. NULL = чистый APPROVE."],
        ["correlation_id", "VARCHAR", "NULLABLE", "X-Correlation-Id для трассировки"],
        ["created_at", "TIMESTAMPTZ", "NOT NULL", "Время создания записи. НЕИЗМЕНЯЕМО."],
    ]
    story.append(make_table(da[0], da[1:], col_widths=[3.5*cm, 2.5*cm, 2.5*cm, 8.5*cm]))
    story.append(warn(
        "Таблица decision_audit — ТОЛЬКО на запись. Записи не обновляются и не удаляются. "
        "Она является аудиторским журналом: каждое вычисление правил должно создавать новую запись."
    ))

    story.append(h2("3.3 Таблицы ledger-mock"))
    story.append(h3("ledger_postings"))
    lp = [
        ["Колонка", "Тип", "Ограничение", "Описание"],
        ["id", "UUID", "PK", "Идентификатор проводки"],
        ["transfer_id", "UUID", "UNIQUE NOT NULL", "Ссылка на перевод. UNIQUE — идемпотентность на уровне ledger."],
        ["amount", "NUMERIC(18,2)", "NOT NULL", "Сумма проводки"],
        ["currency", "VARCHAR(3)", "NOT NULL", "Валюта"],
        ["status", "VARCHAR", "NOT NULL", "POSTED | FAILED"],
        ["correlation_id", "VARCHAR", "NULLABLE", "X-Correlation-Id для трассировки"],
        ["created_at", "TIMESTAMPTZ", "NOT NULL", "Время создания проводки"],
    ]
    story.append(make_table(lp[0], lp[1:], col_widths=[3.5*cm, 2.5*cm, 2.5*cm, 8.5*cm]))
    story.append(p(
        "<b>UNIQUE на transfer_id</b> — ключевое ограничение. Если payment-service вызывает "
        "ledger дважды с тем же transfer_id (сбой сети + retry), второй вызов возвращает "
        "существующую проводку вместо создания новой. Это защита от двойного списания на уровне БД."
    ))
    story.append(PageBreak())


def section_4(story):
    story.append(h1("4. Требования к сервисам"))
    story.append(hr())

    # 4.1 api-gateway
    story.append(h2("4.1 api-gateway (:8000)"))
    story.append(p(
        "<b>Ответственность:</b> принимает все внешние запросы, инжектирует X-Correlation-Id, "
        "проксирует на payment-service. Не содержит бизнес-логики."
    ))
    story.append(h4("Требования к реализации:"))
    for req in [
        "Реализован на FastAPI + Uvicorn, Python 3.12",
        "Для каждого входящего запроса: если X-Correlation-Id отсутствует — генерировать UUID4 и добавить в заголовок",
        "Добавлять в ответ заголовки: X-Correlation-Id, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset",
        "Проксировать POST /api/p2p/transfer → payment-service:8001/p2p/transfer",
        "Проксировать POST /api/p2p/transfer-legacy → payment-service:8001/p2p/transfer-legacy",
        "Пробрасывать заголовки: Idempotency-Key, Content-Type, X-Fail-Mode, X-Correlation-Id",
        "GET /health: возвращать {\"status\": \"ok\", \"service\": \"api-gateway\"}",
        "При ошибке downstream: пробрасывать статус-код и тело ошибки без изменений",
        "Не хранить состояние. Не подключаться к БД.",
    ]:
        story.append(bullet(req))

    story.append(h4("Среда:"))
    story.append(mono("PAYMENT_SERVICE_URL=http://payment-service:8001"))

    story.append(sp(8))

    # 4.2 payment-service
    story.append(h2("4.2 payment-service (:8001)"))
    story.append(p(
        "<b>Ответственность:</b> создаёт и управляет сущностью Transfer. "
        "Делегирует решение в decision-hub. Делегирует проводку в ledger-mock. "
        "Управляет идемпотентностью. Не содержит логики принятия решений."
    ))
    story.append(h4("Маршруты:"))
    routes_ps = [
        ["Метод", "Путь", "Описание"],
        ["POST", "/p2p/transfer", "TO-BE: 8-шаговый flow через Decision Hub"],
        ["POST", "/p2p/transfer-legacy", "AS-IS: антипаттерн с inline if-else (для сравнения)"],
        ["GET", "/p2p/transfers/{id}", "Получить текущее состояние перевода по UUID"],
        ["GET", "/health", "Health check с проверкой подключения к БД"],
    ]
    story.append(make_table(routes_ps[0], routes_ps[1:], col_widths=[2*cm, 6*cm, 9*cm]))

    story.append(h4("TO-BE flow (POST /p2p/transfer) — 8 шагов:"))
    steps = [
        "1. Проверить наличие Idempotency-Key в заголовке → 400 IDEMPOTENCY_KEY_MISSING если отсутствует",
        "2. Проверить таблицу payment_idempotency → если ключ найден, вернуть response_snapshot (HTTP 200, idempotent: true)",
        "3. Создать запись PaymentTransfer со статусом NEW, сохранить в БД",
        "4. Вызвать decision-hub POST /decision/evaluate → при сетевой ошибке: NEW→FAILED, сохранить идемпотентность, HTTP 503",
        "5. Если decision=REJECT: NEW→REJECTED, сохранить идемпотентность, вернуть ответ со структурированными причинами",
        "6. Если decision=APPROVE|CHALLENGE: NEW→DECIDED",
        "7. Вызвать ledger-mock POST /ledger/posting → при ошибке: DECIDED→FAILED",
        "8. При успехе: DECIDED→POSTED, сохранить идемпотентность, вернуть финальный ответ",
    ]
    for s in steps:
        story.append(bullet(s))

    story.append(h4("Требования:"))
    for req in [
        "Каждый переход статуса логировать как JSON: {event: status_transition, from_status, to_status, transfer_id, correlation_id}",
        "CorrelationMiddleware с generate_if_missing=False (gateway генерирует, сервис только читает)",
        "Timeout при обращении к decision-hub: 10 секунд",
        "Timeout при обращении к ledger-mock: 12 секунд",
        "Идемпотентность должна работать для всех конечных состояний: REJECTED, FAILED, POSTED",
    ]:
        story.append(bullet(req))

    story.append(sp(8))

    # 4.3 decision-hub
    story.append(h2("4.3 decision-hub (:8002)"))
    story.append(p(
        "<b>Ответственность:</b> хранит правила, вычисляет их против переданного контекста, "
        "записывает аудит-трейл. Не знает о сущности Transfer."
    ))
    story.append(h4("Маршруты:"))
    routes_dh = [
        ["Метод", "Путь", "Описание"],
        ["POST", "/decision/evaluate", "Запустить движок правил. Записать аудит."],
        ["GET", "/decision/rules", "Список всех правил с полными параметрами"],
        ["PATCH", "/decision/rules/{rule_id}", "Обновить active и/или condition_params. Без деплоя."],
        ["GET", "/decision/audit/{decision_id}", "Получить полную запись аудита по decision_id"],
        ["GET", "/health", "Health check с проверкой подключения к БД"],
    ]
    story.append(make_table(routes_dh[0], routes_dh[1:], col_widths=[2*cm, 6*cm, 9*cm]))

    story.append(h4("Требования к движку:"))
    for req in [
        "Правила загружаются из БД при каждом вызове /decision/evaluate (не кешируются в памяти — изменения сразу видны)",
        "Правила сортируются по полю priority ASC перед вычислением",
        "Вычисляются только правила с active=True",
        "Первый REJECT останавливает вычисление (early exit)",
        "CHALLENGE-правила накапливаются и не останавливают вычисление",
        "Аудит-запись создаётся для КАЖДОГО вызова, включая APPROVE",
        "decision_id генерируется в evaluate, записывается в аудит, возвращается клиенту",
    ]:
        story.append(bullet(req))

    story.append(sp(8))

    # 4.4 ledger-mock
    story.append(h2("4.4 ledger-mock (:8003)"))
    story.append(p(
        "<b>Ответственность:</b> симулирует факт движения денег. Реализует идемпотентность "
        "на уровне transfer_id. Поддерживает управляемые режимы сбоя для тестирования."
    ))
    story.append(h4("Маршруты:"))
    routes_lm = [
        ["Метод", "Путь", "Описание"],
        ["POST", "/ledger/posting", "Создать проводку. Идемпотентно по transfer_id."],
        ["GET", "/health", "Health check"],
    ]
    story.append(make_table(routes_lm[0], routes_lm[1:], col_widths=[2*cm, 5*cm, 10*cm]))

    story.append(h4("Управляемые сбои (X-Fail-Mode):"))
    fail = [
        ["Значение", "Поведение"],
        ["(отсутствует)", "Нормальная работа: создать posting, вернуть 200"],
        ["TIMEOUT", "asyncio.sleep(5 сек), затем успешный ответ — имитация медленного ledger"],
        ["ERROR", "Немедленный HTTP 500 Internal Server Error"],
        ["DUPLICATE_TEST", "Вернуть существующий posting если transfer_id уже есть (тест идемпотентности)"],
    ]
    story.append(make_table(fail[0], fail[1:], col_widths=[4*cm, 13*cm]))
    story.append(PageBreak())


def section_5(story):
    story.append(h1("5. API-контракты"))
    story.append(hr())
    story.append(p(
        "Полные OpenAPI 3.1 спецификации хранятся в каталоге <font name='CourierNew' size='9'>contracts/</font>. "
        "В этом разделе — детальное описание каждого эндпоинта в формате ТЗ."
    ))

    # 5.1
    story.append(h2("5.1 POST /api/p2p/transfer (TO-BE)"))
    story.append(h4("Заголовки запроса:"))
    h_req = [
        ["Заголовок", "Обязателен", "Описание"],
        ["Content-Type", "Да", "application/json"],
        ["Idempotency-Key", "Да", "UUID4, генерируется клиентом. При отсутствии — HTTP 400."],
        ["X-Correlation-Id", "Нет", "Если не передан, api-gateway генерирует и добавляет."],
        ["X-Fail-Mode", "Нет", "Проброс в ledger: TIMEOUT | ERROR | DUPLICATE_TEST"],
    ]
    story.append(make_table(h_req[0], h_req[1:], col_widths=[4.5*cm, 2.5*cm, 10*cm]))

    story.append(h4("Тело запроса:"))
    body_req = [
        ["Поле", "Тип", "Обязателен", "Описание"],
        ["client_id", "string", "Да", "Идентификатор клиента-отправителя"],
        ["receiver_id", "string", "Да", "Идентификатор получателя"],
        ["amount", "float", "Да", "Сумма перевода (> 0)"],
        ["currency", "string", "Да", "ISO 4217: KZT, USD, EUR..."],
        ["country", "string", "Да", "ISO 3166-1 alpha-2: KZ, RU, IR..."],
        ["device_trust", "string", "Да", "HIGH | MEDIUM | LOW"],
        ["daily_sum", "float", "Да", "Накопленная сумма переводов клиента за сегодня"],
    ]
    story.append(make_table(body_req[0], body_req[1:], col_widths=[3*cm, 2*cm, 2.5*cm, 9.5*cm]))

    story.append(h4("Примеры ответов:"))
    story.append(p("<b>HTTP 200 — перевод выполнен (POSTED):</b>"))
    story.append(mono(
        '{\n'
        '  "transfer_id": "uuid-...",\n'
        '  "status": "POSTED",\n'
        '  "idempotent": false,\n'
        '  "decision": {\n'
        '    "decision_id": "uuid-...",\n'
        '    "allowed": true,\n'
        '    "decision": "APPROVE",\n'
        '    "reasons": [],\n'
        '    "risk_score": null,\n'
        '    "rules_evaluated": 3,\n'
        '    "rules_matched": 0\n'
        '  },\n'
        '  "posting": {"posting_id": "uuid-...", "status": "POSTED"},\n'
        '  "correlation_id": "corr-xyz"\n'
        '}'
    ))

    story.append(p("<b>HTTP 200 — отклонён (REJECTED):</b>"))
    story.append(mono(
        '{\n'
        '  "transfer_id": "uuid-...",\n'
        '  "status": "REJECTED",\n'
        '  "idempotent": false,\n'
        '  "decision": {\n'
        '    "decision_id": "uuid-...",\n'
        '    "allowed": false,\n'
        '    "decision": "REJECT",\n'
        '    "reasons": [{\n'
        '      "rule_id": "AML_102",\n'
        '      "reason_code": "AML_COUNTRY_BLOCKED",\n'
        '      "owner": "compliance"\n'
        '    }],\n'
        '    "risk_score": 0.95,\n'
        '    "rules_evaluated": 2,\n'
        '    "rules_matched": 1\n'
        '  },\n'
        '  "correlation_id": "corr-xyz"\n'
        '}'
    ))

    story.append(p("<b>HTTP 400 — отсутствует Idempotency-Key:</b>"))
    story.append(mono(
        '{"error_code": "IDEMPOTENCY_KEY_MISSING", "message": "...", "correlation_id": "...", "service": "payment-service"}'
    ))

    story.append(p("<b>HTTP 503 — decision-hub недоступен:</b>"))
    story.append(mono(
        '{"error_code": "DECISION_HUB_UNAVAILABLE", "transfer_id": "uuid-...", "status": "FAILED", ...}'
    ))

    # 5.2
    story.append(h2("5.2 POST /api/p2p/transfer-legacy (AS-IS)"))
    story.append(p(
        "Антипаттерн-эндпоинт. Та же сигнатура запроса, что и /transfer. "
        "Принципиальное отличие в ответе:"
    ))
    legacy_diff = [
        ["Аспект", "AS-IS (legacy)", "TO-BE (Decision Hub)"],
        ["Отклонение", '{"status": "REJECTED", "reason": "AML_BLOCKED"}', '{"status": "REJECTED", "decision": {"reasons": [{"rule_id": "AML_102", "reason_code": "AML_COUNTRY_BLOCKED", "owner": "compliance"}], ...}}'],
        ["Аудит", "Нет записи", "Запись в decision_audit"],
        ["rule_id", "Нет", "Есть"],
        ["owner", "Нет", "Есть"],
        ["version", "Нет", "Есть (в decision_rules.version)"],
        ["Изменение правила", "Код + деплой", "PATCH /decision/rules/{id}"],
    ]
    story.append(make_table(legacy_diff[0], legacy_diff[1:], col_widths=[4*cm, 6*cm, 7*cm]))

    # 5.3
    story.append(h2("5.3 POST /decision/evaluate"))
    story.append(h4("Запрос:"))
    story.append(mono(
        '{\n'
        '  "decision_type": "P2P_TRANSFER",\n'
        '  "correlation_id": "corr-xyz",\n'
        '  "context": {\n'
        '    "client_id": "...", "receiver_id": "...",\n'
        '    "amount": 50000, "currency": "KZT",\n'
        '    "country": "IR", "device_trust": "HIGH", "daily_sum": 0\n'
        '  }\n'
        '}'
    ))
    story.append(h4("Ответ:"))
    story.append(mono(
        '{\n'
        '  "decision_id": "uuid-...",\n'
        '  "allowed": false,\n'
        '  "decision": "REJECT",\n'
        '  "reasons": [{"rule_id": "AML_102", "reason_code": "AML_COUNTRY_BLOCKED", "owner": "compliance"}],\n'
        '  "risk_score": 0.95,\n'
        '  "rules_evaluated": 2,\n'
        '  "rules_matched": 1\n'
        '}'
    ))

    # 5.4
    story.append(h2("5.4 GET /decision/rules + PATCH /decision/rules/{rule_id}"))
    story.append(p(
        "GET возвращает массив всех правил. PATCH позволяет обновить "
        "active и/или condition_params без деплоя."
    ))
    story.append(h4("Пример PATCH — изменить дневной лимит:"))
    story.append(mono(
        'PATCH /decision/rules/LIMIT_DAILY\n'
        '{\n'
        '  "condition_params": {\n'
        '    "fields": ["daily_sum", "amount"],\n'
        '    "operator": "SUM_GT",\n'
        '    "threshold": 5000000\n'
        '  }\n'
        '}'
    ))
    story.append(p(
        "После PATCH следующий вызов /decision/evaluate немедленно использует новый порог. "
        "Перезапуск сервисов не требуется."
    ))

    # 5.5
    story.append(h2("5.5 GET /decision/audit/{decision_id}"))
    story.append(p("Возвращает полную запись из decision_audit по decision_id:"))
    story.append(mono(
        '{\n'
        '  "decision_id": "uuid-...",\n'
        '  "final_decision": "REJECT",\n'
        '  "risk_score": 0.95,\n'
        '  "correlation_id": "corr-xyz",\n'
        '  "created_at": "2026-03-26T12:00:00Z",\n'
        '  "transfer_context": {"amount": 50000, "country": "IR", ...},\n'
        '  "rules_checked": [\n'
        '    {"rule_id": "LIMIT_DAILY", "matched": false, "action": "REJECT", "priority": 1},\n'
        '    {"rule_id": "AML_102", "matched": true, "action": "REJECT", "priority": 2}\n'
        '  ],\n'
        '  "rules_matched": [{"rule_id": "AML_102", "reason_code": "AML_COUNTRY_BLOCKED", "owner": "compliance"}]\n'
        '}'
    ))

    # 5.6
    story.append(h2("5.6 POST /ledger/posting"))
    story.append(h4("Запрос:"))
    story.append(mono(
        '{\n'
        '  "transfer_id": "uuid-...",\n'
        '  "amount": 50000,\n'
        '  "currency": "KZT",\n'
        '  "correlation_id": "corr-xyz"\n'
        '}'
    ))
    story.append(p(
        "Если posting с данным transfer_id уже существует — возвращает существующую запись (идемпотентность). "
        "Уникальность обеспечивается на уровне БД (UNIQUE на transfer_id в ledger_postings)."
    ))
    story.append(PageBreak())


def section_6(story):
    story.append(h1("6. Логика принятия решений"))
    story.append(hr())

    story.append(h2("6.1 Правила в seed-данных"))
    story.append(p(
        "При первом запуске decision-hub выполняет Alembic-миграцию "
        "<font name='CourierNew' size='9'>002_seed_rules.py</font>, которая идемпотентно "
        "вставляет три начальных правила:"
    ))
    rules = [
        ["rule_id", "version", "priority", "owner", "Условие", "action", "risk_score"],
        ["LIMIT_DAILY", "1.0", "1", "fincontrol",
         "daily_sum + amount > 10 000 000", "REJECT", "0.70"],
        ["AML_102", "2.1", "2", "compliance",
         "country in {IR, KP, CU, SY}", "REJECT", "0.95"],
        ["FRAUD_017", "1.3", "3", "risk",
         "device_trust=LOW AND amount > 200 000", "REJECT", "0.91"],
    ]
    story.append(make_table(rules[0], rules[1:],
                            col_widths=[2.8*cm, 1.8*cm, 1.8*cm, 2.4*cm, 5.5*cm, 1.8*cm, 2*cm]))

    story.append(h4("condition_params для каждого правила:"))
    story.append(p("<b>LIMIT_DAILY:</b>"))
    story.append(mono('{"fields": ["daily_sum", "amount"], "operator": "SUM_GT", "threshold": 10000000}'))
    story.append(p("<b>AML_102:</b>"))
    story.append(mono('{"field": "country", "blocked_values": ["IR", "KP", "CU", "SY"]}'))
    story.append(p("<b>FRAUD_017:</b>"))
    story.append(mono('{"conditions": [{"field": "device_trust", "eq": "LOW"}, {"field": "amount", "gt": 200000}]}'))

    story.append(h2("6.2 Стратегия вычисления"))
    story.append(p("Движок (<font name='CourierNew' size='9'>app/engine/rule_engine.py</font>) реализует следующую логику:"))
    for step in [
        "Правила сортируются по priority ASC перед вычислением",
        "Вычисляются только правила с active=True",
        "Для каждого правила вызывается evaluate_condition(rule, context) → bool",
        "Если правило сработало и action=REJECT → немедленный выход, decision=REJECT",
        "Если правило сработало и action=CHALLENGE → добавляется в список причин, вычисление продолжается",
        "После прохода всех правил: если есть CHALLENGE-причины → decision=CHALLENGE, allowed=True",
        "Если ни одно правило не сработало → decision=APPROVE, allowed=True, risk_score=null",
        "risk_score = максимальный из _RULE_RISK_SCORES для сработавших правил",
    ]:
        story.append(bullet(step))

    story.append(h4("Важно:"))
    story.append(warn(
        "CHALLENGE означает «разрешить, но пометить для ручной проверки». "
        "allowed=True при CHALLENGE — намеренное решение: операция проходит, "
        "но получает флаг для compliance-команды."
    ))

    story.append(h2("6.3 Типы условий (condition_type)"))
    ctypes = [
        ["condition_type", "Описание", "Обязательные поля в condition_params"],
        ["THRESHOLD", "Числовое сравнение. Поддерживает суммирование нескольких полей.",
         "fields: list[str], operator: SUM_GT, threshold: float"],
        ["BLOCKLIST", "Поле должно входить в список запрещённых значений.",
         "field: str, blocked_values: list[str]"],
        ["COMPOSITE", "AND-комбинация нескольких sub-условий. Все должны выполняться.",
         "conditions: [{field, eq?}, {field, gt?}, {field, lt?}]"],
    ]
    story.append(make_table(ctypes[0], ctypes[1:], col_widths=[3*cm, 7*cm, 7*cm]))
    story.append(PageBreak())


def section_7(story):
    story.append(h1("7. Нефункциональные требования"))
    story.append(hr())

    story.append(h2("7.1 Идемпотентность"))
    story.append(p(
        "Идемпотентность — свойство системы, при котором повторный идентичный запрос "
        "не порождает новые сайд-эффекты. В данной системе реализуется на двух уровнях:"
    ))
    story.append(h4("Уровень 1: payment-service (Idempotency-Key)"))
    for req in [
        "Каждый POST /p2p/transfer обязан содержать заголовок Idempotency-Key (UUID4)",
        "При первом запросе: создать transfer, выполнить flow, сохранить response_snapshot в payment_idempotency",
        "При повторном запросе с тем же ключом: вернуть response_snapshot из кэша (HTTP 200, idempotent: true)",
        "Клиент не получает 409 — он получает ровно тот же ответ, что и при первом запросе",
        "Идемпотентность сохраняется для всех конечных состояний: POSTED, REJECTED, FAILED",
    ]:
        story.append(bullet(req))

    story.append(h4("Уровень 2: ledger-mock (UNIQUE на transfer_id)"))
    for req in [
        "Таблица ledger_postings имеет UNIQUE constraint на transfer_id",
        "Если POST /ledger/posting вызван с уже существующим transfer_id — вернуть существующую запись",
        "Это защита от двойного списания даже если payment-service вызовет ledger дважды",
    ]:
        story.append(bullet(req))

    story.append(h2("7.2 Структурированное логирование"))
    story.append(p(
        "Каждая строка лога во всех сервисах — JSON-объект. "
        "Реализуется через <font name='CourierNew' size='9'>shared/logging.py</font> "
        "(JSONFormatter + get_logger)."
    ))
    story.append(h4("Обязательные поля в каждой лог-строке:"))
    log_fields = [
        ["Поле", "Тип", "Описание"],
        ["timestamp", "ISO 8601 UTC", "Время события"],
        ["service", "string", "Имя сервиса: payment-service, decision-hub, ..."],
        ["level", "string", "INFO | WARNING | ERROR"],
        ["correlation_id", "string | null", "X-Correlation-Id для трассировки"],
        ["event", "string", "Машиночитаемый тип события: transfer_created, status_transition, ..."],
    ]
    story.append(make_table(log_fields[0], log_fields[1:], col_widths=[3.5*cm, 3*cm, 10.5*cm]))

    story.append(h4("Пример лог-строки (status_transition):"))
    story.append(mono(
        '{\n'
        '  "timestamp": "2026-03-26T12:00:00.000Z",\n'
        '  "service": "payment-service",\n'
        '  "level": "INFO",\n'
        '  "correlation_id": "corr-abc-123",\n'
        '  "event": "status_transition",\n'
        '  "transfer_id": "uuid-...",\n'
        '  "from_status": "DECIDED",\n'
        '  "to_status": "POSTED"\n'
        '}'
    ))

    story.append(h2("7.3 Propagation X-Correlation-Id"))
    story.append(p("Каждый запрос в системе должен нести X-Correlation-Id для сквозной трассировки:"))
    flow = [
        ["Шаг", "Действие"],
        ["1. Клиент → api-gateway", "Клиент может передать X-Correlation-Id. Если нет — api-gateway генерирует UUID4."],
        ["2. api-gateway → payment-service", "Заголовок пробрасывается как есть."],
        ["3. payment-service → decision-hub", "Передаётся в поле correlation_id тела запроса POST /decision/evaluate."],
        ["4. payment-service → ledger-mock", "Передаётся в заголовке X-Correlation-Id."],
        ["5. Все сервисы", "Сохраняют correlation_id в каждой лог-строке и в записях БД (transfer, audit)."],
    ]
    story.append(make_table(flow[0], flow[1:], col_widths=[5.5*cm, 11.5*cm]))

    story.append(p(
        "Реализуется через <font name='CourierNew' size='9'>ContextVar</font> "
        "в <font name='CourierNew' size='9'>shared/correlation.py</font>: "
        "middleware сохраняет ID в контекст, логгер читает его автоматически при каждом вызове."
    ))
    story.append(PageBreak())


def section_8(story):
    story.append(h1("8. Статус-машина перевода"))
    story.append(hr())

    story.append(p(
        "payment-service является единственным владельцем статуса перевода. "
        "Статус — явный, хранится в payment_transfers.status. "
        "Нет неявных переходов. Нет статуса «в процессе»."
    ))

    story.append(h2("Допустимые переходы:"))
    story.append(mono(
        "NEW → DECIDED → POSTED      (happy path: decision approved, ledger success)\n"
        "NEW → DECIDED → FAILED      (decision approved, ledger failed)\n"
        "NEW → REJECTED              (decision hub returned REJECT)\n"
        "NEW → FAILED                (decision hub unreachable)"
    ))

    story.append(sp(8))
    transitions = [
        ["Из статуса", "В статус", "Условие", "Деньги moved?"],
        ["NEW", "DECIDED", "Decision Hub вернул APPROVE или CHALLENGE", "Нет"],
        ["NEW", "REJECTED", "Decision Hub вернул REJECT", "Нет"],
        ["NEW", "FAILED", "Decision Hub недоступен (сетевая ошибка/timeout)", "Нет"],
        ["DECIDED", "POSTED", "Ledger-mock вернул успешный ответ", "ДА"],
        ["DECIDED", "FAILED", "Ledger-mock вернул ошибку или timeout", "Нет"],
    ]
    story.append(make_table(transitions[0], transitions[1:],
                            col_widths=[3*cm, 3*cm, 8*cm, 3*cm]))

    story.append(sp(8))
    story.append(h2("Значение статусов:"))
    statuses = [
        ["Статус", "Смысл", "Деньги переведены?", "Финальный?"],
        ["NEW", "Запись перевода создана, ничего не вычислено", "Нет", "Нет"],
        ["DECIDED", "Decision Hub разрешил, ожидается проводка", "Нет", "Нет"],
        ["POSTED", "Ledger подтвердил проводку", "ДА", "Да"],
        ["REJECTED", "Правило заблокировало перевод", "Нет", "Да"],
        ["FAILED", "Инфраструктурный сбой (любой из вызовов)", "Нет", "Да"],
    ]
    story.append(make_table(statuses[0], statuses[1:],
                            col_widths=[3*cm, 7*cm, 3.5*cm, 3.5*cm]))

    story.append(sp(8))
    story.append(warn(
        "DECIDED ≠ POSTED. Это два разных факта: решение принято и деньги переведены. "
        "В случае сбоя ledger статус DECIDED → FAILED. "
        "Деньги не двигались. Это намеренная архитектурная точность."
    ))
    story.append(PageBreak())


def section_9(story):
    story.append(h1("9. Shared-библиотека"))
    story.append(hr())
    story.append(p(
        "Каталог <font name='CourierNew' size='9'>shared/</font> содержит два модуля, "
        "используемые всеми четырьмя сервисами. При сборке Docker-образов "
        "<font name='CourierNew' size='9'>shared/</font> копируется в "
        "<font name='CourierNew' size='9'>/service/shared/</font> "
        "и добавляется в PYTHONPATH."
    ))

    story.append(h3("shared/logging.py"))
    story.append(p(
        "Предоставляет <font name='CourierNew' size='9'>get_logger(service_name: str)</font> — "
        "возвращает стандартный Python logger с JSONFormatter. Каждый сервис вызывает "
        "один раз при инициализации."
    ))
    story.append(h4("Требования к JSONFormatter:"))
    for req in [
        "Поля timestamp (UTC ISO 8601), service, level, correlation_id, event обязательны в каждой строке",
        "correlation_id читается из ContextVar (shared/correlation.py) — не нужно передавать явно",
        "Дополнительные поля из extra={} добавляются в тот же JSON-объект",
        "Если record.getMessage() не пустой и event не задан явно — использовать как event",
    ]:
        story.append(bullet(req))

    story.append(h3("shared/correlation.py"))
    story.append(p(
        "Управляет X-Correlation-Id через "
        "<font name='CourierNew' size='9'>contextvars.ContextVar</font>."
    ))
    story.append(h4("Требования:"))
    for req in [
        "CorrelationMiddleware(BaseHTTPMiddleware) — при каждом запросе читает X-Correlation-Id из заголовка и сохраняет в ContextVar",
        "Параметр generate_if_missing: bool — если True (decision-hub), генерирует UUID если заголовок отсутствует; если False (payment-service), оставляет None",
        "get_correlation_id() → str | None — возвращает текущее значение из ContextVar",
        "set_correlation_id(value: str) — устанавливает значение вручную",
        "api-gateway устанавливает с generate_if_missing=True",
        "payment-service устанавливает с generate_if_missing=False (gateway уже обеспечил наличие)",
    ]:
        story.append(bullet(req))

    story.append(PageBreak())


def section_10(story):
    story.append(h1("10. Конфигурация и деплой"))
    story.append(hr())

    story.append(h2("10.1 Переменные окружения"))
    env_vars = [
        ["Переменная", "Используется в", "Значение по умолчанию", "Описание"],
        ["DATABASE_URL", "payment-service, decision-hub, ledger-mock",
         "postgresql+asyncpg://user:pass@postgres:5432/bankdb",
         "Строка подключения к PostgreSQL (asyncpg driver)"],
        ["PAYMENT_SERVICE_URL", "api-gateway",
         "http://payment-service:8001",
         "Базовый URL payment-service"],
        ["DECISION_HUB_URL", "payment-service",
         "http://decision-hub:8002",
         "Базовый URL decision-hub"],
        ["LEDGER_URL", "payment-service",
         "http://ledger-mock:8003",
         "Базовый URL ledger-mock"],
        ["LOG_LEVEL", "все сервисы",
         "INFO",
         "Уровень логирования: DEBUG | INFO | WARNING | ERROR"],
    ]
    story.append(make_table(env_vars[0], env_vars[1:],
                            col_widths=[4*cm, 4*cm, 4.5*cm, 4.5*cm]))
    story.append(p(
        "Все переменные хранятся в <font name='CourierNew' size='9'>.env</font> "
        "(не коммитится) на основе "
        "<font name='CourierNew' size='9'>.env.example</font>."
    ))

    story.append(h2("10.2 Docker Compose"))
    story.append(p("Порядок запуска сервисов (зависимости через healthcheck):"))
    story.append(mono(
        "postgres (healthcheck: pg_isready)\n"
        "  ├── decision-hub (depends_on: postgres)\n"
        "  ├── ledger-mock  (depends_on: postgres)\n"
        "  └── payment-service (depends_on: decision-hub, ledger-mock)\n"
        "       └── api-gateway (depends_on: payment-service)"
    ))
    story.append(h4("Требования к Dockerfile каждого сервиса:"))
    for req in [
        "Build context: корень репозитория (не подкаталог сервиса)",
        "COPY shared/ /service/shared/  — до копирования кода сервиса",
        "COPY services/{service-name}/ .  — код сервиса",
        "ENV PYTHONPATH=/service — чтобы from shared.logging import ... работало",
        "CMD: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port {port}",
        "Healthcheck: curl -f http://localhost:{port}/health",
    ]:
        story.append(bullet(req))

    story.append(h2("10.3 Alembic-миграции"))
    story.append(p(
        "Три сервиса (payment-service, decision-hub, ledger-mock) используют Alembic. "
        "Каждый мигрирует только свои таблицы."
    ))
    story.append(h4("Требования к env.py (async):"))
    for req in [
        "Использовать async_engine_from_config + connection.run_sync(do_run_migrations)",
        "DATABASE_URL читать из os.environ['DATABASE_URL']",
        "poolclass=pool.NullPool — не держать пул во время миграции",
        "target_metadata = Base.metadata — импортировать модели явно",
    ]:
        story.append(bullet(req))

    story.append(h4("Структура миграций decision-hub:"))
    story.append(mono(
        "001_create_tables.py  — создать decision_rules, decision_audit\n"
        "002_seed_rules.py     — идемпотентно вставить LIMIT_DAILY, AML_102, FRAUD_017"
    ))
    story.append(warn(
        "002_seed_rules.py должен быть идемпотентным: "
        "перед INSERT проверять существование по rule_id. "
        "Повторный запуск миграции не должен падать с ошибкой дублирования."
    ))
    story.append(PageBreak())


def section_11(story):
    story.append(h1("11. Структура репозитория"))
    story.append(hr())
    story.append(p(
        "Ниже приведена полная структура файлов, которые должны быть созданы. "
        "Каждый файл несёт конкретную ответственность."
    ))
    story.append(mono(
        "/\n"
        "├── docker-compose.yml              # оркестрация 4 сервисов + postgres\n"
        "├── .env.example                    # шаблон переменных окружения\n"
        "│\n"
        "├── shared/                         # общий код для всех сервисов\n"
        "│   ├── __init__.py\n"
        "│   ├── logging.py                  # JSONFormatter + get_logger()\n"
        "│   └── correlation.py              # CorrelationMiddleware + ContextVar\n"
        "│\n"
        "├── contracts/                      # OpenAPI 3.1 (источник правды об API)\n"
        "│   ├── api-gateway.openapi.yaml\n"
        "│   ├── payment-service.openapi.yaml\n"
        "│   ├── decision-hub.openapi.yaml\n"
        "│   └── ledger-mock.openapi.yaml\n"
        "│\n"
        "├── docs/                           # документация\n"
        "│   ├── sequence-legacy.puml        # PlantUML: AS-IS flow\n"
        "│   ├── sequence-v2.puml            # PlantUML: TO-BE flow\n"
        "│   ├── state-machine-transfer.md   # статус-машина перевода\n"
        "│   └── decision-hub-rules.md       # каталог правил\n"
        "│\n"
        "├── scripts/\n"
        "│   └── demo.sh                     # 4 демо-сценария (curl)\n"
        "│\n"
        "└── services/\n"
        "    ├── api-gateway/\n"
        "    │   ├── Dockerfile\n"
        "    │   ├── requirements.txt\n"
        "    │   └── app/\n"
        "    │       ├── main.py             # proxy + correlation injection\n"
        "    │       └── __init__.py\n"
        "    │\n"
        "    ├── payment-service/\n"
        "    │   ├── Dockerfile\n"
        "    │   ├── requirements.txt\n"
        "    │   ├── alembic.ini\n"
        "    │   └── app/\n"
        "    │       ├── main.py\n"
        "    │       ├── models.py           # PaymentTransfer, PaymentIdempotency\n"
        "    │       ├── db/\n"
        "    │       │   ├── database.py     # async engine + get_db\n"
        "    │       │   └── migrations/\n"
        "    │       │       ├── env.py      # async Alembic setup\n"
        "    │       │       └── versions/\n"
        "    │       │           └── 001_create_tables.py\n"
        "    │       ├── routes/\n"
        "    │       │   ├── transfer.py     # TO-BE 8-step flow\n"
        "    │       │   └── transfer_legacy.py  # AS-IS антипаттерн\n"
        "    │       └── services/\n"
        "    │           ├── decision_client.py  # httpx client для decision-hub\n"
        "    │           └── ledger_client.py    # httpx client для ledger-mock\n"
        "    │\n"
        "    ├── decision-hub/\n"
        "    │   ├── Dockerfile\n"
        "    │   ├── requirements.txt\n"
        "    │   ├── alembic.ini\n"
        "    │   └── app/\n"
        "    │       ├── main.py\n"
        "    │       ├── models.py           # DecisionRule, DecisionAudit\n"
        "    │       ├── db/\n"
        "    │       │   ├── database.py\n"
        "    │       │   └── migrations/\n"
        "    │       │       ├── env.py\n"
        "    │       │       └── versions/\n"
        "    │       │           ├── 001_create_tables.py\n"
        "    │       │           └── 002_seed_rules.py\n"
        "    │       ├── engine/\n"
        "    │       │   └── rule_engine.py  # evaluate_condition + run_evaluation\n"
        "    │       └── routes/\n"
        "    │           ├── evaluate.py     # POST /decision/evaluate\n"
        "    │           └── admin.py        # GET/PATCH rules, GET audit\n"
        "    │\n"
        "    └── ledger-mock/\n"
        "        ├── Dockerfile\n"
        "        ├── requirements.txt\n"
        "        ├── alembic.ini\n"
        "        └── app/\n"
        "            ├── main.py             # POST /ledger/posting + fail modes\n"
        "            ├── models.py           # LedgerPosting\n"
        "            └── db/\n"
        "                ├── database.py\n"
        "                └── migrations/\n"
        "                    ├── env.py\n"
        "                    └── versions/\n"
        "                        └── 001_create_tables.py"
    ))
    story.append(PageBreak())


def section_12(story):
    story.append(h1("12. Демо-сценарии"))
    story.append(hr())
    story.append(p(
        "Система должна поддерживать 4 демо-сценария, запускаемых через "
        "<font name='CourierNew' size='9'>./scripts/demo.sh [A|B|C|D]</font> "
        "или все вместе без аргументов."
    ))

    # Scenario A
    story.append(h2("Сценарий A — Объяснимость решения"))
    story.append(p(
        "<b>Вопрос: почему транзакция отклонена?</b><br/>"
        "Демонстрирует разницу между AS-IS и TO-BE ответами при одинаковом входном запросе "
        "(страна: IR — Иран, в списке AML)."
    ))
    story.append(mono(
        "TO-BE: POST /api/p2p/transfer\n"
        "  Ответ: {status: REJECTED, decision: {reasons: [{rule_id: AML_102,\n"
        "          reason_code: AML_COUNTRY_BLOCKED, owner: compliance}], ...}}\n"
        "\n"
        "AS-IS: POST /api/p2p/transfer-legacy\n"
        "  Ответ: {status: REJECTED, reason: AML_BLOCKED}   ← только это"
    ))
    story.append(p(
        "После получения decision_id из TO-BE ответа: "
        "<font name='CourierNew' size='9'>GET /decision/audit/{decision_id}</font> "
        "возвращает полный snapshot: что проверялось, что сработало, кто владелец."
    ))

    # Scenario B
    story.append(h2("Сценарий B — Изменение правила без деплоя"))
    story.append(p(
        "<b>Цель: снизить дневной лимит немедленно, без пересборки образов.</b>"
    ))
    steps_b = [
        "Отправить перевод 500 000 → проходит (500K < 10M лимит)",
        "PATCH /decision/rules/LIMIT_DAILY с threshold: 100000",
        "Тот же перевод 500 000 → отклоняется (500K > 100K новый лимит)",
        "Восстановить оригинальный порог через ещё один PATCH",
    ]
    for s in steps_b:
        story.append(bullet(s))
    story.append(p(
        "Ни один контейнер не перезапускается. "
        "Между шагами 1 и 3 — только один API-вызов."
    ))

    # Scenario C
    story.append(h2("Сценарий C — Идемпотентность"))
    story.append(p(
        "<b>Цель: ретрай не создаёт второй перевод и вторую проводку.</b>"
    ))
    story.append(mono(
        "# Первый запрос\n"
        "POST /api/p2p/transfer  (Idempotency-Key: stable-key-001)\n"
        "Ответ: {transfer_id: uuid-abc, status: POSTED, idempotent: false}\n"
        "\n"
        "# Повторный запрос (симуляция сетевого ретрая)\n"
        "POST /api/p2p/transfer  (Idempotency-Key: stable-key-001, те же данные)\n"
        "Ответ: {transfer_id: uuid-abc, status: POSTED, idempotent: true}"
    ))
    story.append(p(
        "Оба ответа содержат одинаковый transfer_id. "
        "В таблице ledger_postings — одна запись."
    ))

    # Scenario D
    story.append(h2("Сценарий D — Частичный сбой (DECIDED ≠ POSTED)"))
    story.append(p(
        "<b>Цель: показать что decision и проводка — независимые факты.</b>"
    ))
    story.append(mono(
        "# Шаг 1: принудительный сбой ledger\n"
        "POST /api/p2p/transfer  (X-Fail-Mode: ERROR)\n"
        "Ответ: {status: FAILED, decision: {decision: APPROVE, ...}}\n"
        "  → Decision Hub одобрил. Ledger упал. Деньги НЕ двигались.\n"
        "\n"
        "# Шаг 2: повторить без fail mode\n"
        "POST /api/p2p/transfer  (новый Idempotency-Key)\n"
        "Ответ: {status: POSTED, ...}"
    ))
    story.append(PageBreak())


def section_13(story):
    story.append(h1("13. Антипаттерн AS-IS vs TO-BE"))
    story.append(hr())
    story.append(p(
        "Файл <font name='CourierNew' size='9'>services/payment-service/app/routes/transfer_legacy.py</font> "
        "является намеренным антипаттерном. Он существует для образовательного сравнения "
        "и должен оставаться рабочим кодом."
    ))

    story.append(h3("Проблемы, которые демонстрирует transfer_legacy.py:"))
    problems = [
        ["#", "Проблема", "Проявление в коде"],
        ["1", "Логика встроена в сервис", "_AML_BLOCKED_COUNTRIES и _DAILY_LIMIT — константы внутри файла"],
        ["2", "Нет аудит-трейла", "При отклонении не создаётся ни одна запись в БД"],
        ["3", "Нет версионирования", "Версия правила существует только в git blame"],
        ["4", "Нет структуры в ответе", "reason: AML_BLOCKED — строка, не объект"],
        ["5", "Нет владельца", "Кто изменит список стран? Разработчик, не compliance"],
        ["6", "Дублирование логики", "Каждый новый сервис копирует этот if-else"],
        ["7", "Сложное тестирование", "Правило нельзя проверить без HTTP-запроса к сервису"],
    ]
    story.append(make_table(problems[0], problems[1:], col_widths=[1*cm, 5*cm, 11*cm]))

    story.append(sp(8))
    story.append(h3("Сравнительная таблица AS-IS vs TO-BE:"))
    comparison = [
        ["Возможность", "AS-IS (legacy)", "TO-BE (Decision Hub)"],
        ["Где живёт логика решений?", "Внутри сервиса (код)", "decision-hub (данные + движок)"],
        ["Почему отклонено?", "Строка в ответе", "rule_id + reason_code + owner"],
        ["Кто владелец правила?", "Никто / git blame", "Поле owner в каждом правиле"],
        ["Изменить порог", "Код → PR → деплой (дни)", "PATCH /decision/rules (секунды)"],
        ["Аудит-трейл", "Отсутствует", "Таблица decision_audit, каждое решение"],
        ["Версионирование правил", "Git история", "version + updated_at в decision_rules"],
        ["Тестирование изменений", "Деплой на staging", "PATCH + один API-вызов"],
        ["Добавить логику в новый сервис", "Copy-paste (расходится)", "Вызов decision-hub (единый источник)"],
    ]
    story.append(make_table(comparison[0], comparison[1:], col_widths=[5*cm, 5.5*cm, 6.5*cm]))
    story.append(PageBreak())


def section_14(story):
    story.append(h1("14. Критерии приёмки"))
    story.append(hr())
    story.append(p(
        "Система считается реализованной корректно, если все следующие условия выполнены:"
    ))

    story.append(h2("14.1 Функциональные критерии"))
    criteria_f = [
        ["#", "Критерий", "Как проверить"],
        ["F1", "POST /api/p2p/transfer с country=IR возвращает REJECTED с reasons[0].rule_id=AML_102",
         "curl из Сценария A"],
        ["F2", "POST /api/p2p/transfer-legacy с тем же запросом возвращает только {reason: AML_BLOCKED}",
         "Сравнить ответы A"],
        ["F3", "GET /decision/audit/{decision_id} возвращает полный snapshot с rules_checked",
         "Сценарий A, шаг 3"],
        ["F4", "PATCH /decision/rules/LIMIT_DAILY с threshold=100000 немедленно блокирует 500K перевод",
         "Сценарий B"],
        ["F5", "Повторный запрос с тем же Idempotency-Key возвращает idempotent=true, один posting в БД",
         "Сценарий C"],
        ["F6", "POST /api/p2p/transfer с X-Fail-Mode=ERROR возвращает status=FAILED, decision=APPROVE",
         "Сценарий D"],
        ["F7", "Все 4 сервиса возвращают HTTP 200 на GET /health после docker compose up",
         "curl healthchecks"],
        ["F8", "POST /p2p/transfer без Idempotency-Key заголовка → HTTP 400",
         "Прямой вызов"],
    ]
    story.append(make_table(criteria_f[0], criteria_f[1:], col_widths=[1*cm, 8*cm, 8*cm]))

    story.append(h2("14.2 Нефункциональные критерии"))
    criteria_nf = [
        ["#", "Критерий", "Как проверить"],
        ["NF1", "Каждая строка лога — валидный JSON с полями timestamp, service, level, correlation_id, event",
         "docker compose logs | python3 -c \"import sys,json; [json.loads(l) for l in sys.stdin]\""],
        ["NF2", "X-Correlation-Id присутствует во всех лог-строках одного запроса",
         "docker compose logs | grep {correlation_id}"],
        ["NF3", "decision_audit содержит запись для каждого вызова /decision/evaluate (включая APPROVE)",
         "SELECT COUNT(*) FROM decision_audit"],
        ["NF4", "ledger_postings содержит ровно одну запись при повторных запросах с тем же transfer_id",
         "SELECT COUNT(*) FROM ledger_postings WHERE transfer_id=..."],
        ["NF5", "Alembic миграции выполняются без ошибок при каждом docker compose up --build",
         "Проверить логи запуска"],
    ]
    story.append(make_table(criteria_nf[0], criteria_nf[1:], col_widths=[1*cm, 8*cm, 8*cm]))

    story.append(h2("14.3 Команды для запуска и проверки"))
    story.append(mono(
        "# Запуск системы\n"
        "cp .env.example .env\n"
        "docker compose up --build\n"
        "\n"
        "# Проверка здоровья\n"
        "curl http://localhost:8000/health\n"
        "curl http://localhost:8001/health\n"
        "curl http://localhost:8002/health\n"
        "curl http://localhost:8003/health\n"
        "\n"
        "# Запуск всех 4 демо-сценариев\n"
        "./scripts/demo.sh\n"
        "\n"
        "# Или по отдельности\n"
        "./scripts/demo.sh A\n"
        "./scripts/demo.sh B\n"
        "./scripts/demo.sh C\n"
        "./scripts/demo.sh D"
    ))

    story.append(sp(16))
    story.append(hr())
    story.append(p(
        "<b>Конец документа.</b> Версия 1.0 | 2026-03-26 | Decision Hub Sandbox",
        CAPTION
    ))


def build_pdf():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm,
        title="ТЗ Decision Hub",
        author="SA Lab",
        subject="Спецификация требований к программному обеспечению",
    )

    story = []

    cover_page(story)
    toc_page(story)
    section_1(story)
    section_2(story)
    section_3(story)
    section_4(story)
    section_5(story)
    section_6(story)
    section_7(story)
    section_8(story)
    section_9(story)
    section_10(story)
    section_11(story)
    section_12(story)
    section_13(story)
    section_14(story)

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Arial", 8)
        canvas.setFillColor(colors.grey)
        # Footer
        canvas.drawString(2*cm, 1.5*cm, "Decision Hub — СТПО v1.0")
        canvas.drawRightString(A4[0] - 2*cm, 1.5*cm, f"Стр. {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF сгенерирован: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
