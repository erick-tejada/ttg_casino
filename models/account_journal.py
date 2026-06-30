from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    use_for_pago_bancarizado = fields.Boolean(
        'Usar para Pago Bancarizado',
        help='Si está activo, este diario estará disponible como "Banco" en las líneas de Pago Bancarizado del Casino.',
    )
