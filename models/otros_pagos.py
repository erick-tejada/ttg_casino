from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class OtrosPagos(models.Model):
    _name = 'casino.otros.pagos'
    _description = "Pagos Manuales Maquinas"
    _rec_name = 'partner_id'
    _order = 'cuadre_id,partner_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True)
    state = fields.Selection(related='cuadre_id.state', string='Estado')

    maquina_id = fields.Many2one('casino.maquina', string='Maquina', required=True)
    code = fields.Integer('Código', related='maquina_id.code', store=True)
    brand_id = fields.Many2one('casino.maquina.marca', string='Marca', related='maquina_id.brand_id', store=True)
    model_id = fields.Many2one('casino.maquina.modelo', string='Modelo', related='maquina_id.model_id', store=True)
    maquina_state = fields.Selection(related='maquina_id.state', string="Estado Máquina")
    
    employee_id = fields.Many2one('hr.employee', string="Cajero", domain="['|', ('job_title', 'in', ['CAJERO', 'CAJERA', 'Cajera', 'Cajero']),('department_id','=',10)]", required=True)
    employee_sales_id = fields.Many2one('hr.employee', string="Slot", domain="['|', ('job_title', 'in', ['MAQUINA']),('department_id','=',13)]", required=True)
    hour = fields.Char('Hora')

    partner_id = fields.Many2one('res.partner', string="Cliente", required=True, domain="[('x_is_casino_client', '=', True)]")
    ref = fields.Char('Código Cliente', related='partner_id.ref', store=True, index=True)
    amount = fields.Monetary('Monto', required=True)
    error_id = fields.Many2one('casino.tipo.error.pago', string="Tipo de Pago Manual", ondelete='restrict')
    note = fields.Char('Nota')

    def unlink(self):
        if any(record.state == 'done' for record in self):
            raise ValidationError('CUADRE CERRADO: No puede borrar un Pago si el Cuadre está cerrado.')
        res = super(OtrosPagos, self).unlink()
        return res