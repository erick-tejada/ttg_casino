from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_is_casino_client = fields.Boolean('Es Cliente Casino', help='Indica que es un cliente del Casino')

    x_is_lender = fields.Boolean('Es Prestamista')
    x_tier2_amount = fields.Float('Meta Monto Prestado para Nivel 2', help='Es el monto mínimo prestado para cambiar el porciento pagado de comisión al Porciento Comisión Nivel 2.')
    x_tier1_percent = fields.Float('Porciento Comision Nivel 1', help='Es el Porcentaje de comisión a pagar al prestamista si las ganancias son menores o iguales al Monto de Comisión Nivel 1.')
    x_tier2_percent = fields.Float('Porciento Comision Nivel 2', help='Es el Porcentaje de comisión a pagar al prestamista si las ganancias son mayores al Monto de Comisión .')
    
    x_deposit_ids = fields.One2many('casino.lender.deposit', 'partner_id', string='Depósitos')
    x_amount_available = fields.Monetary('Monto Disponible para Prestar', compute='_compute_x_amount_available')

    x_marca_maquina_ids = fields.One2many('casino.marca.maquina', 'lender_partner_id', string='Marcas Maquinas')
    x_marca_mesa_ids = fields.One2many('casino.marca.mesa', 'lender_partner_id', string='Marcas Mesas')

    @api.depends('x_deposit_ids', 'x_deposit_ids.amount', 'x_marca_maquina_ids', 'x_marca_maquina_ids.amount', 'x_marca_mesa_ids', 'x_marca_mesa_ids.amount')
    def _compute_x_amount_available(self):
        for record in self:
            sql_query = '''
                        SELECT SUM(d.amount)
                        FROM casino_lender_deposit d
                        WHERE d.partner_id = %s
                    '''
            self.env.cr.execute(sql_query, (record.id,))
            result = self.env.cr.dictfetchall()
            _logger.warning('----------------------')
            _logger.warning(result[0].get('sum', 0.0))
            _logger.warning('----------------------')
            record.x_amount_available = result[0].get('sum', 0.0)