
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    casino_tasa_usd = fields.Float('Tasa USD Caja', default=55.0, related='company_id.casino_tasa_usd', readonly=False, help='Tasa USD utilizada para el cambio de Divisas en el Módulo de Ingresos.')
