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