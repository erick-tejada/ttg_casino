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
            merge = cell.get('{%s}MergeAcross' % SS_NS)
            if merge:
                # Celdas combinadas: las columnas cubiertas quedan vacías para que las siguientes caigan en su posición.
                cells.extend([''] * int(merge))
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



# ------------------------------------------------------------------------------------------------
# Reporte "Operation Balance" / Overview (RD$) de DRGT
# ------------------------------------------------------------------------------------------------
OVERVIEW_VALUES = {
    'handpay_liability': 'Handpay Liability Movement',
    'variacion_efectivo': 'EFT Cash Liability Movement',
    'credito_maquina': 'Credit Meter Cash Liability Movement',
    'credito_no_efectivo': 'Noncash Credit Meter Liability Movement',
    'egm_win_loss': 'EGM Cash Win/Loss Meters',
}
OVERVIEW_OPTIONAL = ('egm_win_loss', 'credito_no_efectivo')
_PERIOD_RE = re.compile(r'Period:\s*(\d{1,2})\.(\d{1,2})\.(\d{2,4})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{2,4})')


def _period_dates(text):
    import datetime
    m = _PERIOD_RE.search(text or '')
    if not m:
        return None
    parts = [int(g) for g in m.groups()]
    dates = []
    for d, mth, y in (parts[0:3], parts[3:6]):
        if y < 100:
            y += 2000
        try:
            dates.append(datetime.date(y, mth, d))
        except ValueError:
            return None
    return tuple(dates)


def parse_overview(content):
    """Lee el reporte "Operation Balance" (hoja Overview RD$) de DRGT.

    Devuelve dict(period=(fecha_desde, fecha_hasta) o None, values={clave: número}).
    Cada valor se toma de la celda a la derecha de la primera etiqueta que coincide.
    """
    rows = read_rows(content)
    texts = [[_to_text(c) for c in row] for row in rows]
    if not any('overview' in c.lower() for row in texts[:3] for c in row if c):
        raise SlotMeterFileError('El archivo no es el reporte "Operation Balance" (Overview RD$) de DRGT.')
    period = None
    for row in texts[:5]:
        for cell in row:
            period = period or _period_dates(cell)
    values = {}
    for key, label in OVERVIEW_VALUES.items():
        for r, row in enumerate(rows):
            for c, cell in enumerate(texts[r]):
                if cell == label and key not in values:
                    nxt = row[c + 1] if c + 1 < len(row) else None
                    number = to_number(nxt)
                    if number is not None and _to_text(nxt) != '':
                        values[key] = number
        if key not in values and key not in OVERVIEW_OPTIONAL:
            raise SlotMeterFileError('No se encontró "%s" en el reporte Operation Balance.' % label)
    return {'period': period, 'values': values}


# ------------------------------------------------------------------------------------------------
# Reporte de Caja (Cash Desk) de DRGT: cuentas personalizadas de Rifas y Devoluciones
# ------------------------------------------------------------------------------------------------
CASH_DESK_PREFIXES = {
    'rifas': ('RIFA',),
    'devoluciones': ('DEVOLUCION', 'DEVOLUCIÓN'),
}


def parse_cash_desk(content):
    """Lee el reporte de Caja (Cash Desk) de DRGT.

    Devuelve dict(period=(desde, hasta) o None, values={'rifas': x, 'devoluciones': y}, accounts=[(cuenta, monto)]).
    Suma la columna "Movement" de las cuentas cuyo nombre empieza con RIFA / DEVOLUCION.
    """
    rows = read_rows(content)
    texts = [[_to_text(c) for c in row] for row in rows]
    header_idx = None
    for i, row in enumerate(texts):
        names = [_norm_header(c) for c in row]
        if 'Account' in names and 'Movement' in names:
            header_idx = i
            break
    if header_idx is None:
        raise SlotMeterFileError('El archivo no es el reporte de Caja de DRGT (no se encontraron las columnas '
                                 '"Account" y "Movement").')
    names = [_norm_header(c) for c in texts[header_idx]]
    col_account, col_movement = names.index('Account'), names.index('Movement')
    period = None
    for row in texts[:header_idx + 1]:
        for cell in row:
            period = period or _period_dates(cell)
    values = dict.fromkeys(CASH_DESK_PREFIXES, 0.0)
    accounts = []
    for r in range(header_idx + 1, len(rows)):
        name = texts[r][col_account] if col_account < len(texts[r]) else ''
        upper = name.upper()
        for key, prefixes in CASH_DESK_PREFIXES.items():
            if upper.startswith(prefixes):
                raw = rows[r][col_movement] if col_movement < len(rows[r]) else None
                number = to_number('0' if _to_text(raw) in ('', '-') else raw)
                if number is None:
                    raise SlotMeterFileError('El monto de la cuenta "%s" no es un número: %s' % (name, raw))
                values[key] += number
                accounts.append((name, number))
    return {'period': period, 'values': {k: round(v, 2) for k, v in values.items()}, 'accounts': accounts}


# ------------------------------------------------------------------------------------------------
# Mesas: reporte "Table Result" de DRGT
# ------------------------------------------------------------------------------------------------
_USD_RE = re.compile(r'^\s*(-?[\d,]+(?:\.\d+)?)\s*\(\s*(-?[\d,]+(?:\.\d+)?)\s*RD\$\s*\)\s*$')
TABLE_COMMON = {'Table': 'table_code', 'Game': 'game', 'Net Opening': 'net_opening', 'Net Closing': 'net_closing',
                'Net Fills': 'net_fills'}
TABLE_GROUPS = {
    'Predicted Result': {'Bill RD$': 'pred_bill_dop', 'Amount USD': 'pred_usd', 'Gross Drop': 'pred_gross_drop',
                         'Net Drop': 'pred_net_drop'},
    'Actual Count': {'Bill USD': 'act_usd', 'Bill RD$': 'act_bill_dop', 'Gross Drop': 'act_gross_drop',
                     'Net Drop': 'act_net_drop'},
    'Variance': {'Gross Drop': 'variance_gross_drop'},
}
TABLE_USD_FIELDS = ('pred_usd', 'act_usd')
TABLE_TOTAL_FIELDS = ('net_fills', 'pred_bill_dop', 'pred_gross_drop', 'act_bill_dop', 'act_gross_drop')


def _usd_cell(value):
    """'350.00 (19,950.00 RD$)' -> (350.0, 19950.0); '-' o vacío -> (0, 0)."""
    text = _to_text(value)
    if text in ('', '-'):
        return 0.0, 0.0
    m = _USD_RE.match(text)
    if m:
        return float(m.group(1).replace(',', '')), float(m.group(2).replace(',', ''))
    number = to_number(text)
    if number is None:
        raise SlotMeterFileError('Monto en USD no reconocido: "%s".' % text)
    return number, 0.0


def _num_cell(value, label):
    text = _to_text(value)
    if text in ('', '-'):
        return 0.0
    number = to_number(value)
    if number is None:
        raise SlotMeterFileError('El valor "%s" de %s no es un número.' % (text, label))
    return number


def parse_table_result(content):
    """Lee el reporte de resultados de mesas de DRGT (Predicted Result / Actual Count / Variance).

    Devuelve dict(lines=[...], totals={...}, fingerprint=str). Cada línea trae los montos en RD$ y, para USD,
    el monto en dólares y su equivalente en RD$ según DRGT (pred_usd_dop / act_usd_dop).
    """
    rows = read_rows(content)
    texts = [[_norm_header(_to_text(c)) for c in row] for row in rows]
    header_idx = None
    for i, row in enumerate(texts):
        if 'Table' in row and 'Net Fills' in row:
            header_idx = i
            break
    if header_idx is None or header_idx == 0:
        raise SlotMeterFileError('El archivo no es el reporte de resultados de mesas de DRGT (no se encontraron las '
                                 'columnas "Table" y "Net Fills").')
    groups_row = texts[header_idx - 1]
    headers = texts[header_idx]
    group_of, current = [], None
    for col in range(len(headers)):
        label = groups_row[col] if col < len(groups_row) else ''
        if label:
            current = label
        group_of.append(current)
    columns = {}
    for col, header in enumerate(headers):
        if header in TABLE_COMMON and group_of[col] is None:
            columns[TABLE_COMMON[header]] = col
        elif group_of[col] in TABLE_GROUPS and header in TABLE_GROUPS[group_of[col]]:
            columns[TABLE_GROUPS[group_of[col]][header]] = col
    expected = list(TABLE_COMMON.values()) + [f for g in TABLE_GROUPS.values() for f in g.values()]
    missing = [f for f in expected if f not in columns]
    if missing:
        raise SlotMeterFileError('Al reporte de mesas le faltan columnas (%s). Expórtelo de DRGT sin modificarlo.'
                                 % ', '.join(missing))

    lines, total_row = [], None
    for row_number, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        cell = lambda f: row[columns[f]] if columns[f] < len(row) else ''
        code = _to_text(cell('table_code'))
        if not code:
            continue
        if to_number(code) is not None:
            total_row = row
            break
        line = {'table_code': code, 'game': _to_text(cell('game'))}
        for field in expected:
            if field in ('table_code', 'game'):
                continue
            if field in TABLE_USD_FIELDS:
                line[field], line[field + '_dop'] = _usd_cell(cell(field))
            else:
                line[field] = _num_cell(cell(field), 'la mesa %s (fila %s)' % (code, row_number))
        lines.append(line)
    if not lines:
        raise SlotMeterFileError('El reporte de mesas no contiene mesas.')
    codes = [l['table_code'] for l in lines]
    duplicated = sorted({c for c in codes if codes.count(c) > 1})
    if duplicated:
        raise SlotMeterFileError('El reporte de mesas trae mesas repetidas: %s.' % ', '.join(duplicated))
    totals = {f: round(sum(l[f] for l in lines), 2) for f in TABLE_TOTAL_FIELDS + TABLE_USD_FIELDS}
    if total_row:
        for field in TABLE_TOTAL_FIELDS:
            col = columns[field]
            file_total = _num_cell(total_row[col] if col < len(total_row) else '', 'el total')
            if abs(file_total - totals[field]) > 0.05:
                raise SlotMeterFileError('La suma de las mesas (%.2f) no coincide con el total del archivo (%.2f). '
                                         'Vuelva a exportar el reporte.' % (totals[field], file_total))
    canonical = json.dumps(sorted([[l['table_code']] + [round(l[f], 2) for f in sorted(l) if isinstance(l[f], float)]
                                   for l in lines]))
    return {'lines': lines, 'totals': totals, 'fingerprint': hashlib.sha256(canonical.encode()).hexdigest()}


# ------------------------------------------------------------------------------------------------
# Mesas: reporte "Chip Liability" de DRGT
# ------------------------------------------------------------------------------------------------
_CHIP_RE = re.compile(r'^(.+?)\s+-\s+(-?[\d,]+(?:\.\d+)?)$')
_CHIP_LOCATIONS = {'Cash Desk': 'cash_desk', 'Table': 'table'}


def parse_chip_liability(content):
    """Lee el reporte "Chip Liability" de DRGT: inventario de fichas por ubicación (Caja de Mesas y cada mesa).

    Devuelve dict(period=(desde, hasta) o None, locations=[{type, code, name, lines=[...]}], totals={...}).
    El inventario final de cada línea se calcula (inicial + movimiento) y se valida contra el del archivo.
    """
    rows = read_rows(content)
    texts = [[_norm_header(_to_text(c)) for c in row] for row in rows]
    if not any('Chip Liability' in c for row in texts[:3] for c in row):
        raise SlotMeterFileError('El archivo no es el reporte "Chip Liability" de DRGT.')
    period = None
    for row in texts[:5]:
        for c in row:
            period = period or _period_dates(c)
    header_idx = None
    for i, row in enumerate(texts):
        if 'Beginning Inventory' in row and 'Movement' in row and 'Ending Inventory' in row:
            header_idx = i
            break
    if header_idx is None:
        raise SlotMeterFileError('No se encontraron las columnas Beginning Inventory / Movement / Ending Inventory.')
    head = texts[header_idx]
    cols = {'begin': head.index('Beginning Inventory'), 'move': head.index('Movement'), 'end': head.index('Ending Inventory')}

    def pair(row, key, label):
        col = cols[key]
        qty = _num_cell(row[col] if col < len(row) else '', label)
        amount = _num_cell(row[col + 1] if col + 1 < len(row) else '', label)
        return qty, amount

    locations, current, grand = [], None, None
    for row_number, row in enumerate(rows[header_idx + 2:], start=header_idx + 3):
        first = _to_text(row[0]) if row else ''
        if not first:
            if any(_to_text(c) for c in row):
                grand = row
            continue
        kind = first.split(' - ')[0].strip()
        if kind in _CHIP_LOCATIONS:
            parts = [p.strip() for p in first.split(' - ')]
            current = {'type': _CHIP_LOCATIONS[kind], 'code': parts[-1], 'name': first, 'lines': [],
                       'file_amounts': {k: pair(row, k, first)[1] for k in cols}}
            locations.append(current)
            continue
        m = _CHIP_RE.match(first)
        if not m or current is None:
            raise SlotMeterFileError('Fila %s del Chip Liability no reconocida: "%s".' % (row_number, first))
        label = '%s (%s)' % (first, current['code'])
        bq, ba = pair(row, 'begin', label)
        mq, ma = pair(row, 'move', label)
        eq, ea = pair(row, 'end', label)
        if abs(bq + mq - eq) > 0.001 or abs(ba + ma - ea) > 0.005:
            raise SlotMeterFileError('En %s el inventario final del archivo no es inicial + movimiento.' % label)
        current['lines'].append({'chip_type': m.group(1).strip(), 'denomination': float(m.group(2).replace(',', '')),
                                 'begin_qty': bq, 'begin_amount': ba, 'move_qty': mq, 'move_amount': ma,
                                 'file_end_amount': ea})
    if not locations:
        raise SlotMeterFileError('El Chip Liability no contiene ubicaciones (Caja de Mesas o mesas).')
    for loc in locations:
        for key, field in (('begin', 'begin_amount'), ('move', 'move_amount')):
            total = round(sum(l[field] for l in loc['lines']), 2)
            if abs(total - loc['file_amounts'][key]) > 0.05:
                raise SlotMeterFileError('En %s la suma de las fichas (%.2f) no coincide con el total del archivo (%.2f).'
                                         % (loc['code'], total, loc['file_amounts'][key]))
    totals = {'begin': round(sum(l['begin_amount'] for loc in locations for l in loc['lines']), 2),
              'move': round(sum(l['move_amount'] for loc in locations for l in loc['lines']), 2)}
    totals['end'] = round(totals['begin'] + totals['move'], 2)
    if grand:
        file_begin = _num_cell(grand[cols['begin'] + 1] if cols['begin'] + 1 < len(grand) else '', 'el total')
        if abs(file_begin - totals['begin']) > 0.05:
            raise SlotMeterFileError('La suma del Chip Liability (%.2f) no coincide con el total del archivo (%.2f).'
                                     % (totals['begin'], file_begin))
    return {'period': period, 'locations': locations, 'totals': totals}
