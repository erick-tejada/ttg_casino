# -*- coding: utf-8 -*-
import base64

from odoo import fields, models, _
from odoo.exceptions import UserError


class MesaAuditImport(models.TransientModel):
    _name = 'casino.mesa.audit.import'
    _description = 'Importar Resultados de Mesas de DRGT'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    date = fields.Date('Fecha del Cuadre', related='cuadre_id.date')
    casino_tasa_usd = fields.Float('Tasa USD del Cuadre', related='cuadre_id.casino_tasa_usd')
    has_lines = fields.Boolean(related='cuadre_id.mesa_audit_has_result')
    result_file = fields.Binary('Resultados de Mesas')
    result_filename = fields.Char('Nombre del Archivo de Resultados')
    chip_file = fields.Binary('Chip Liability')
    chip_filename = fields.Char('Nombre del Archivo Chip Liability')

    def action_import(self):
        self.ensure_one()
        if not (self.result_file or self.chip_file):
            raise UserError(_('Seleccione el reporte de resultados de mesas y/o el Chip Liability exportados desde DRGT.'))
        cuadre = self.cuadre_id
        if self.chip_file:
            cuadre.import_chip_liability(base64.b64decode(self.chip_file), self.chip_filename)
        if self.result_file:
            cuadre.import_mesa_results(base64.b64decode(self.result_file), self.result_filename)
        return {'type': 'ir.actions.act_window_close'}
