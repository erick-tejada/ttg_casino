# -*- coding: utf-8 -*-
"""Lectura del reporte "Slot Analysis" exportado desde DRGT.

DRGT exporta el reporte como hoja de cálculo XML de Excel 2003 (SpreadsheetML) con
extensión .xls. También se aceptan .xlsx y .xls binarios, por si el archivo se
vuelve a guardar desde Excel.

Estructura esperada: una fila de encabezados (Position, Inventory #, ..., NGWINE, ...),
una fila por máquina y una fila de totales. Todo lo que venga después (por ejemplo el
cuadro de ajustes que el auditor agrega a mano) se ignora.
"""
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET

# Encabezado DRGT -> (campo, es_texto)
COLUMNS = {
    'Position': ('position', True),
    'Inventory #': ('inventory', True),
    'Serial #': ('serial', True),
    'Manufacturer': ('manufacturer', True),
    'Model': ('model_name', True),
    'Game': ('game', True),
    'EGM Audit': ('egm_audit', False),
    'Audit': ('audit', False),
    'NGWINE': ('ngwine', False),
    'TAP': ('tap', False),
    'CRE': ('cre', False),
    'GTIE': ('gtie', False),
    'GTOE': ('gtoe', False),
    'GJOE': ('gjoe', False),
    'GTIN': ('gtin', False),
    'GTINE': ('gtine', False),
    'GP': ('gp', False),
    'BDIE': ('bdie', False),
    'CCOE': ('ccoe', False),
    'PWE': ('pwe', False),
    'CLIC': ('clic', False),
    'CLOC': ('cloc', False),
    'Avg. Bet': ('avg_bet', False),
    'Retention %': ('retention', False),
    'ET': ('et', False),
    'ST': ('st', False),
}
NUMERIC_FIELDS = sorted(field for field, is_text in COLUMNS.values() if not is_text)
REQUIRED_HEADERS = ('Position', 'Inventory #', 'NGWINE', 'CRE', 'BDIE')
# Totales que se comparan contra la fila de totales del archivo, si existe.
CHECKED_TOTALS = ('ngwine', 'bdie', 'cre')

SS_NS = 'urn:schemas-microsoft-com:office:spreadsheet'


class SlotMeterFileError(Exception):
    """Error de formato del archivo, con mensaje listo para el usuario."""


def _norm_header(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def _to_text(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def to_number(value):
    """Convierte el texto de una celda en número. Vacío -> 0.0. No numérico -> None."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(',', '')
    if not text:
        return 0.0
    if text.startswith('(') and text.endswith(')'):
        text = '-' + text[1:-1]
    try:
        return float(text)
    except ValueError:
        return None


def _rows_spreadsheetml(content):
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise SlotMeterFileError('El archivo no se pudo leer como hoja de Excel (XML): %s' % e)
    ns = {'ss': SS_NS}
    sheet = root.find('.//ss:Worksheet', ns)
    if sheet is None:
        raise SlotMeterFileError('El archivo no contiene ninguna hoja.')
    rows = []
    for row in sheet.findall('.//ss:Table/ss:Row', ns):
        cells = []
        for cell in row.findall('ss:Cell', ns):
            index = cell.get('{%s}Index' % SS_NS)
            if index:
                while len(cells) < int(index) - 1:
                    cells.append('')
            data = cell.find('ss:Data', ns)
            cells.append(data.text if data is not None and data.text is not None else '')
        rows.append(cells)
    return rows


def _rows_xlsx(content):
    try:
        import openpyxl
    except ImportError:
        raise SlotMeterFileError('No se pueden leer archivos .xlsx en este servidor. Exporte el reporte de DRGT sin modificarlo.')
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    return [[c for c in row] for row in ws.iter_rows(values_only=True)]


def _rows_xls(content):
    try:
        import xlrd
    except ImportError:
        raise SlotMeterFileError('No se pueden leer archivos .xls binarios en este servidor. Exporte el reporte de DRGT sin modificarlo.')
    try:
        book = xlrd.open_workbook(file_contents=content)
    except Exception as e:  # xlrd lanza varios tipos de error
        raise SlotMeterFileError('El archivo no se pudo leer como hoja de Excel: %s' % e)
    sheet = book.sheet_by_index(0)
    return [sheet.row_values(i) for i in range(sheet.nrows)]


def read_rows(content):
    head = content[:512].lstrip()
    if head.startswith(b'\xef\xbb\xbf'):
        head = head[3:]
    if head.startswith(b'<'):
        return _rows_spreadsheetml(content)
    if content[:2] == b'PK':
        return _rows_xlsx(content)
    if content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        return _rows_xls(content)
    raise SlotMeterFileError('Formato de archivo no reconocido. Use el reporte "Slot Analysis" exportado desde DRGT.')


def _is_machine_row(record):
    position = record.get('position', '')
    inventory = record.get('inventory', '')
    if not position or to_number(position) is not None:
        # La fila de totales trae conteos numéricos en la columna de posición.
        return False
    num = to_number(inventory)
    return num is not None and inventory != '' and float(num).is_integer()


def parse(content):
    """Devuelve dict(lines=[...], totals={...}, fingerprint=str).

    Cada línea trae los campos de COLUMNS (texto o número), 'inventory_code' (int)
    y 'extra' con las columnas no reconocidas.
    """
    rows = read_rows(content)
    header_idx = None
    for i, row in enumerate(rows):
        names = {_norm_header(c) for c in row}
        if 'Inventory #' in names and 'NGWINE' in names:
            header_idx = i
            break
    if header_idx is None:
        raise SlotMeterFileError('No se encontró la fila de encabezados del reporte (columnas "Inventory #" y "NGWINE"). '
                                 'Verifique que sea el reporte "Slot Analysis" de DRGT.')
    headers = [_norm_header(c) for c in rows[header_idx]]
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        raise SlotMeterFileError('Al archivo le faltan columnas obligatorias: %s.' % ', '.join(missing))

    lines = []
    total_row = None
    started = False
    for row_number, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        record, extra = {}, {}
        for col, header in enumerate(headers):
            if not header:
                continue
            value = row[col] if col < len(row) else ''
            if header in COLUMNS:
                field, is_text = COLUMNS[header]
                record[field] = _to_text(value) if is_text else value
            else:
                extra[header] = _to_text(value)
        if not any(_to_text(v) for v in record.values()):
            if started:
                break
            continue
        if not _is_machine_row(record):
            if started:
                total_row = record
                break
            continue
        started = True
        for header, (field, is_text) in COLUMNS.items():
            if is_text:
                record.setdefault(field, '')
                continue
            number = to_number(record.get(field))
            if number is None:
                raise SlotMeterFileError('Fila %s (máquina %s): el valor "%s" de la columna %s no es un número.'
                                         % (row_number, record.get('inventory'), record.get(field), header))
            record[field] = number
        record['inventory_code'] = int(to_number(record['inventory']) or 0)
        record['extra'] = extra
        lines.append(record)

    if not lines:
        raise SlotMeterFileError('El archivo no contiene líneas de máquinas.')

    seen, duplicated = set(), set()
    for line in lines:
        code = line['inventory_code']
        (duplicated if code in seen else seen).add(code)
    if duplicated:
        raise SlotMeterFileError('El archivo trae máquinas repetidas: %s.' % ', '.join(str(c) for c in sorted(duplicated)))

    totals = {f: round(sum(line[f] for line in lines), 2) for f in CHECKED_TOTALS}
    if total_row:
        header_by_field = {field: header for header, (field, _t) in COLUMNS.items()}
        for field in CHECKED_TOTALS:
            file_total = to_number(total_row.get(field))
            if file_total is not None and abs(file_total - totals[field]) > 0.05:
                raise SlotMeterFileError(
                    'La suma de la columna %s (%.2f) no coincide con el total del archivo (%.2f). '
                    'Puede que falten filas; vuelva a exportar el reporte.' % (header_by_field[field], totals[field], file_total))

    canonical = json.dumps([[line['inventory_code']] + [round(line[f], 4) for f in NUMERIC_FIELDS]
                            for line in sorted(lines, key=lambda l: l['inventory_code'])])
    return {
        'lines': lines,
        'totals': totals,
        'fingerprint': hashlib.sha256(canonical.encode()).hexdigest(),
    }

