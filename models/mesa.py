from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class Mesa(models.Model):
    _name = 'casino.mesa'
    _description = "Máquina"

    name = fields.Char('Nombre', required=True)
    company_id = fields.Many2one('res.company', 'Compañia', required=True, index=True, default=lambda self: self.env.company)
    active = fields.Boolean('Activo', default=True)

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'El nombre de la Mesa debe de ser único!'),
    ]
