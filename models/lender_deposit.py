from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class DepositoPrestamista(models.Model):
    _name = 'casino.lender.deposit'
    _description = "Deposito de Prestamista"
    _rec_name = 'date'
    _order = 'partner_id,date desc'

    partner_id = fields.Many2one('res.partner', 'Prestamista', required=True)
    date = fields.Date('Fecha', required=True, default=lambda self: fields.Date.context_today(self), copy=False, index=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True)
    amount = fields.Monetary('Monto')
    note = fields.Char('Notas')
