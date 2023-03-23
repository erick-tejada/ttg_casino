from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class Sobrante(models.Model):
    _name = 'casino.sobrante'
    _description = "Cambio Tarjeta Credito"
    _rec_name = 'employee_id'
    _order = 'cuadre_id,employee_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True)
    state = fields.Selection(related='cuadre_id.state', string='Estado')

    employee_id = fields.Many2one('hr.employee', string="Cajero", required=True)
    amount = fields.Monetary('Monto', required=True)
    note = fields.Char('Nota')

    def unlink(self):
        if any(record.state == 'done' for record in self):
            raise ValidationError('CUADRE CERRADO: No puede borrar un Sobrante si el Cuadre está cerrado.')
        res = super(Devolucion, self).unlink()
        return res


class Faltante(models.Model):
    _name = 'casino.faltante'
    _description = "Cambio Tarjeta Credito"
    _rec_name = 'employee_id'
    _order = 'cuadre_id,employee_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True)
    state = fields.Selection(related='cuadre_id.state', string='Estado')

    employee_id = fields.Many2one('hr.employee', string="Cajero", required=True)
    amount = fields.Monetary('Monto', required=True)
    note = fields.Char('Nota')

    def unlink(self):
        if any(record.state == 'done' for record in self):
            raise ValidationError('CUADRE CERRADO: No puede borrar un Faltante si el Cuadre está cerrado.')
        res = super(Devolucion, self).unlink()
        return res