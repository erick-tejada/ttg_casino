
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    casino_tasa_usd = fields.Float('Tasa USD Caja', related='company_id.casino_tasa_usd', readonly=False, help='Tasa USD utilizada para el cambio de Divisas en el Módulo de Ingresos.')
