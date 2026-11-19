# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

RESULT_HEADERS = ['Table', 'Game', 'Net Opening', 'Net Closing', 'Net Fills', 'Bill RD$', 'Amount USD', 'Gross Drop',
                  'Net Drop', 'Bill USD', 'Bill RD$', 'Gross Drop', 'Net Drop', 'Gross Drop']


def _c(value, extra=''):
    if value is None:
        return '<Cell%s/>' % extra
    kind = 'String' if isinstance(value, str) else 'Number'
    return '<Cell%s><Data ss:Type="%s">%s</Data></Cell>' % (extra, kind, value)


def _usd(amount, rate=57.0):
    return '%.2f (%s RD$)' % (amount, '{:,.2f}'.format(amount * rate)) if amount else '-'


def build_result(tables, total=True):
    """tables: [(code, game, opening, fills, pred_bill, pred_usd, act_bill, act_usd)] (estructura del archivo de DRGT)."""
    rows = ['<Row>' + _c(None) + _c('Predicted Result', ' ss:Index="6" ss:MergeAcross="3"')
            + _c('Actual Count', ' ss:MergeAcross="3"') + _c('Variance') + '</Row>',
            '<Row>' + ''.join(_c(h) for h in RESULT_HEADERS) + '</Row>']
    sums = [0.0] * 6
    for code, game, opening, fills, pbill, pusd, abill, ausd in tables:
        pgross, agross = pbill + pusd * 57, abill + ausd * 57
        rows.append('<Row>' + ''.join(_c(v if v else '-') if not isinstance(v, str) else _c(v) for v in (
            code, game, opening, opening - fills, fills, pbill, _usd(pusd), pgross, pgross, _usd(ausd), abill,
            agross, agross, pgross - agross)) + '</Row>')
        for i, v in enumerate((fills, pbill, pgross, abill, agross, pusd)):
            sums[i] += v
    if total:
        rows.append('<Row>' + ''.join(_c(v) for v in (len(tables), 1, 0, 0, sums[0], sums[1], _usd(sums[5]), sums[2],
                                                      sums[2], _usd(sums[5]), sums[3], sums[4], sums[4], 0)) + '</Row>')
    return ('<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
            'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="Sheet1"><Table>'
            + ''.join(rows) + '</Table></Worksheet></Workbook>').encode()


def _sc(value, extra=''):
    kind = 'String' if isinstance(value, str) else 'Number'
    return '<ss:Cell%s><ss:Data ss:Type="%s">%s</ss:Data></ss:Cell>' % (extra, kind, value)


def build_chips(date_str, locations):
    """locations: [(header, [(chip, qty_begin, denom, qty_move)])]."""
    rows = ['<ss:Row>' + _sc('Chip Liability (RD$)', ' ss:MergeAcross="6"') + '</ss:Row>',
            '<ss:Row>' + _sc('Period: %s - %s • Account: Jetons' % (date_str, date_str), ' ss:MergeAcross="6"') + '</ss:Row>',
            '<ss:Row><ss:Cell ss:Index="1"><ss:Data ss:Type="String"/></ss:Cell>'
            + _sc('Beginning Inventory', ' ss:MergeAcross="1"') + _sc('Movement', ' ss:MergeAcross="1"')
            + _sc('Ending Inventory', ' ss:MergeAcross="1"') + '</ss:Row>',
            '<ss:Row><ss:Cell/>' + ''.join(_sc(h) for h in ('Count', 'Amount') * 3) + '</ss:Row>']
    grand_b = grand_m = 0.0
    for header, chips in locations:
        b = sum(q * d for _c_, q, d, _m in chips)
        m = sum(mq * d for _c_, _q, d, mq in chips)
        grand_b, grand_m = grand_b + b, grand_m + m
        rows.append('<ss:Row>' + _sc(header) + '<ss:Cell/>' + _sc(b) + '<ss:Cell/>' + _sc(m or '-') + '<ss:Cell/>'
                    + _sc(b + m) + '</ss:Row>')
        for chip, q, d, mq in chips:
            rows.append('<ss:Row>' + _sc('%s - %s' % (chip, '{:,.2f}'.format(d))) + _sc(q) + _sc(q * d)
                        + _sc(mq or '-') + _sc(mq * d or '-') + _sc(q + mq) + _sc((q + mq) * d) + '</ss:Row>')
    rows.append('<ss:Row><ss:Cell/><ss:Cell/>' + _sc(grand_b) + '<ss:Cell/>' + _sc(grand_m) + '<ss:Cell/>'
                + _sc(grand_b + grand_m) + '</ss:Row>')
    return ('<?xml version="1.0"?><ss:Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
            '<ss:Worksheet ss:Name="Chip Liability"><ss:Table>' + ''.join(rows)
            + '</ss:Table></ss:Worksheet></ss:Workbook>').encode()


@tagged('post_install', '-at_install')
class TestMesaAudit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({'tc_comision_percent': 0.0345, 'tc_itbis_percent': 0.0, 'casino_slot_audit_required': False,
                           'casino_mesa_audit_required': True, 'casino_mesa_audit_tolerance': 99.0})
        cls.bj1 = cls.env['casino.mesa'].create({'name': 'BLACK JACK TEST 1', 'drgt_code': 'TBJ01'})
        cls.bj2 = cls.env['casino.mesa'].create({'name': 'BLACK JACK TEST 2', 'drgt_code': 'TBJ02'})
        cls.encargado = cls.env['casino.encargado.caja'].create({'name': 'Encargado Test'})
        cls.auditor = cls.env['res.users'].create({
            'name': 'Auditor Mesas', 'login': 'auditor_mesa_test', 'email': 'auditor.mesa@example.com',
            'groups_id': [(6, 0, [cls.env.ref('ttg_casino.group_casino_audit').id])],
        })
        # Réplica a escala del ejemplo de Luis del 9/11
        cls.tables = [('TBJ01', 'Black Jack', 836600, 112300, 141300, 0, 140800, 0),
                      ('TBJ02', 'Black Jack', 2154600, 677250, 612500, 350, 613500, 350)]
        cls.chips = [
            ('Cash Desk - DP01 - DP11 - DP01-DP11-001-100-003 - Caja-Mesas',
             [('Jetons', 562, 25.0, 0), ('Jetons', 200, 1000.0, 6), ('Non-Negotiables', 20, 5000.0, -1)]),
            ('Table - DP01 - DP11 - DP01-DP11-002-140-001 - TBJ01', [('Jetons', 8366, 100.0, 0)]),
            ('Table - DP01 - DP11 - DP01-DP11-002-140-002 - TBJ02', [('Jetons', 21546, 100.0, 0)]),
        ]

    def _new_cuadre(self, date):
        cuadre = self.env['casino.cuadre'].create({'date': date, 'encargado_id': self.encargado.id,
                                                   'company_id': self.company.id})
        cuadre.write({'casino_tasa_usd': 57.0, 'pago_apuestas_mesas': 752300.0, 'pago_apuestas_mesas_usd': 750.0})
        cuadre.action_audit()
        return cuadre

    def _import(self, cuadre, tables=None, chips=None, date_str=None):
        date_str = date_str or cuadre.date.strftime('%d.%m.%y')
        wizard = self.env['casino.mesa.audit.import'].with_user(self.auditor).create({
            'cuadre_id': cuadre.id,
            'result_file': base64.b64encode(build_result(tables or self.tables)), 'result_filename': 'mesas.xls',
            'chip_file': base64.b64encode(build_chips(date_str, chips or self.chips)), 'chip_filename': 'lia.xls',
        })
        return wizard.action_import()

    def test_import_and_figures(self):
        cuadre = self._new_cuadre('2030-05-01')
        self._import(cuadre)
        self.assertEqual(len(cuadre.mesa_result_ids), 2)
        self.assertEqual(cuadre.mesa_result_ids.mapped('mesa_id'), self.bj1 | self.bj2)
        # Mesas: 753,800 + 350 x 57 = 773,750 - 789,550 = -15,800
        self.assertAlmostEqual(cuadre.mesa_pred_gross_drop, 773750.0)
        self.assertAlmostEqual(cuadre.mesa_net_fills, 789550.0)
        self.assertAlmostEqual(cuadre.mesa_audit_resultado, -15800.0)
        # Caja: 754,300 + 19,950 = 774,250 - (752,300 + 750 x 57 = 795,050) = -20,800
        self.assertAlmostEqual(cuadre.mesa_pagos_caja, 795050.0)
        self.assertAlmostEqual(cuadre.mesa_audit_caja_resultado, -20800.0)
        self.assertAlmostEqual(cuadre.mesa_chip_conciliacion, -5500.0)
        self.assertAlmostEqual(cuadre.mesa_variacion, 5000.0)
        self.assertTrue(cuadre.mesa_fuera_tolerancia)
        self.assertEqual(cuadre.mesa_estado, 'pendiente')
        # Chip Liability: Caja de Mesas 6 x 1,000 - 1 x 5,000 = 1,000 de movimiento; inventario final calculado
        self.assertAlmostEqual(cuadre.mesa_chip_begin, 562 * 25 + 200000 + 100000)
        self.assertAlmostEqual(cuadre.mesa_chip_movement, 1000.0)
        self.assertAlmostEqual(cuadre.mesa_chip_end, cuadre.mesa_chip_begin + 1000.0)
        self.assertEqual(len(cuadre.chip_liability_ids), 5)
        line = cuadre.chip_liability_ids.filtered(lambda l: l.denomination == 1000.0)
        self.assertEqual((line.begin_qty, line.move_qty, line.end_qty), (200, 6, 206))
        self.assertEqual(line.name, 'Jetons RD$1,000')
        self.assertEqual(cuadre.chip_liability_ids.filtered(lambda l: l.location_code == 'TBJ01').mesa_id, self.bj1)
        # La tasa del cuadre convierte los USD
        cuadre.casino_tasa_usd = 60.0
        self.assertAlmostEqual(cuadre.mesa_pred_usd_dop, 21000.0)

    def test_tolerance_requires_justification(self):
        cuadre = self._new_cuadre('2030-05-02')
        self._import(cuadre)
        with self.assertRaisesRegex(UserError, 'tolerancia'):
            cuadre.with_user(self.auditor).action_accounting()
        cuadre.with_user(self.auditor).mesa_observaciones = 'Ficha de 5,000 cambiada en la mesa 2.'
        self.assertEqual(cuadre.mesa_estado, 'justificado')
        cuadre.with_user(self.auditor).action_accounting()
        self.assertEqual(cuadre.state, 'accounting')
        self.assertTrue(cuadre.mesa_approved)
        with self.assertRaisesRegex(UserError, 'aprobada'):
            cuadre.with_user(self.auditor).mesa_observaciones = 'otra cosa'
        with self.assertRaisesRegex(UserError, 'aprobada'):
            self._import(cuadre)
        cuadre.action_draft()
        self.assertFalse(cuadre.mesa_approved)

    def test_within_tolerance(self):
        cuadre = self._new_cuadre('2030-05-03')
        # Sin diferencia entre Predicted y Actual, Net Fills = pagos de Caja -> variación 0
        tables = [('TBJ01', 'Black Jack', 836600, 795050 - 677250, 141300, 0, 141300, 0),
                  ('TBJ02', 'Black Jack', 2154600, 677250, 612500, 350, 612500, 350)]
        self._import(cuadre, tables=tables)
        self.assertAlmostEqual(cuadre.mesa_variacion, 0.0)
        self.assertEqual(cuadre.mesa_estado, 'conciliado')
        cuadre.with_user(self.auditor).action_accounting()
        self.assertTrue(cuadre.mesa_approved)

    def test_required_before_accounting(self):
        cuadre = self._new_cuadre('2030-05-04')
        with self.assertRaisesRegex(UserError, 'resultados de mesas'):
            cuadre.with_user(self.auditor).action_accounting()
        self.company.casino_mesa_audit_required = False
        cuadre.with_user(self.auditor).action_accounting()
        self.assertEqual(cuadre.state, 'accounting')

    def test_unknown_table_code(self):
        cuadre = self._new_cuadre('2030-05-05')
        tables = self.tables + [('TPK01', 'Poker', 560600, 0, 0, 0, 0, 0)]
        with self.assertRaisesRegex(UserError, 'TPK01'):
            self._import(cuadre, tables=tables)

    def test_chip_wrong_date(self):
        cuadre = self._new_cuadre('2030-05-06')
        with self.assertRaisesRegex(UserError, 'Chip Liability es del'):
            self._import(cuadre, date_str='05.05.30')

    def test_files_from_different_days(self):
        cuadre = self._new_cuadre('2030-05-07')
        chips = self.chips[:1] + [('Table - X - TBJ01', [('Jetons', 9000, 100.0, 0)])] + self.chips[2:]
        with self.assertRaisesRegex(UserError, 'no corresponden al mismo día'):
            self._import(cuadre, chips=chips)

    def test_same_file_other_day(self):
        self._import(self._new_cuadre('2030-05-08'))
        other = self._new_cuadre('2030-05-09')
        with self.assertRaisesRegex(UserError, 'ya fue importado'):
            self._import(other)

    def test_report_renders(self):
        cuadre = self._new_cuadre('2030-05-10')
        self._import(cuadre)
        html, _fmt = self.env['ir.actions.report']._render_qweb_html('ttg_casino.report_mesa_audit', cuadre.ids)
        html = html.decode()
        self.assertIn('CUADRE DE AUDITORÍA DE MESAS', html)
        self.assertIn('RD$ -15,800.00', html)
        self.assertIn('RD$ 5,000.00', html)
        self.assertIn('CAJA DE MESAS', html)
        self.assertIn('BLACK JACK TEST 2', html)
