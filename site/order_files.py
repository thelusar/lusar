"""Excel workbooks and printable PDF reports for the order workspace."""
import io
from html import escape
from itertools import chain, islice
from pathlib import Path
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile


XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
SHEET_NAME = 'Заказы'
TEXT_COLUMNS = {'number', 'phone', 'sku', 'product_id', 'source_number'}


def write_xlsx(output, rows):
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet(SHEET_NAME)
    sheet.freeze_panes = 'B2'
    headings = next(rows)
    widths = {'number': 20, 'created': 29, 'name': 26, 'phone': 22, 'email': 32, 'address': 38,
              'product_id': 40, 'product': 52, 'remaining_total_amd': 24, 'payment': 24}
    for index, heading in enumerate(headings, 1):
        column = sheet.column_dimensions[get_column_letter(index)]
        column.width = widths.get(heading, 18)
        if heading in TEXT_COLUMNS:
            column.number_format = '@'
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill('solid', fgColor='27252A')
    last_row = 1
    for last_row, row in enumerate(chain((headings,), rows), 1):
        cells = []
        for value in row:
            if isinstance(value, str):
                cell = WriteOnlyCell(sheet, value=ILLEGAL_CHARACTERS_RE.sub('', value))
                cell.data_type = 's'
            else:
                cell = WriteOnlyCell(sheet, value=value)
            if last_row == 1:
                cell.font = header_font
                cell.fill = header_fill
            cells.append(cell)
        sheet.append(cells)
    sheet.auto_filter.ref = f'A1:{get_column_letter(len(headings))}{last_row}'
    workbook.save(output)


def xlsx_rows(data, max_lines):
    from defusedxml.common import DefusedXmlException
    from openpyxl import load_workbook
    from openpyxl.utils.exceptions import InvalidFileException

    try:
        with ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 128 or sum(member.file_size for member in members) > 16 * 1024 * 1024:
                raise ValueError('Книга Excel слишком большая. Сохраните нужные строки в отдельный файл.')
        workbook = load_workbook(io.BytesIO(data), read_only=True, keep_links=False)
        try:
            sheet = workbook[SHEET_NAME] if SHEET_NAME in workbook.sheetnames else workbook.worksheets[0]
            for index, cells in enumerate(sheet.iter_rows(min_row=1, max_col=32), 1):
                if index > max_lines + 1:
                    raise ValueError(f'В одном файле допускается до {max_lines} строк с товарами.')
                values = []
                for cell in cells:
                    if cell.data_type in {'f', 'e'}:
                        raise ValueError(f'Строка {index}: замените формулы и ошибки на значения.')
                    values.append('' if cell.value is None else str(cell.value))
                while values and not values[-1]:
                    values.pop()
                yield index, values
        finally:
            workbook.close()
    except (BadZipFile, InvalidFileException, DefusedXmlException, ParseError, IndexError, KeyError, TypeError, OSError):
        raise ValueError('Не удалось прочитать книгу Excel. Сохраните её заново в формате .xlsx.') from None


def write_pdf(output, rows):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate

    font = 'LusarDejaVu'
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, str(Path(__file__).with_name('report_fonts') / 'DejaVuSans.ttf')))
    dark = colors.HexColor('#26252A')
    muted = colors.HexColor('#5F5D67')
    width, height = A4
    document = SimpleDocTemplate(output, pagesize=A4, topMargin=90, bottomMargin=46,
                                 leftMargin=32, rightMargin=32, title='Заказы LUSAR', author='LUSAR')
    normal = ParagraphStyle('OrderCell', fontName=font, fontSize=9, leading=13, textColor=dark)
    header = ParagraphStyle('OrderHeader', parent=normal, textColor=colors.white)
    numeric = ParagraphStyle('OrderAmount', parent=normal, alignment=TA_RIGHT)
    labels = [Paragraph(value, header) for value in ('Номер', 'Дата · Ереван', 'Клиент', 'Статус', 'Шт.', 'Сумма, AMD')]
    widths = [88, 79, 144, 82, 34, 90]
    style = [('BACKGROUND', (0, 0), (-1, 0), dark), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
             ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F6F5F7')]),
             ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]

    def page_frame(canvas, _document):
        canvas.setFillColor(dark)
        canvas.setFont(font, 21)
        canvas.drawString(38, height - 47, 'Заказы LUSAR')
        canvas.setFont(font, 9)
        canvas.setFillColor(muted)
        canvas.drawString(38, height - 65, 'Суммы учитывают возвраты · Время Еревана')
        canvas.drawRightString(width - 38, 28, str(canvas.getPageNumber()))

    tables = []
    orders = iter(rows)
    while batch := list(islice(orders, 200)):
        cells = [[Paragraph(escape(str(value)), numeric if index >= 4 else normal)
                  for index, value in enumerate(row)] for row in batch]
        tables.append(LongTable([labels, *cells], colWidths=widths, repeatRows=1, style=style))
    if not tables:
        tables.append(Paragraph('По выбранным условиям заказов нет.', normal))
    document.build(tables, onFirstPage=page_frame, onLaterPages=page_frame)
