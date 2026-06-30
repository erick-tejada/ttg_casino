from odoo import models


class CasinoPagoBancarizadoMaquina(models.Model):
    _name = 'casino.pago.bancarizado.maquina'
    _inherit = 'casino.pago.bancarizado.mixin'
    _description = "Pagos Bancarizados Maquinas"
    _order = 'cuadre_id,partner_id'

    def _get_caja_account(self):
        self.ensure_one()
        return self.company_id.caja_maquina_account_id
