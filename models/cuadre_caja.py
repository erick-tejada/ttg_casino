from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class CuadreDeCaja(models.Model):
    _name = 'casino.cuadre'
    _description = "Cuadre de Caja"
    _order = 'date'
    _rec_name = 'date'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _default_currency_usd_id(self):
        return self.env['res.currency'].search([('name','=','USD')])
    
    @api.constrains('company_id', 'date')
    def _date_company_id(self):
        for record in self:
            cant_cuadres = self.env['casino.cuadre'].search_count([('company_id','=',record.company_id.id), ('date','=',record.date)])
            if cant_cuadres > 1:
                raise ValidationError('FECHA REPETIDA: Existe otro cuadre para la misma fecha!')

    date = fields.Date('Fecha', required=True, default=lambda self: fields.Date.context_today(self), copy=False, index=True, tracking=3)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True)
    currency_usd_id = fields.Many2one('res.currency', string='Moneda USD', readonly=True, default=_default_currency_usd_id)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('audit', 'Auditoría'),
        ('accounting', 'Contabilidad'),
        ('done', 'Cerrado'),
        ], string='Estado', readonly=True, copy=False, index=True, tracking=3, default='draft')

    # MAQUINAS
    bill_drop_ids = fields.One2many('casino.bill.drop', 'cuadre_id', 'Detalle Bill Drop')
    bill_drop_total = fields.Monetary('Bill Drop', compute='_compute_bill_drop')

    @api.depends('bill_drop_ids', 'bill_drop_ids.amount_total')
    def _compute_bill_drop(self):
        for record in self:
            total = 0
            for line in record.bill_drop_ids:
                total += line.amount_total
            record.bill_drop_total = total
    
    def open_bill_drop(self):
        bill_drop_ids = self.mapped('bill_drop_ids')
        if self.state != 'done':
            action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.view_bill_drop_tree")
        else:
            action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_bill_drop_readonly")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action
    
    @api.model
    def create(self, vals):
        cuadre = super(CuadreDeCaja, self).create(vals)
        if not cuadre.bill_drop_ids:
            maquina_ids = self.env['casino.maquina'].search([('company_id','=',cuadre.company_id.id)])
            for maquina in maquina_ids:
                _logger.warning('--------- %s ----------' % maquina.name)
                self.env['casino.bill.drop'].create({
                    'cuadre_id': cuadre.id,
                    'maquina_id': maquina.id,
                })
        return cuadre
