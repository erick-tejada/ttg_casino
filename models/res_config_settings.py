
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    casino_tasa_usd = fields.Float('Tasa USD Caja', related='company_id.casino_tasa_usd', readonly=False, help='Tasa USD utilizada para el cambio de Divisas en el Módulo de Ingresos.')

    # Comisiones de Tarjeta de Credito
    tc_itbis_percent = fields.Float(related='company_id.tc_itbis_percent', readonly=False)
    tc_itbis_account_id = fields.Many2one(related='company_id.tc_itbis_account_id', readonly=False)
    tc_comision_percent = fields.Float(related='company_id.tc_comision_percent', readonly=False)
    tc_comision_account_id = fields.Many2one(related='company_id.tc_comision_account_id', readonly=False)
    
    # Fondos
    dop_boveda_fondo = fields.Float(related='company_id.dop_boveda_fondo', readonly=False, help='Fondo en DOP a mantener en la Bóveda de Pesos.')
    usd_boveda_fondo = fields.Float(related='company_id.usd_boveda_fondo', readonly=False, help='Fondo en USD a mantener en la Bóveda de Dólares.')
    dop_boveda_account_id = fields.Many2one(related='company_id.dop_boveda_account_id', readonly=False, help='Cuenta con valor en Bóveda de Pesos.')
    usd_boveda_account_id = fields.Many2one(related='company_id.usd_boveda_account_id', readonly=False, help='Cuenta con valor en Bóveda de Dólares.')