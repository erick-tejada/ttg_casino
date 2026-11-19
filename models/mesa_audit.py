# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

from . import slot_meter_parser


class Mesa(models.Model):
    _inherit = 'casino.mesa'

    drgt_code = fields.Char('Código DRGT', help='Código de la mesa en DRGT (ej. BJ01, RL02). Se usa para importar los '
                                                'reportes de mesas y el Chip Liability.')

    _sql_constraints = [
        ('unique_drgt_code', 'unique(company_id, drgt_code)', 'El código DRGT de la mesa debe ser único.'),
    ]


class MesaResultLine(models.Model):
    _name = 'casino.mesa.result'
    _description = 'Resultado de Mesa (DRGT)'
    _order = 'date desc, table_code'
    _rec_name = 'mesa_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', related='cuadre_id.currency_id', store=True)
    currency_usd_id = fields.Many2one('res.currency', related='cuadre_id.currency_usd_id')
    date = fields.Date('Fecha', related='cuadre_id.date', store=True, index=True)
    mesa_id = fields.Many2one('casino.mesa', string='Mesa', required=True, ondelete='restrict', index=True)
    table_code = fields.Char('Código DRGT')
    game = fields.Char('Juego')
    net_opening = fields.Monetary('Apertura (Net Opening)')
    net_closing = fields.Monetary('Cierre (Net Closing)')
    net_fills = fields.Monetary('Net Fills')
    pred_bill_dop = fields.Monetary('Billetes RD$ (Predicted)')
    pred_usd = fields.Monetary('USD (Predicted)', currency_field='currency_usd_id')
    pred_usd_dop = fields.Monetary('USD en RD$ según DRGT (Predicted)')
    pred_gross_drop = fields.Monetary('Gross Drop (Predicted)')
    pred_net_drop = fields.Monetary('Net Drop (Predicted)')
    act_usd = fields.Monetary('USD (Actual Count)', currency_field='currency_usd_id')
    act_usd_dop = fields.Monetary('USD en RD$ según DRGT (Actual Count)')
    act_bill_dop = fields.Monetary('Billetes RD$ (Actual Count)')
    act_gross_drop = fields.Monetary('Gross Drop (Actual Count)')
    act_net_drop = fields.Monetary('Net Drop (Actual Count)')
    variance_gross_drop = fields.Monetary('Variación Gross Drop')


class ChipLiabilityLine(models.Model):
    _name = 'casino.chip.liability'
    _description = 'Inventario de Fichas (Chip Liability DRGT)'
    _order = 'cuadre_id, location_type, location_code, chip_type, denomination'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True, index=True)
    location_type = fields.Selection([('cash_desk', 'Caja de Mesas'), ('table', 'Mesa')], string='Tipo de Ubicación',
                                     required=True)
    location_code = fields.Char('Ubicación')
    mesa_id = fields.Many2one('casino.mesa', string='Mesa', ondelete='restrict')
    chip_type = fields.Char('Tipo de Ficha')
    denomination = fields.Float('Denominación', digits=(16, 2))
    name = fields.Char('Ficha', compute='_compute_name', store=True)
    begin_qty = fields.Integer('Cantidad Inicial')
    begin_amount = fields.Monetary('Monto Inicial')
    move_qty = fields.Integer('Cantidad Movimiento')
    move_amount = fields.Monetary('Monto Movimiento')
    end_qty = fields.Integer('Cantidad Final', compute='_compute_end', store=True)
    end_amount = fields.Monetary('Monto Final', compute='_compute_end', store=True)

    @api.depends('chip_type', 'denomination')
    def _compute_name(self):
        for line in self:
            line.name = '%s RD$%s' % (line.chip_type or '', '{:,.0f}'.format(line.denomination)
                                      if float(line.denomination).is_integer() else '{:,.2f}'.format(line.denomination))

    @api.depends('begin_qty', 'begin_amount', 'move_qty', 'move_amount')
    def _compute_end(self):
        for line in self:
            line.end_qty = line.begin_qty + line.move_qty
            line.end_amount = line.begin_amount + line.move_amount


class CuadreDeCaja(models.Model):
    _inherit = 'casino.cuadre'

    mesa_result_ids = fields.One2many('casino.mesa.result', 'cuadre_id', 'Resultados por Mesa (DRGT)')
    chip_liability_ids = fields.One2many('casino.chip.liability', 'cuadre_id', 'Inventario de Fichas (DRGT)')
    mesa_audit_has_result = fields.Boolean('Tiene Resultados de Mesas', compute='_compute_mesa_audit', store=True)

    mesa_result_file = fields.Binary('Archivo de Resultados de Mesas', attachment=True, copy=False)
    mesa_result_filename = fields.Char('Nombre del Archivo de Resultados de Mesas', copy=False)
    mesa_result_fingerprint = fields.Char('Huella del Archivo de Mesas', copy=False, index=True)
    mesa_chip_file = fields.Binary('Archivo Chip Liability', attachment=True, copy=False)
    mesa_chip_filename = fields.Char('Nombre del Archivo Chip Liability', copy=False)
    mesa_import_date = fields.Datetime('Importado el (Mesas)', copy=False, readonly=True)
    mesa_import_user_id = fields.Many2one('res.users', 'Importado por (Mesas)', copy=False, readonly=True)

    # Cuadre de Mesas (Predicted Result)
    mesa_pred_bill_dop = fields.Monetary('Bill RD$ (Mesas)', compute='_compute_mesa_audit', store=True)
    mesa_pred_usd = fields.Monetary('Amount USD (Mesas)', currency_field='currency_usd_id', compute='_compute_mesa_audit', store=True)
    mesa_pred_usd_dop = fields.Monetary('USD Convertido (Mesas)', compute='_compute_mesa_audit', store=True)
    mesa_pred_gross_drop = fields.Monetary('Gross Drop (Mesas)', compute='_compute_mesa_audit', store=True)
    mesa_net_fills = fields.Monetary('Net Fills', compute='_compute_mesa_audit', store=True)
    mesa_audit_resultado = fields.Monetary('Ganancia / Pérdida Mesas', compute='_compute_mesa_audit', store=True,
                                           help='Gross Drop (Predicted Result) - Net Fills.')
    # Cuadre de Caja (Actual Count)
    mesa_act_bill_dop = fields.Monetary('Bill RD$ (Caja)', compute='_compute_mesa_audit', store=True)
    mesa_act_usd = fields.Monetary('Amount USD (Caja)', currency_field='currency_usd_id', compute='_compute_mesa_audit', store=True)
    mesa_act_usd_dop = fields.Monetary('USD Convertido (Caja)', compute='_compute_mesa_audit', store=True)
    mesa_act_gross_drop = fields.Monetary('Gross Drop (Caja)', compute='_compute_mesa_audit', store=True)
    mesa_pagos_caja = fields.Monetary('Pagos de Caja', compute='_compute_mesa_audit', store=True,
                                      help='Pagos de Mesas registrados en el cuadre: Pago Apuestas RD$ + Pago Apuestas USD '
                                           'convertido + Premios/Rifas de Mesas + Pagos Bancarizados de Mesas.')
    mesa_audit_caja_resultado = fields.Monetary('Ganancia / Pérdida Caja', compute='_compute_mesa_audit', store=True,
                                                help='Gross Drop (Actual Count) - Pagos de Caja.')
    # Conciliaciones
    mesa_chip_conciliacion = fields.Monetary('Chip Liability', compute='_compute_mesa_audit', store=True,
                                             help='Net Fills - Pagos de Caja.')
    mesa_variacion = fields.Monetary('Variación', compute='_compute_mesa_audit', store=True,
                                     help='Ganancia/Pérdida Mesas - Ganancia/Pérdida Caja.')
    mesa_fuera_tolerancia = fields.Boolean('Variación Fuera de Tolerancia', compute='_compute_mesa_audit', store=True)
    # Chip Liability (Caja de Mesas)
    mesa_chip_begin = fields.Monetary('Inventario Inicial Caja de Mesas', compute='_compute_mesa_chips', store=True)
    mesa_chip_movement = fields.Monetary('Movimiento Caja de Mesas', compute='_compute_mesa_chips', store=True)
    mesa_chip_end = fields.Monetary('Inventario Final Caja de Mesas', compute='_compute_mesa_chips', store=True)

    mesa_observaciones = fields.Text('Observaciones de Mesas', copy=False, tracking=True)
    mesa_estado = fields.Selection([
        ('sin_contadores', 'Sin resultados importados'),
        ('conciliado', 'Conciliado'),
        ('justificado', 'Variación justificada'),
        ('pendiente', 'Variación pendiente de justificación'),
    ], string='Estado de Conciliación de Mesas', compute='_compute_mesa_estado', store=True)
    mesa_approved = fields.Boolean('Auditoría de Mesas Aprobada', copy=False, readonly=True, tracking=True)
    mesa_approved_date = fields.Datetime('Mesas Aprobada el', copy=False, readonly=True)
    mesa_approved_user_id = fields.Many2one('res.users', 'Mesas Aprobada por', copy=False, readonly=True)

    MESA_LOCKED_FIELDS = ('mesa_observaciones', 'mesa_result_file', 'mesa_chip_file')

    @api.depends('mesa_result_ids.pred_bill_dop', 'mesa_result_ids.pred_usd', 'mesa_result_ids.net_fills',
                 'mesa_result_ids.act_bill_dop', 'mesa_result_ids.act_usd', 'casino_tasa_usd', 'pago_apuestas_mesas',
                 'pago_apuestas_mesas_usd', 'premios_mesa_total', 'pago_bancarizado_mesa_total',
                 'company_id.casino_mesa_audit_tolerance')
    def _compute_mesa_audit(self):
        for record in self:
            cur = record.currency_id or record.company_id.currency_id
            lines = record.mesa_result_ids
            rate = record.casino_tasa_usd
            pred_bill = sum(lines.mapped('pred_bill_dop'))
            pred_usd = sum(lines.mapped('pred_usd'))
            pred_usd_dop = cur.round(pred_usd * rate)
            pred_gross = pred_bill + pred_usd_dop
            fills = sum(lines.mapped('net_fills'))
            act_bill = sum(lines.mapped('act_bill_dop'))
            act_usd = sum(lines.mapped('act_usd'))
            act_usd_dop = cur.round(act_usd * rate)
            act_gross = act_bill + act_usd_dop
            pagos = cur.round(record.pago_apuestas_mesas + record.pago_apuestas_mesas_usd * rate
                              + record.premios_mesa_total + record.pago_bancarizado_mesa_total)
            resultado = cur.round(pred_gross - fills)
            caja = cur.round(act_gross - pagos)
            variacion = cur.round(resultado - caja) if lines else 0.0
            record.update({
                'mesa_audit_has_result': bool(lines),
                'mesa_pred_bill_dop': pred_bill, 'mesa_pred_usd': pred_usd, 'mesa_pred_usd_dop': pred_usd_dop,
                'mesa_pred_gross_drop': pred_gross, 'mesa_net_fills': fills, 'mesa_audit_resultado': resultado if lines else 0.0,
                'mesa_act_bill_dop': act_bill, 'mesa_act_usd': act_usd, 'mesa_act_usd_dop': act_usd_dop,
                'mesa_act_gross_drop': act_gross, 'mesa_pagos_caja': pagos,
                'mesa_audit_caja_resultado': caja if lines else 0.0,
                'mesa_chip_conciliacion': cur.round(fills - pagos) if lines else 0.0,
                'mesa_variacion': variacion,
                'mesa_fuera_tolerancia': bool(lines) and float_compare(
                    abs(variacion), record.company_id.casino_mesa_audit_tolerance, precision_digits=2) > 0,
            })

    @api.depends('chip_liability_ids.begin_amount', 'chip_liability_ids.move_amount', 'chip_liability_ids.location_type')
    def _compute_mesa_chips(self):
        for record in self:
            desk = record.chip_liability_ids.filtered(lambda l: l.location_type == 'cash_desk')
            record.mesa_chip_begin = sum(desk.mapped('begin_amount'))
            record.mesa_chip_movement = sum(desk.mapped('move_amount'))
            record.mesa_chip_end = record.mesa_chip_begin + record.mesa_chip_movement

    @api.depends('mesa_audit_has_result', 'mesa_fuera_tolerancia', 'mesa_observaciones')
    def _compute_mesa_estado(self):
        for record in self:
            if not record.mesa_audit_has_result:
                record.mesa_estado = 'sin_contadores'
            elif not record.mesa_fuera_tolerancia:
                record.mesa_estado = 'conciliado'
            elif (record.mesa_observaciones or '').strip():
                record.mesa_estado = 'justificado'
            else:
                record.mesa_estado = 'pendiente'

    def write(self, vals):
        if set(vals) & set(self.MESA_LOCKED_FIELDS) and not self.env.context.get('casino_audit_unlock'):
            approved = self.filtered('mesa_approved')
            if approved:
                raise UserError(_('La auditoría de mesas del %s ya fue aprobada; sus observaciones y archivos no se pueden '
                                  'modificar.') % ', '.join(approved.mapped(lambda r: r._slot_date_label())))
        return super().write(vals)

    # ------------------------------------------------------------------------------------------------
    # Importación
    # ------------------------------------------------------------------------------------------------
    def _check_mesa_import_allowed(self):
        if not self.env.user.has_group('ttg_casino.group_casino_audit'):
            raise UserError(_('Solo el Auditor puede importar los resultados de mesas.'))
        for record in self:
            if record.state == 'draft':
                raise UserError(_('El cuadre del %s todavía está en Borrador. Los resultados de mesas se importan después '
                                  'de que Caja lo presente al Auditor.') % record._slot_date_label())
            if record.mesa_approved:
                raise UserError(_('La auditoría de mesas del %s ya fue aprobada.') % record._slot_date_label())

    def _mesas_by_code(self, codes):
        mesas = self.env['casino.mesa'].with_context(active_test=False).search(
            [('drgt_code', 'in', list(codes)), ('company_id', '=', self.company_id.id)])
        by_code = {m.drgt_code: m for m in mesas}
        missing = sorted(set(codes) - set(by_code))
        if missing:
            raise UserError(_('Estas mesas de DRGT no tienen su código asignado en Odoo: %s. Asigne el "Código DRGT" en '
                              'Casino > Mesas y vuelva a importar.') % ', '.join(missing))
        return by_code

    def import_mesa_results(self, content, filename=False):
        """Importa el reporte de resultados de mesas de DRGT y reemplaza los resultados por mesa del cuadre."""
        self.ensure_one()
        self._check_mesa_import_allowed()
        try:
            parsed = slot_meter_parser.parse_table_result(content)
        except slot_meter_parser.SlotMeterFileError as e:
            raise UserError(str(e))
        duplicate = self.search([('company_id', '=', self.company_id.id), ('id', '!=', self.id),
                                 ('mesa_result_fingerprint', '=', parsed['fingerprint'])], limit=1)
        if duplicate:
            raise UserError(_('Este reporte de mesas ya fue importado en el cuadre del %s. Verifique que descargó el '
                              'reporte del día correcto (%s).') % (duplicate._slot_date_label(), self._slot_date_label()))
        by_code = self._mesas_by_code({l['table_code'] for l in parsed['lines']})
        self._check_mesa_files_match(results=parsed['lines'])
        previous = len(self.mesa_result_ids)
        self.mesa_result_ids.unlink()
        self.env['casino.mesa.result'].create([
            dict({k: v for k, v in line.items()}, cuadre_id=self.id, mesa_id=by_code[line['table_code']].id)
            for line in parsed['lines']])
        self.write({
            'mesa_result_file': base64.b64encode(content),
            'mesa_result_filename': filename or 'mesas.xls',
            'mesa_result_fingerprint': parsed['fingerprint'],
            'mesa_import_date': fields.Datetime.now(),
            'mesa_import_user_id': self.env.user.id,
        })
        body = _('Resultados de mesas de DRGT importados (%(file)s): %(count)s mesas, Ganancia/Pérdida Mesas %(res)s, '
                 'Ganancia/Pérdida Caja %(caja)s, Variación %(var)s.', file=filename or '', count=len(parsed['lines']),
                 res=self._fmt_amount(self.mesa_audit_resultado), caja=self._fmt_amount(self.mesa_audit_caja_resultado),
                 var=self._fmt_amount(self.mesa_variacion))
        if previous:
            body += ' ' + _('Se reemplazaron %s líneas de una importación anterior.') % previous
        self.message_post(body=body)
        return True

    def import_chip_liability(self, content, filename=False):
        """Importa el reporte Chip Liability de DRGT (inventario de fichas de la Caja de Mesas y de cada mesa)."""
        self.ensure_one()
        self._check_mesa_import_allowed()
        try:
            parsed = slot_meter_parser.parse_chip_liability(content)
        except slot_meter_parser.SlotMeterFileError as e:
            raise UserError(str(e))
        period = parsed['period']
        if not period:
            raise UserError(_('No se encontró el período ("Period: ...") en el Chip Liability. Expórtelo de DRGT sin '
                              'modificarlo.'))
        if period[0] != self.date or period[1] != self.date:
            raise UserError(_('El Chip Liability es del %(desde)s al %(hasta)s, pero el cuadre es del %(fecha)s.',
                              desde=period[0].strftime('%d/%m/%Y'), hasta=period[1].strftime('%d/%m/%Y'),
                              fecha=self._slot_date_label()))
        table_codes = {loc['code'] for loc in parsed['locations'] if loc['type'] == 'table'}
        by_code = self._mesas_by_code(table_codes) if table_codes else {}
        self._check_mesa_files_match(chips=parsed['locations'])
        self.chip_liability_ids.unlink()
        vals_list = []
        for loc in parsed['locations']:
            for line in loc['lines']:
                vals_list.append({
                    'cuadre_id': self.id, 'location_type': loc['type'], 'location_code': loc['code'],
                    'mesa_id': by_code[loc['code']].id if loc['type'] == 'table' else False,
                    'chip_type': line['chip_type'], 'denomination': line['denomination'],
                    'begin_qty': int(round(line['begin_qty'])), 'begin_amount': line['begin_amount'],
                    'move_qty': int(round(line['move_qty'])), 'move_amount': line['move_amount'],
                })
        self.env['casino.chip.liability'].create(vals_list)
        self.write({'mesa_chip_file': base64.b64encode(content), 'mesa_chip_filename': filename or 'chip_liability.xls'})
        self.message_post(body=_('Chip Liability de DRGT importado (%(file)s): Caja de Mesas inicial %(b)s, movimiento '
                                 '%(m)s, final %(e)s.', file=filename or '', b=self._fmt_amount(self.mesa_chip_begin),
                                 m=self._fmt_amount(self.mesa_chip_movement), e=self._fmt_amount(self.mesa_chip_end)))
        return True

    def _check_mesa_files_match(self, results=None, chips=None):
        """La apertura de cada mesa (Net Opening) debe ser su inventario inicial en el Chip Liability."""
        self.ensure_one()
        if results is None:
            results = [{'table_code': l.table_code, 'net_opening': l.net_opening} for l in self.mesa_result_ids]
        if chips is None:
            begin = {}
            for l in self.chip_liability_ids.filtered(lambda c: c.location_type == 'table'):
                begin[l.location_code] = begin.get(l.location_code, 0.0) + l.begin_amount
        else:
            begin = {loc['code']: sum(x['begin_amount'] for x in loc['lines']) for loc in chips if loc['type'] == 'table'}
        if not results or not begin:
            return
        issues = []
        for line in results:
            if line['table_code'] in begin and abs(begin[line['table_code']] - line['net_opening']) > 0.05:
                issues.append(_('%(mesa)s: apertura %(a)s, inventario inicial en Chip Liability %(b)s.',
                                mesa=line['table_code'], a=self._fmt_amount(line['net_opening']),
                                b=self._fmt_amount(begin[line['table_code']])))
        if issues:
            raise UserError(_('El reporte de mesas y el Chip Liability no corresponden al mismo día:\n%s') % '\n'.join(issues))

    def action_open_mesa_audit_import(self):
        self.ensure_one()
        self._check_mesa_import_allowed()
        return {
            'name': _('Importar Resultados de Mesas de DRGT'),
            'type': 'ir.actions.act_window',
            'res_model': 'casino.mesa.audit.import',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cuadre_id': self.id},
        }

    # ------------------------------------------------------------------------------------------------
    # Validación, aprobación e impresión
    # ------------------------------------------------------------------------------------------------
    def _check_mesa_audit(self):
        for record in self:
            if not record.mesa_audit_has_result:
                if record.company_id.casino_mesa_audit_required:
                    raise UserError(_('Debe importar el reporte de resultados de mesas de DRGT (pestaña "Auditoría de '
                                      'Mesas") antes de presentar el cuadre a Contabilidad.'))
                continue
            if record.company_id.casino_mesa_audit_required and not record.mesa_chip_file:
                raise UserError(_('Debe importar el Chip Liability de DRGT (pestaña "Auditoría de Mesas") antes de '
                                  'presentar el cuadre a Contabilidad.'))
            if record.mesa_fuera_tolerancia and not (record.mesa_observaciones or '').strip():
                raise UserError(_('La Variación de mesas es de %(var)s, mayor que la tolerancia de %(tol)s. Escriba la '
                                  'justificación en las Observaciones de la pestaña "Auditoría de Mesas" antes de aprobar.',
                                  var=record._fmt_amount(record.mesa_variacion),
                                  tol=record._fmt_amount(record.company_id.casino_mesa_audit_tolerance)))

    def _approve_mesa_audit(self):
        estados = dict(self._fields['mesa_estado']._description_selection(self.env))
        for record in self.filtered(lambda r: r.mesa_audit_has_result and not r.mesa_approved):
            record.with_context(casino_audit_unlock=True).write({
                'mesa_approved': True, 'mesa_approved_date': fields.Datetime.now(),
                'mesa_approved_user_id': self.env.user.id,
            })
            body = _('Auditoría de mesas aprobada: Ganancia/Pérdida Mesas %(res)s, Ganancia/Pérdida Caja %(caja)s, '
                     'Chip Liability %(chip)s, Variación %(var)s (%(estado)s).',
                     res=record._fmt_amount(record.mesa_audit_resultado),
                     caja=record._fmt_amount(record.mesa_audit_caja_resultado),
                     chip=record._fmt_amount(record.mesa_chip_conciliacion), var=record._fmt_amount(record.mesa_variacion),
                     estado=estados[record.mesa_estado])
            if (record.mesa_observaciones or '').strip():
                body += ' ' + _('Observaciones: %s') % record.mesa_observaciones.strip()
            record.message_post(body=body)

    def action_accounting(self):
        self._compute_all()
        self._check_mesa_audit()
        res = super().action_accounting()
        self._approve_mesa_audit()
        return res

    def action_approve_mesa_audit(self):
        """Aprobar la auditoría de mesas de un cuadre ya en Contabilidad o cerrado (carga de días anteriores)."""
        if not self.env.user.has_group('ttg_casino.group_casino_audit'):
            raise UserError(_('Solo el Auditor puede aprobar la auditoría de mesas.'))
        for record in self:
            if not record.mesa_audit_has_result:
                raise UserError(_('Importe el reporte de resultados de mesas antes de aprobar la auditoría.'))
        self._check_mesa_audit()
        self._approve_mesa_audit()
        return True

    def action_draft(self):
        res = super().action_draft()
        approved = self.filtered('mesa_approved')
        if approved:
            approved.with_context(casino_audit_unlock=True).write({
                'mesa_approved': False, 'mesa_approved_date': False, 'mesa_approved_user_id': False})
            for record in approved:
                record.message_post(body=_('El cuadre volvió a Borrador: la auditoría de mesas debe aprobarse de nuevo.'))
        return res

    def action_print_mesa_audit(self):
        self.ensure_one()
        return self.env.ref('ttg_casino.action_report_mesa_audit').report_action(self)
