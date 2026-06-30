from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class CasinoPagoBancarizadoMixin(models.AbstractModel):
    _name = 'casino.pago.bancarizado.mixin'
    _description = 'Pago Bancarizado (Mixin)'
    _rec_name = 'partner_id'

    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True)
    state = fields.Selection(related='cuadre_id.state', string='Estado')

    partner_id = fields.Many2one('res.partner', string="Cliente", required=True, domain="[('x_is_casino_client', '=', True)]")

    account_journal_id = fields.Many2one('account.journal', string='Banco', required=True,
        domain="[('use_for_pago_bancarizado', '=', True)]")

    outbound_payment_method_line_ids = fields.Many2many('account.payment.method.line',
        compute='_compute_outbound_payment_method_line_ids')
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Metodo de Pago', required=True,
        domain="[('id', 'in', outbound_payment_method_line_ids)]")

    is_check_method = fields.Boolean('Es Cheque', compute='_compute_is_check_method', store=True)
    numero_cheque = fields.Char('Numero de Cheque')

    amount = fields.Monetary('Monto', required=True)

    pago_cliente_payment_id = fields.Many2one('account.payment', string='Pago al Cliente', readonly=True, copy=False)
    reposicion_payment_id = fields.Many2one('account.payment', string='Reposicion de Pago Bancarizado', readonly=True, copy=False)

    @api.depends('account_journal_id')
    def _compute_outbound_payment_method_line_ids(self):
        for record in self:
            record.outbound_payment_method_line_ids = record.account_journal_id.outbound_payment_method_line_ids

    @api.depends('payment_method_line_id')
    def _compute_is_check_method(self):
        for record in self:
            record.is_check_method = record.payment_method_line_id.payment_method_id.code == 'check_printing'

    @api.constrains('is_check_method', 'numero_cheque')
    def _check_numero_cheque(self):
        for record in self:
            if record.is_check_method and not record.numero_cheque:
                raise ValidationError('NUMERO DE CHEQUE REQUERIDO: Debe indicar el Número de Cheque si el Método de Pago es Cheque.')

    def _get_caja_account(self):
        self.ensure_one()
        raise NotImplementedError

    def action_create_pago_cliente(self):
        self.ensure_one()
        if self.pago_cliente_payment_id:
            raise UserError('PAGO YA EXISTE: Ya se generó el Pago al Cliente para esta línea.')
        if self.is_check_method and not self.numero_cheque:
            raise UserError('NUMERO DE CHEQUE REQUERIDO: Debe indicar el Número de Cheque si el Método de Pago es Cheque.')
        memo = 'Pago Bancarizado %s' % self.cuadre_id.display_name
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'journal_id': self.account_journal_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'date': self.cuadre_id.date,
            'memo': memo,
            'ref': memo,
            'force_destination_account_id': self._get_caja_account().id,
            'company_id': self.company_id.id,
        })
        payment.action_post()
        self.pago_cliente_payment_id = payment.id

    def action_create_reposicion(self):
        self.ensure_one()
        if not self.pago_cliente_payment_id:
            raise UserError('FALTA PAGO AL CLIENTE: Debe generar el Pago al Cliente antes de la Reposición.')
        if self.reposicion_payment_id:
            raise UserError('REPOSICION YA EXISTE: Ya se generó la Reposición de Pago Bancarizado para esta línea.')
        memo = 'Reposicion Pago Bancarizado %s' % self.cuadre_id.display_name
        journal_id = self.account_journal_id
        inbound_lines = journal_id.inbound_payment_method_line_ids
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'journal_id': journal_id.id,
            'payment_method_line_id': inbound_lines[0].id if inbound_lines else False,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'date': self.cuadre_id.date,
            'memo': memo,
            'ref': memo,
            'force_destination_account_id': self._get_caja_account().id,
            'company_id': self.company_id.id,
        })
        payment.action_post()
        self.reposicion_payment_id = payment.id

    def _cancel_payments(self):
        for record in self:
            for field_name in ('reposicion_payment_id', 'pago_cliente_payment_id'):
                payment = record[field_name]
                if payment:
                    payment.action_cancel()
                    try:
                        payment.unlink()
                    except Exception:
                        pass
                    finally:
                        record[field_name] = False

    def unlink(self):
        if any(record.state == 'done' for record in self):
            raise ValidationError('CUADRE CERRADO: No puede borrar un Pago Bancarizado si el Cuadre está cerrado.')
        if any(record.pago_cliente_payment_id or record.reposicion_payment_id for record in self):
            raise ValidationError('PAGO GENERADO: No puede borrar esta línea porque ya tiene Pagos generados. Cancele los pagos primero.')
        return super(CasinoPagoBancarizadoMixin, self).unlink()
