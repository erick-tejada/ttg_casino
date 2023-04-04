from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class ApuestaMesa(models.Model):
    _name = 'casino.apuesta.mesa'
    _description = "Drop en Mesa"
    _rec_name = 'mesa_id'
    _order = 'cuadre_id,mesa_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True)
    state = fields.Selection(related='cuadre_id.state', string='Estado', store=True)

    mesa_id = fields.Many2one('casino.mesa', string="Mesa", required=True)

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
    note = fields.Char('Nota')

    def _verify_state(self):
        for record in self:
            if record.state == 'done':
                raise ValidationError('CUADRE CERRADO: No puede crear/modificar un %s si el Cuadre al que pertenece esta Cerrado.' % self._description)

    def unlink(self):
        if any(record.state == 'done' for record in self):
            raise ValidationError('CUADRE CERRADO: No puede borrar un %s si el Cuadre está cerrado.' % self._description)
        res = super(ApuestaMesa, self).unlink()
        return res


class ApuestaMesaUSD(models.Model):
    _name = 'casino.apuesta.mesa.usd'
    _description = "Drop en Mesa USD"
    _rec_name = 'mesa_id'
    _order = 'cuadre_id,mesa_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_usd_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True)
    state = fields.Selection(related='cuadre_id.state', string='Estado', store=True)

    mesa_id = fields.Many2one('casino.mesa', string="Mesa", required=True)

    qty_1 = fields.Integer('Cant. 1')
    qty_5 = fields.Integer('Cant. 5')
    qty_10 = fields.Integer('Cant. 10')
    qty_20 = fields.Integer('Cant. 20')
    qty_50 = fields.Integer('Cant. 50')
    qty_100 = fields.Integer('Cant. 100')

    amount_1 = fields.Monetary('Monto 1', compute='_compute_amounts', store=True)
    amount_5 = fields.Monetary('Monto 5', compute='_compute_amounts', store=True)
    amount_10 = fields.Monetary('Monto 10', compute='_compute_amounts', store=True)
    amount_20 = fields.Monetary('Monto 20', compute='_compute_amounts', store=True)
    amount_50 = fields.Monetary('Monto 50', compute='_compute_amounts', store=True)
    amount_100 = fields.Monetary('Monto 100', compute='_compute_amounts', store=True)
    amount_total = fields.Monetary('Monto Total', compute='_compute_amounts', store=True)

    @api.depends('qty_1', 'qty_5', 'qty_10', 'qty_20', 'qty_50', 'qty_100')
    def _compute_amounts(self):
        for record in self:
            amount_1 = record.qty_1
            amount_5 = record.qty_5 * 5.0
            amount_10 = record.qty_10 * 10.0
            amount_20 = record.qty_20 * 20.0
            amount_50 = record.qty_50 * 50.0
            amount_100 = record.qty_100 * 100.0
            record.write({
                'amount_1': amount_1,
                'amount_5': amount_5,
                'amount_10': amount_10,
                'amount_20': amount_20,
                'amount_50': amount_50,
                'amount_100': amount_100,
                'amount_total': amount_1 + amount_5 + amount_10 + amount_20 + amount_50 + amount_100
            })
    note = fields.Char('Nota')

    def _verify_state(self):
        for record in self:
            if record.state == 'done':
                raise ValidationError('CUADRE CERRADO: No puede crear/modificar un %s si el Cuadre al que pertenece esta Cerrado.' % self._description)

    def unlink(self):
        if any(record.state == 'done' for record in self):
            raise ValidationError('CUADRE CERRADO: No puede borrar un %s si el Cuadre está cerrado.' % self._description)
        res = super(ApuestaMesa, self).unlink()
        return res