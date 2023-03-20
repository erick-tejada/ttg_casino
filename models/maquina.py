from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class Maquina(models.Model):
    _name = 'casino.maquina'
    _description = "Máquina"
    _order = 'code'

    code = fields.Integer('Secuencia', default=1, required=True)
    name = fields.Char('Nombre', compute='_compute_name', store=True)
    company_id = fields.Many2one('res.company', 'Compañia', required=True, index=True, default=lambda self: self.env.company)
    brand_id = fields.Many2one('casino.maquina.marca', string='Marca', related='model_id.brand_id', store=True, ondelete='restrict')
    model_id = fields.Many2one('casino.maquina.modelo', string='Modelo', required=True)
    active = fields.Boolean('Activo', default=True)

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'El código de la maquina debe de ser único!'),
    ]

    @api.depends('code', 'brand_id', 'model_id')
    def _compute_name(self):
        for record in self:
            if record.code and record.brand_id and record.model_id:
                record.name = '%d %s %s' % (record.code, record.brand_id.name, record.model_id.name)
            else:
                record.name = ''


class MaquinaMarca(models.Model):
    _name = 'casino.maquina.marca'
    _description = "Marca Máquina"

    name = fields.Char('Nombre', required=True)
    model_ids = fields.One2many('casino.maquina.modelo', 'brand_id', string='Modelos')
    active = fields.Boolean('Activo', default=True)


class MaquinaModelo(models.Model):
    _name = 'casino.maquina.modelo'
    _description = "Modelo Máquina"

    name = fields.Char('Nombre', required=True)
    brand_id = fields.Many2one('casino.maquina.marca', 'Marca', ondelete='cascade')
