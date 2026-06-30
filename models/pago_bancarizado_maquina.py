from odoo import models, fields


class CasinoPagoBancarizadoMaquina(models.Model):
    _name = 'casino.pago.bancarizado.maquina'
    _inherit = 'casino.pago.bancarizado.mixin'
    _description = "Pagos Bancarizados Maquinas"
    _order = 'cuadre_id,partner_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')

    def _get_caja_account(self):
        self.ensure_one()
        return self.company_id.caja_maquina_account_id
