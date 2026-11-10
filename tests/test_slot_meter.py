# -*- coding: utf-8 -*-
import base64

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

HEADERS = ['Position', 'Inventory #', 'Serial #', 'Manufacturer', 'Model', 'Game', 'EGM Audit', 'Audit', 'NGWINE',
           'TAP', 'CRE', 'GTIE', 'GTOE', 'GJOE', 'GTIN', 'GTINE', 'GP', 'BDIE', 'CCOE', 'PWE', 'CLIC', 'CLOC',
           'Avg. Bet', 'Retention %', 'ET', 'ST', 'XTRA']
NUMERIC = HEADERS[6:]


def _cell(value):
    if isinstance(value, str):
        return '<Cell><Data ss:Type="String">%s</Data></Cell>' % value
    return '<Cell><Data ss:Type="Number">%s</Data></Cell>' % value


def build_file(machines, total_override=None, headers=HEADERS, box=True):
    """machines: list of dicts {code, NGWINE, CRE, BDIE, TAP, GP, ...}. Devuelve bytes SpreadsheetML como DRGT."""
    rows = ['<Row>%s</Row>' % ''.join(_cell(h) for h in headers)]
    totals = dict.fromkeys(NUMERIC, 0.0)
    for m in machines:
        values = {'Position': 'DP01-DP11-001-007-%03d' % m['code'], 'Inventory #': str(m['code']),
                  'Serial #': 'SER%s' % m['code'], 'Manufacturer': 'NOVOMATIC', 'Model': 'FV-600', 'Game': 'GAME'}
        for h in NUMERIC:
            values[h] = m.get(h, 0)
            totals[h] += values[h]
        rows.append('<Row>%s</Row>' % ''.join(_cell(values[h]) for h in headers))
    totals.update(total_override or {})
    count = len(machines)
    total_row = [count, count, count, 1, 1, 1] + [round(totals[h], 2) for h in NUMERIC]
    rows.append('<Row>%s</Row>' % ''.join(_cell(v) for v in total_row[:len(headers)]))
    if box:
        rows.append('<Row>%s%s</Row>' % (_cell('NGWINE'), _cell(round(totals['NGWINE'], 2))))
        rows.append('<Row>%s%s</Row>' % (_cell('HANDPAY LIABILITY'), _cell(7.25)))
    xml = ('<?xml version="1.0"?>\n<?mso-application progid="Excel.Sheet"?>\n'
           '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
           'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
           '<Worksheet ss:Name="1. Slot Analysis RD$"><Table>%s</Table></Worksheet></Workbook>') % ''.join(rows)
    return xml.encode()


@tagged('post_install', '-at_install')
class TestSlotMeterAudit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({'tc_comision_percent': 0.0345, 'tc_itbis_percent': 0.0,
                           'casino_slot_audit_required': True, 'casino_slot_audit_tolerance': 3.0})
        brand = cls.env['casino.maquina.marca'].create({'name': 'TEST BRAND'})
        model = cls.env['casino.maquina.modelo'].create({'name': 'TEST MODEL', 'brand_id': brand.id})
        cls.machines = cls.env['casino.maquina'].create([
            {'code': code, 'model_id': model.id, 'company_id': cls.company.id} for code in (9001, 9002, 9003)])
        cls.encargado = cls.env['casino.encargado.caja'].create({'name': 'Encargado Test'})
        cls.employee = cls.env['hr.employee'].create({'name': 'Cajera Test'})
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Test'})
        cls.error = cls.env['casino.tipo.error.pago'].search([], limit=1) or cls.env['casino.tipo.error.pago'].create({'name': 'Otros'})
        cls.premio = cls.env['casino.tipo.premio'].search([], limit=1) or cls.env['casino.tipo.premio'].create({'name': 'Rifa'})
        cls.auditor = cls.env['res.users'].create({
            'name': 'Auditor Test', 'login': 'auditor_slot_test', 'email': 'auditor@example.com',
            'groups_id': [(6, 0, [cls.env.ref('ttg_casino.group_casino_audit').id])],
        })
        cls.cajero = cls.env['res.users'].create({
            'name': 'Caja Test', 'login': 'caja_slot_test', 'email': 'caja@example.com',
            'groups_id': [(6, 0, [cls.env.ref('ttg_casino.group_casino_user').id])],
        })
        # Contadores: NGWINE 1,300.25, CRE -10.25 -> 1,290.00 + 5 de handpay = 1,295.00
        cls.lines = [
            {'code': 9001, 'NGWINE': 1000.0, 'CRE': -10.25, 'BDIE': 2000, 'TAP': 0, 'GP': 120, 'Retention %': 0.25, 'XTRA': 7},
            {'code': 9002, 'NGWINE': -200.0, 'CRE': 0, 'BDIE': 0, 'TAP': 5, 'GP': 30},
            {'code': 9003, 'NGWINE': 500.25, 'CRE': 0, 'BDIE': 0, 'GP': 15},
        ]

    def _new_cuadre(self, date, state='audit'):
        cuadre = self.env['casino.cuadre'].create({'date': date, 'encargado_id': self.encargado.id,
                                                   'company_id': self.company.id})
        # Caja: 2 billetes de 1,000 en la máquina 9001, 705 de retiros -> Resultado Caja Máquina 1,295
        cuadre.bill_drop_ids.filtered(lambda b: b.maquina_id == self.machines[0]).qty_1000 = 2
        cuadre.tarjetas_cashout = 705.0
        if state != 'draft':
            cuadre.action_audit()
        if state == 'done':
            cuadre.state = 'done'
        return cuadre

    def _import(self, cuadre, content=None, user=None):
        cuadre = cuadre.with_user(user or self.auditor)
        return cuadre.import_slot_meters(content or build_file(self.lines), 'slot.xls')

    def test_import_creates_lines_and_audit(self):
        cuadre = self._new_cuadre('2030-01-01')
        self._import(cuadre)
        self.assertEqual(len(cuadre.slot_meter_ids), 3)
        line = cuadre.slot_meter_ids.filtered(lambda l: l.code == 9001)
        self.assertEqual(line.maquina_id, self.machines[0])
        self.assertEqual(line.bdie, 2000)
        self.assertEqual(line.gp, 120)
        self.assertAlmostEqual(line.retention, 0.25)
        self.assertEqual(line.serial, 'SER9001')
        self.assertEqual(line.extra_data, {'XTRA': '7'})
        self.assertAlmostEqual(cuadre.audit_ngwine, 1300.25)
        self.assertAlmostEqual(cuadre.audit_credito_maquina, -10.25)
        cuadre.audit_handpay_liability = 5.0
        self.assertAlmostEqual(cuadre.resultado_caja_maquina, 1295.0)
        self.assertAlmostEqual(cuadre.audit_resultado, 1295.0)
        self.assertAlmostEqual(cuadre.audit_diferencia, 0.0)
        self.assertFalse(cuadre.audit_fuera_tolerancia)
        self.assertTrue(cuadre.slot_meter_file)
        self.assertEqual(cuadre.slot_meter_import_user_id, self.auditor)
        self.assertIn('3 máquinas', cuadre.message_ids[0].body)

    def test_formula_uses_cuadre_sobrantes_rifas_devoluciones(self):
        cuadre = self._new_cuadre('2030-01-02')
        self._import(cuadre)
        cuadre.audit_handpay_liability = 5.0
        self.env['casino.sobrante'].create({'cuadre_id': cuadre.id, 'employee_id': self.employee.id, 'amount': 100.0})
        self.env['casino.premios.maquina'].create({'cuadre_id': cuadre.id, 'employee_id': self.employee.id,
                                                   'employee_sales_id': self.employee.id, 'premio_id': self.premio.id,
                                                   'partner_id': self.partner.id, 'amount': 50.0})
        self.env['casino.devolucion'].create({'cuadre_id': cuadre.id, 'maquina_id': self.machines[1].id,
                                              'partner_id': self.partner.id, 'error_id': self.error.id, 'amount': 30.0})
        cuadre.audit_billetes_no_registrados = 30.0
        # Caja: 1,295 + 100 sobrante - 50 rifa - 30 devolución = 1,315
        self.assertAlmostEqual(cuadre.resultado_caja_maquina, 1315.0)
        self.assertAlmostEqual(cuadre.audit_sobrantes, 100.0)
        self.assertAlmostEqual(cuadre.audit_rifas, 50.0)
        self.assertAlmostEqual(cuadre.audit_devoluciones, 30.0)
        # Contadores: 1,295 + 100 - 50 - 30 + 30 billetes no registrados = 1,345
        self.assertAlmostEqual(cuadre.audit_resultado, 1345.0)
        self.assertAlmostEqual(cuadre.audit_diferencia, 30.0)
        self.assertTrue(cuadre.audit_fuera_tolerancia)

    def test_missing_machine_blocks_import(self):
        cuadre = self._new_cuadre('2030-01-03')
        content = build_file(self.lines + [{'code': 9999, 'NGWINE': 1}, {'code': 9998}])
        with self.assertRaisesRegex(UserError, '9998, 9999'):
            self._import(cuadre, content)
        self.assertFalse(cuadre.slot_meter_ids)

    def test_archived_machine_is_accepted(self):
        self.machines[2].active = False
        cuadre = self._new_cuadre('2030-01-04')
        self._import(cuadre)
        self.assertIn(self.machines[2], cuadre.slot_meter_ids.maquina_id)

    def test_reimport_replaces_lines(self):
        cuadre = self._new_cuadre('2030-01-05')
        self._import(cuadre)
        first_ids = cuadre.slot_meter_ids.ids
        other = [dict(self.lines[0], NGWINE=900.0)]
        self._import(cuadre, build_file(other))
        self.assertEqual(len(cuadre.slot_meter_ids), 1)
        self.assertFalse(set(first_ids) & set(cuadre.slot_meter_ids.ids))
        self.assertAlmostEqual(cuadre.audit_ngwine, 900.0)
        self.assertIn('Se reemplazaron 3 líneas', cuadre.message_ids[0].body)

    def test_same_file_in_another_cuadre_is_blocked(self):
        first = self._new_cuadre('2030-01-06')
        second = self._new_cuadre('2030-01-07')
        self._import(first)
        with self.assertRaisesRegex(UserError, '06/01/2030'):
            self._import(second)
        # Mismas filas con otro cuadro de ajustes debajo = mismo reporte
        with self.assertRaisesRegex(UserError, 'ya fue importado'):
            self._import(second, build_file(self.lines, box=False))

    def test_draft_and_non_auditor_are_blocked(self):
        draft = self._new_cuadre('2030-01-08', state='draft')
        with self.assertRaisesRegex(UserError, 'Borrador'):
            self._import(draft)
        cuadre = self._new_cuadre('2030-01-09')
        with self.assertRaisesRegex(UserError, 'Solo el Auditor'):
            self._import(cuadre, user=self.cajero)

    def test_accounting_requires_import(self):
        cuadre = self._new_cuadre('2030-01-10')
        with self.assertRaisesRegex(UserError, 'Debe importar'):
            cuadre.action_accounting()
        self.company.casino_slot_audit_required = False
        cuadre.action_accounting()
        self.assertEqual(cuadre.state, 'accounting')

    def test_accounting_within_tolerance(self):
        cuadre = self._new_cuadre('2030-01-11')
        self._import(cuadre)
        cuadre.audit_handpay_liability = 7.0  # diferencia de 2.00
        cuadre.action_accounting()
        self.assertEqual(cuadre.state, 'accounting')
        self.assertIn('diferencia 2.00', cuadre.message_ids[0].body)

    def test_out_of_tolerance_requires_justification(self):
        cuadre = self._new_cuadre('2030-01-12')
        self._import(cuadre)
        cuadre.audit_handpay_liability = 14.39  # diferencia de 9.39
        self.assertTrue(cuadre.audit_fuera_tolerancia)
        with self.assertRaisesRegex(UserError, '9.39'):
            cuadre.action_accounting()
        self.assertEqual(cuadre.state, 'audit')
        cuadre.audit_justificacion = '   '
        with self.assertRaises(UserError):
            cuadre.action_accounting()
        cuadre.audit_justificacion = 'Error de centavos en DRGT, revisado con Caja.'
        cuadre.action_accounting()
        self.assertEqual(cuadre.state, 'accounting')
        self.assertIn('Error de centavos en DRGT', cuadre.message_ids[0].body)

    def test_tolerance_is_configurable(self):
        self.company.casino_slot_audit_tolerance = 10.0
        cuadre = self._new_cuadre('2030-01-13')
        self._import(cuadre)
        cuadre.audit_handpay_liability = 14.39
        self.assertFalse(cuadre.audit_fuera_tolerancia)

    def test_import_on_closed_cuadre(self):
        cuadre = self._new_cuadre('2030-01-14', state='done')
        self._import(cuadre)
        self.assertEqual(len(cuadre.slot_meter_ids), 3)
        self.assertEqual(cuadre.state, 'done')

    def test_wizard(self):
        cuadre = self._new_cuadre('2030-01-15')
        action = cuadre.with_user(self.auditor).action_open_slot_meter_import()
        wizard = self.env['casino.slot.meter.import'].with_user(self.auditor).with_context(action['context']).create({
            'file': base64.b64encode(build_file(self.lines)), 'filename': 'slot.xls',
            'audit_handpay_liability': 5.0, 'audit_variacion_efectivo': 1.5, 'audit_billetes_no_registrados': 2.0,
        })
        wizard.action_import()
        self.assertEqual(len(cuadre.slot_meter_ids), 3)
        self.assertAlmostEqual(cuadre.audit_variacion_efectivo, 1.5)
        self.assertAlmostEqual(cuadre.audit_resultado, 1298.5)
        # Sin archivo: solo actualiza los valores y conserva las líneas
        wizard2 = self.env['casino.slot.meter.import'].with_user(self.auditor).with_context(action['context']).create({})
        self.assertAlmostEqual(wizard2.audit_variacion_efectivo, 1.5)
        wizard2.audit_variacion_efectivo = 0.0
        wizard2.action_import()
        self.assertEqual(len(cuadre.slot_meter_ids), 3)
        self.assertAlmostEqual(cuadre.audit_resultado, 1297.0)

    def test_file_errors(self):
        cuadre = self._new_cuadre('2030-01-16')
        with self.assertRaisesRegex(UserError, 'no coincide'):
            self._import(cuadre, build_file(self.lines, total_override={'NGWINE': 5000}))
        with self.assertRaisesRegex(UserError, 'repetidas'):
            self._import(cuadre, build_file(self.lines + [self.lines[0]]))
        bad_headers = [h for h in HEADERS if h != 'CRE']
        with self.assertRaisesRegex(UserError, 'CRE'):
            self._import(cuadre, build_file(self.lines, headers=bad_headers))
        with self.assertRaisesRegex(UserError, 'Formato de archivo'):
            self._import(cuadre, b'hola')
        self.assertFalse(cuadre.slot_meter_ids)

    def test_cajero_can_still_use_cuadre(self):
        """Caja (sin acceso a los contadores) sigue pudiendo abrir y editar cuadres en borrador."""
        cuadre = self._new_cuadre('2030-01-17', state='draft')
        as_caja = cuadre.with_user(self.cajero)
        as_caja.tarjetas_cashout = 700.0
        as_caja.invalidate_recordset()
        self.assertAlmostEqual(as_caja.resultado_caja_maquina, 1300.0)
        as_caja.action_audit()
