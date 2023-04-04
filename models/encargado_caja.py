from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class MarcaMaquina(models.Model):
    _name = 'casino.encargado.caja'
    _description = "Encargado de Caja"

    name = fields.Char('Nombre', required=True)
    active = fields.Boolean('Activo', default=True)