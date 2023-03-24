
from odoo import fields, models, api


class ResComapany(models.Model):
    _inherit = 'res.company'

    casino_tasa_usd = fields.Float('Tasa USD Caja', default=55.0, help='Tasa USD utilizada para el cambio de Divisas en el Módulo de Ingresos.')

    # Comisiones de Tarjeta de Credito
    tc_itbis_percent = fields.Float('% Retencion ITBIS', default=0.02, help='%% de ITBIS Retenido en los cobros de Tarjeta de Crédito.')
    tc_itbis_account_id = fields.Many2one('account.account', 'Cuenta de Retencion ITBIS', help='Cuenta donde se registrará el ITBIS Retenido en los cobros de Tarjeta de Crédito.')
    tc_comision_percent = fields.Float('% Gasto de Comision', default=0.0345, help='%% de Comisión Retenida en los cobros de Tarjeta de Crédito.')
    tc_comision_account_id = fields.Many2one('account.account', 'Cuenta de Gasto de Comisión', help='Cuenta donde se registrará la Comisión Retenida en los cobros de Tarjeta de Crédito.')