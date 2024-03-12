from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class TipoError(models.Model):
    _name = 'casino.tipo.premio'
    _description = "Tipo de Premio"

    name = fields.Char('Nombre', required=True)
    company_id = fields.Many2one('res.company', 'Compañia', required=True, index=True, default=lambda self: self.env.company)
    active = fields.Boolean('Activo', default=True)

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'El nombre del tipo de Rifa/Premio debe de ser único!'),
    ]
