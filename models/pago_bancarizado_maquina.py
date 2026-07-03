from odoo import models, fields


class CasinoPagoBancarizadoMaquina(models.Model):
    _name = 'casino.pago.bancarizado.maquina'
    _inherit = 'casino.pago.bancarizado.mixin'
    _description = "Pagos Bancarizados Maquinas"
    _order = 'cuadre_id,partner_id'

    employee_sales_id = fields.Many2one('hr.employee', string="Slot", domain="['|', ('department_id.name', 'ilike', 'MAQUINA'),('department_id','=',13)]")

    def _get_caja_account(self):
        self.ensure_one()
        return self.company_id.caja_maquina_account_id
