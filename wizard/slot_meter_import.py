# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SlotMeterImport(models.TransientModel):
    _name = 'casino.slot.meter.import'
    _description = 'Importar Contadores de DRGT'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    date = fields.Date('Fecha del Cuadre', related='cuadre_id.date')
    currency_id = fields.Many2one('res.currency', related='cuadre_id.currency_id')
    file = fields.Binary('Reporte "Slot Analysis" de DRGT')
    filename = fields.Char('Nombre del Archivo')
    balance_file = fields.Binary('Reporte "Operation Balance" de DRGT',
                                 help='Si lo sube, Handpay Liability y Variación de Efectivo se toman de este archivo.')
    balance_filename = fields.Char('Nombre del Archivo Operation Balance')
    has_lines = fields.Boolean(compute='_compute_has_lines')
    audit_handpay_liability = fields.Monetary('Handpay Liability', help='"Handpay Liability Movement" del resumen de DRGT.')
    audit_variacion_efectivo = fields.Monetary('Variación de Efectivo', help='"EFT Cash Liability Movement" del resumen de DRGT.')
    audit_billetes_no_registrados = fields.Monetary('Billetes No Registrados',
                                                    help='Billetes que la máquina no contabilizó pero aparecieron en el conteo de Caja.')

    @api.depends('cuadre_id')
    def _compute_has_lines(self):
        for wizard in self:
            wizard.has_lines = bool(wizard.cuadre_id.slot_meter_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        cuadre = self.env['casino.cuadre'].browse(res.get('cuadre_id') or self.env.context.get('default_cuadre_id'))
        if cuadre.exists():
            res.update({
                'audit_handpay_liability': cuadre.audit_handpay_liability,
                'audit_variacion_efectivo': cuadre.audit_variacion_efectivo,
                'audit_billetes_no_registrados': cuadre.audit_billetes_no_registrados,
            })
        return res

    def action_import(self):
        self.ensure_one()
        cuadre = self.cuadre_id
        if self.file:
            cuadre.import_slot_meters(base64.b64decode(self.file), self.filename)
        elif not cuadre.slot_meter_ids:
            raise UserError(_('Seleccione el archivo "Slot Analysis" exportado desde DRGT.'))
        else:
            cuadre._check_slot_meter_import_allowed()
        vals = {'audit_billetes_no_registrados': self.audit_billetes_no_registrados}
        if self.balance_file:
            cuadre.import_operation_balance(base64.b64decode(self.balance_file), self.balance_filename)
        else:
            vals.update({
                'audit_handpay_liability': self.audit_handpay_liability,
                'audit_variacion_efectivo': self.audit_variacion_efectivo,
            })
        cuadre.write(vals)
        return {'type': 'ir.actions.act_window_close'}
