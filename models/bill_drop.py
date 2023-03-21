from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class BillDrop(models.Model):
    _name = 'casino.bill.drop'
    _description = "Bill Drop"
    _order = 'cuadre_id, maquina_id'
    _rec_name = 'maquina_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True)
    state = fields.Selection(related='cuadre_id.state', string='Estado')

    maquina_id = fields.Many2one('casino.maquina', string='Maquina', required=True)
    code = fields.Integer('Código', related='maquina_id.code', store=True)
    brand_id = fields.Many2one('casino.maquina.marca', string='Marca', related='maquina_id.brand_id', store=True)
    model_id = fields.Many2one('casino.maquina.modelo', string='Modelo', related='maquina_id.model_id', store=True)

    qty_50 = fields.Integer('Cant. 50')
    qty_100 = fields.Integer('Cant. 100')
    qty_200 = fields.Integer('Cant. 200')
    qty_500 = fields.Integer('Cant. 500')
    qty_1000 = fields.Integer('Cant. 1000')
    qty_2000 = fields.Integer('Cant. 2000')

    amount_50 = fields.Monetary('Monto 50', compute='_compute_amounts', store=True)
    amount_100 = fields.Monetary('Monto 100', compute='_compute_amounts', store=True)
    amount_200 = fields.Monetary('Monto 200', compute='_compute_amounts', store=True)
    amount_500 = fields.Monetary('Monto 500', compute='_compute_amounts', store=True)
    amount_1000 = fields.Monetary('Monto 1000', compute='_compute_amounts', store=True)
    amount_2000 = fields.Monetary('Monto 2000', compute='_compute_amounts', store=True)
    amount_total = fields.Monetary('Monto Total', compute='_compute_amounts', store=True)

    @api.depends('qty_50', 'qty_100', 'qty_200', 'qty_500', 'qty_1000', 'qty_2000')
    def _compute_amounts(self):
        for record in self:
            amount_50 = record.qty_50 * 50.0
            amount_100 = record.qty_100 * 100.0
            amount_200 = record.qty_200 * 200.0
            amount_500 = record.qty_500 * 500.0
            amount_1000 = record.qty_1000 * 1000.0
            amount_2000 = record.qty_2000 * 2000.0
            record.write({
                'amount_50': amount_50,
                'amount_100': amount_100,
                'amount_200': amount_200,
                'amount_500': amount_500,
                'amount_1000': amount_1000,
                'amount_2000': amount_2000,
                'amount_total': amount_50 + amount_100 + amount_200 + amount_500 + amount_1000 + amount_2000
            })
    
    @api.constrains('cuadre_id', 'maquina_id')
    def _cuadre_maquina_constrains(self):
        for record in self:
            cant_bill_drop = self.env['casino.bill.drop'].search_count([('company_id','=',record.company_id.id), ('cuadre_id','=',record.cuadre_id.id), ('maquina_id','=',record.maquina_id.id)])
            if cant_bill_drop > 1:
                raise ValidationError('MAQUINA REPETIDA EN CUADRE: Esta máquina ya fue reportada para este cuadre!')