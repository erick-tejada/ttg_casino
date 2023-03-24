
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    casino_tasa_usd = fields.Float('Tasa USD Caja', related='company_id.casino_tasa_usd', readonly=False, help='Tasa USD utilizada para el cambio de Divisas en el Módulo de Ingresos.')

    # Comisiones de Tarjeta de Credito
    tc_itbis_percent = fields.Float(related='company_id.tc_itbis_percent', readonly=False)
    tc_itbis_account_id = fields.Many2one(related='company_id.tc_itbis_account_id', readonly=False)
    tc_comision_percent = fields.Float(related='company_id.tc_comision_percent', readonly=False)
    tc_comision_account_id = fields.Many2one(related='company_id.tc_comision_account_id', readonly=False)