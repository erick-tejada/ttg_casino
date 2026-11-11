# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestCuadreFixes(TransactionCase):
    """Regresiones: borrar Sobrantes/Faltantes y cerrar un cuadre con cobros TC y retención de ITBIS."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        Account = cls.env['account.account']
        cls.account = Account.create({'code': '999001', 'name': 'Caja Test', 'account_type': 'asset_cash'})
        cls.journal = cls.env['account.journal'].create({'name': 'Cierre Test', 'code': 'CTST', 'type': 'general'})
        cls.bank = cls.env['account.journal'].create({'name': 'Banco Test', 'code': 'BTST', 'type': 'bank'})
        vals = {name: cls.account.id for name, field in cls.company._fields.items()
                if field.type == 'many2one' and field.comodel_name == 'account.account'
                and (name.startswith(('caja_', 'maquina_', 'mesa_', 'tc_', 'dop_', 'usd_')))}
        vals.update({'cierre_journal_id': cls.journal.id, 'banco_dop_journal_id': cls.bank.id,
                     'banco_usd_journal_id': cls.bank.id, 'tc_comision_percent': 0.0345, 'tc_itbis_percent': 0.02,
                     'tc_partner_id': cls.env['res.partner'].create({'name': 'Procesador TC'}).id,
                     'casino_slot_audit_required': False, 'casino_refresh_future': False})
        cls.company.write(vals)
        # Como en producción: el método de cobro del banco tiene su cuenta.
        cls.deposit_account = Account.create({'code': '999002', 'name': 'Cobros Pendientes Test', 'account_type': 'asset_current', 'reconcile': True})
        cls.bank.inbound_payment_method_line_ids[:1].payment_account_id = cls.deposit_account
        cls.encargado = cls.env['casino.encargado.caja'].create({'name': 'Encargado Test'})
        cls.employee = cls.env['hr.employee'].create({'name': 'Cajera Test'})
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Test'})

    def _cuadre(self, date):
        return self.env['casino.cuadre'].create({'date': date, 'encargado_id': self.encargado.id})

    def test_unlink_sobrante_faltante(self):
        cuadre = self._cuadre('2031-02-01')
        sobrante = self.env['casino.sobrante'].create({'cuadre_id': cuadre.id, 'employee_id': self.employee.id, 'amount': 100})
        faltante = self.env['casino.faltante'].create({'cuadre_id': cuadre.id, 'employee_id': self.employee.id, 'amount': 50})
        sobrante.unlink()
        faltante.unlink()
        self.assertFalse(sobrante.exists() or faltante.exists())
        self.assertEqual(cuadre.sobrante_total, 0)
        self.assertEqual(cuadre.faltante_total, 0)

    def test_unlink_on_closed_cuadre_still_blocked(self):
        cuadre = self._cuadre('2031-02-02')
        sobrante = self.env['casino.sobrante'].create({'cuadre_id': cuadre.id, 'employee_id': self.employee.id, 'amount': 100})
        cuadre.state = 'done'
        with self.assertRaisesRegex(ValidationError, 'CUADRE CERRADO'):
            sobrante.unlink()

    def test_close_with_credit_card_and_itbis_retention(self):
        cuadre = self._cuadre('2031-02-03')
        self.env['casino.cobro.tc'].create({'cuadre_id': cuadre.id, 'partner_id': self.partner.id,
                                           'amount': 10000.0, 'amount_fee': 500.0})
        cuadre.action_audit()
        cuadre.action_accounting()
        cuadre.action_done()
        self.assertEqual(cuadre.state, 'done')
        lines = cuadre.deposito_dop_move_id.line_ids
        itbis = lines.filtered(lambda l: l.name == 'ITBIS Retenido por Cobros con Tarjeta de Crédito')
        self.assertAlmostEqual(sum(itbis.mapped('debit')), 200.0)

    def _close_with_tc(self, date):
        cuadre = self._cuadre(date)
        self.env['casino.cobro.tc'].create({'cuadre_id': cuadre.id, 'partner_id': self.partner.id,
                                           'amount': 10000.0, 'amount_fee': 500.0})
        cuadre.action_audit()
        cuadre.action_accounting()
        cuadre.action_done()
        return cuadre

    def test_deposit_uses_payment_method_account(self):
        cuadre = self._close_with_tc('2031-02-04')
        deposit = cuadre.deposito_dop_move_id.line_ids.filtered(lambda l: l.name == 'Cobros con Tarjeta de Crédito' and l.debit)
        self.assertEqual(deposit.account_id, self.deposit_account)

    def test_deposit_fallback_without_payment_method_account(self):
        """Antes fallaba con AttributeError (campo de compañía que ya no existe en Odoo 18)."""
        self.bank.inbound_payment_method_line_ids.payment_account_id = False
        transfer = self.env['account.account'].create({'code': '999003', 'name': 'Transferencias Test', 'account_type': 'asset_current', 'reconcile': True})
        self.company.transfer_account_id = transfer
        expected = self.env['account.chart.template'].ref('account_journal_payment_debit_account_id', raise_if_not_found=False) or transfer
        cuadre = self._close_with_tc('2031-02-05')
        deposit = cuadre.deposito_dop_move_id.line_ids.filtered(lambda l: l.name == 'Cobros con Tarjeta de Crédito' and l.debit)
        self.assertEqual(deposit.account_id, expected)
