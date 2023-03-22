
from odoo import fields, models, api


class ResComapany(models.Model):
    _inherit = 'res.company'

    casino_tasa_usd = fields.Float('Tasa USD Caja', help='Tasa USD utilizada para el cambio de Divisas en el Módulo de Ingresos.')