# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

from . import slot_meter_parser


class SlotMeter(models.Model):
    _name = 'casino.slot.meter'
    _description = 'Contadores de Slot (DRGT)'
    _order = 'date desc, code'
    _rec_name = 'maquina_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True, index=True)

    maquina_id = fields.Many2one('casino.maquina', string='Máquina', required=True, ondelete='restrict', index=True)
    code = fields.Integer('Código', related='maquina_id.code', store=True)
    brand_id = fields.Many2one('casino.maquina.marca', string='Marca', related='maquina_id.brand_id', store=True)
    model_id = fields.Many2one('casino.maquina.modelo', string='Modelo', related='maquina_id.model_id', store=True)

    # Datos de la máquina según DRGT
    position = fields.Char('Posición DRGT')
    inventory = fields.Char('Inventario DRGT')
    serial = fields.Char('Serial')
    manufacturer = fields.Char('Fabricante DRGT')
    model_name = fields.Char('Modelo DRGT')
    game = fields.Char('Juego')

    # Contadores (los nombres entre paréntesis son las columnas del reporte de DRGT)
    egm_audit = fields.Monetary('Auditoría EGM (EGM Audit)')
    audit = fields.Monetary('Auditoría (Audit)')
    ngwine = fields.Monetary('Ganancia Contadores (NGWINE)')
    tap = fields.Monetary('Pagos Manuales (TAP)')
    cre = fields.Monetary('Crédito en Máquina (CRE)')
    gtie = fields.Monetary('Total Jugado (GTIE)')
    gtoe = fields.Monetary('Total Ganado (GTOE)')
    gjoe = fields.Monetary('Jackpots (GJOE)')
    gtin = fields.Monetary('GTIN')
    gtine = fields.Monetary('GTINE')
    gp = fields.Integer('Juegos Jugados (GP)')
    bdie = fields.Monetary('Billetes Recibidos (BDIE)')
    ccoe = fields.Monetary('Créditos Cancelados (CCOE)')
    pwe = fields.Monetary('PWE')
    clic = fields.Monetary('Entrada desde Tarjeta (CLIC)')
    cloc = fields.Monetary('Salida a Tarjeta (CLOC)')
    avg_bet = fields.Monetary('Apuesta Promedio (Avg. Bet)')
    retention = fields.Float('Retención (Retention %)', digits=(16, 4), help='Fracción: 0.25 = 25%.')
    et = fields.Monetary('Total Entradas (ET)')
    st = fields.Monetary('Total Salidas (ST)')
    extra_data = fields.Json('Otras Columnas', help='Columnas del reporte de DRGT que no tienen un campo propio.')

    _sql_constraints = [
        ('cuadre_maquina_uniq', 'unique(cuadre_id, maquina_id)', 'La máquina ya tiene contadores en este cuadre.'),
    ]


class CuadreDeCaja(models.Model):
    _inherit = 'casino.cuadre'

    slot_meter_ids = fields.One2many('casino.slot.meter', 'cuadre_id', 'Contadores de Slot (DRGT)')
    slot_meter_count = fields.Integer('Máquinas en Contadores', compute='_compute_slot_meter_count')
    slot_meter_file = fields.Binary('Archivo de Contadores', attachment=True, copy=False)
    slot_meter_filename = fields.Char('Nombre del Archivo', copy=False)
    slot_meter_fingerprint = fields.Char('Huella del Archivo', copy=False, index=True,
                                         help='Identifica el contenido del archivo importado, para no importar el mismo reporte en dos cuadres.')
    slot_meter_import_date = fields.Datetime('Importado el', copy=False, readonly=True)
    slot_meter_import_user_id = fields.Many2one('res.users', 'Importado por', copy=False, readonly=True)

    # Cuadro de auditoría (fórmula del auditor)
    audit_ngwine = fields.Monetary('Ganancia según Contadores (NGWINE)', compute='_compute_slot_audit', store=True)
    audit_handpay_liability = fields.Monetary('Handpay Liability', copy=False, tracking=True,
                                              help='"Handpay Liability Movement" del resumen de DRGT.')
    audit_sobrantes = fields.Monetary('Sobrantes', compute='_compute_slot_audit', store=True,
                                      help='Total de Sobrantes registrados en este cuadre.')
    audit_rifas = fields.Monetary('Rifas', compute='_compute_slot_audit', store=True,
                                  help='Total de Premios/Rifas de Máquinas registrados en este cuadre.')
    audit_devoluciones = fields.Monetary('Devoluciones', compute='_compute_slot_audit', store=True,
                                        help='Total de Devoluciones registradas en este cuadre.')
    audit_variacion_efectivo = fields.Monetary('Variación de Efectivo', copy=False, tracking=True,
                                               help='"EFT Cash Liability Movement" del resumen de DRGT.')
    audit_billetes_no_registrados = fields.Monetary('Billetes No Registrados', copy=False, tracking=True,
                                                    help='Billetes que la máquina no contabilizó pero aparecieron en el conteo de Caja.')
    audit_credito_maquina = fields.Monetary('Crédito en Máquina (CRE)', compute='_compute_slot_audit', store=True,
                                            help='Suma de la columna CRE del archivo de contadores.')
    audit_resultado = fields.Monetary('Resultado según Contadores', compute='_compute_slot_audit', store=True)
    audit_diferencia = fields.Monetary('Diferencia vs Resultado Caja Máquina', compute='_compute_slot_audit', store=True,
                                       help='Resultado según Contadores menos Resultado Caja Máquina.')
    audit_fuera_tolerancia = fields.Boolean('Fuera de Tolerancia', compute='_compute_slot_audit', store=True)
    audit_justificacion = fields.Text('Observaciones de Auditoría', copy=False, tracking=True,
                                      help='Observaciones y justificaciones del Auditor. Obligatorias si la diferencia '
                                           'supera la tolerancia. Se bloquean al aprobar la auditoría.')
    audit_estado = fields.Selection([
        ('sin_contadores', 'Sin contadores importados'),
        ('conciliado', 'Conciliado'),
        ('justificado', 'Diferencia justificada'),
        ('pendiente', 'Diferencia pendiente de justificación'),
    ], string='Estado de Conciliación', compute='_compute_audit_estado', store=True)
    audit_approved = fields.Boolean('Auditoría Aprobada', copy=False, readonly=True, tracking=True)
    audit_approved_date = fields.Datetime('Aprobada el', copy=False, readonly=True)
    audit_approved_user_id = fields.Many2one('res.users', 'Aprobada por', copy=False, readonly=True)

    # Reporte "Operation Balance" de DRGT
    audit_balance_file = fields.Binary('Archivo Operation Balance', attachment=True, copy=False)
    audit_balance_filename = fields.Char('Nombre del Archivo Operation Balance', copy=False)
    audit_balance_credito_maquina = fields.Monetary('Crédito en Máquina según Operation Balance', copy=False, readonly=True,
                                                    help='"Credit Meter Cash Liability Movement". Se compara con la suma de la columna CRE.')
    audit_balance_egm_win_loss = fields.Monetary('Ganancia EGM según Operation Balance', copy=False, readonly=True,
                                                 help='"EGM Cash Win/Loss Meters". Se compara con la suma de la columna NGWINE.')

    AUDIT_LOCKED_FIELDS = ('audit_justificacion', 'audit_handpay_liability', 'audit_variacion_efectivo',
                           'audit_billetes_no_registrados', 'slot_meter_file', 'audit_balance_file')

    @api.depends('slot_meter_ids', 'audit_fuera_tolerancia', 'audit_justificacion')
    def _compute_audit_estado(self):
        for record in self:
            if not record.slot_meter_ids:
                record.audit_estado = 'sin_contadores'
            elif not record.audit_fuera_tolerancia:
                record.audit_estado = 'conciliado'
            elif (record.audit_justificacion or '').strip():
                record.audit_estado = 'justificado'
            else:
                record.audit_estado = 'pendiente'

    def write(self, vals):
        locked = set(vals) & set(self.AUDIT_LOCKED_FIELDS)
        if locked and not self.env.context.get('casino_audit_unlock'):
            approved = self.filtered('audit_approved')
            if approved:
                raise UserError(_('La auditoría de contadores del %s ya fue aprobada; sus observaciones y valores no se '
                                  'pueden modificar.') % ', '.join(approved.mapped(lambda r: r._slot_date_label())))
        return super().write(vals)

    def _compute_slot_meter_count(self):
        data = self.env['casino.slot.meter'].sudo()._read_group([('cuadre_id', 'in', self.ids)], ['cuadre_id'], ['__count'])
        counts = {cuadre.id: count for cuadre, count in data}
        for record in self:
            record.slot_meter_count = counts.get(record.id, 0)

    @api.depends('slot_meter_ids.ngwine', 'slot_meter_ids.cre', 'audit_handpay_liability', 'audit_variacion_efectivo',
                 'audit_billetes_no_registrados', 'sobrante_total', 'premios_maquina_total', 'devolucion_total',
                 'resultado_caja_maquina', 'company_id.casino_slot_audit_tolerance')
    def _compute_slot_audit(self):
        for record in self:
            currency = record.currency_id or record.company_id.currency_id
            ngwine = currency.round(sum(record.slot_meter_ids.mapped('ngwine')))
            credito = currency.round(sum(record.slot_meter_ids.mapped('cre')))
            resultado = (ngwine
                         + record.audit_handpay_liability
                         + record.sobrante_total
                         - record.premios_maquina_total
                         - record.devolucion_total
                         + record.audit_variacion_efectivo
                         + record.audit_billetes_no_registrados
                         + credito)
            resultado = currency.round(resultado)
            diferencia = currency.round(resultado - record.resultado_caja_maquina) if record.slot_meter_ids else 0.0
            tolerance = record.company_id.casino_slot_audit_tolerance
            record.audit_ngwine = ngwine
            record.audit_credito_maquina = credito
            record.audit_sobrantes = record.sobrante_total
            record.audit_rifas = record.premios_maquina_total
            record.audit_devoluciones = record.devolucion_total
            record.audit_resultado = resultado if record.slot_meter_ids else 0.0
            record.audit_diferencia = diferencia
            record.audit_fuera_tolerancia = bool(record.slot_meter_ids) and float_compare(
                abs(diferencia), tolerance, precision_digits=2) > 0

    # ------------------------------------------------------------------------------------------------
    # Importación
    # ------------------------------------------------------------------------------------------------
    def _check_slot_meter_import_allowed(self):
        if not self.env.user.has_group('ttg_casino.group_casino_audit'):
            raise UserError(_('Solo el Auditor puede importar los contadores de las máquinas.'))
        for record in self:
            if record.audit_approved:
                raise UserError(_('La auditoría de contadores del %s ya fue aprobada.') % record._slot_date_label())
            if record.state == 'draft':
                raise UserError(_('El cuadre del %s todavía está en Borrador. Los contadores se importan después de que Caja '
                                  'lo presente al Auditor.') % record._slot_date_label())

    def _slot_date_label(self):
        return self.date.strftime('%d/%m/%Y') if self.date else ''

    def import_slot_meters(self, content, filename=False):
        """Importa el reporte "Slot Analysis" de DRGT y reemplaza los contadores del cuadre."""
        self.ensure_one()
        self._check_slot_meter_import_allowed()
        try:
            parsed = slot_meter_parser.parse(content)
        except slot_meter_parser.SlotMeterFileError as e:
            raise UserError(str(e))

        duplicate = self.search([('company_id', '=', self.company_id.id), ('id', '!=', self.id),
                                 ('slot_meter_fingerprint', '=', parsed['fingerprint'])], limit=1)
        if duplicate:
            raise UserError(_('Este archivo ya fue importado en el cuadre del %s. Verifique que descargó el reporte del '
                              'día correcto (%s).') % (duplicate._slot_date_label(), self._slot_date_label()))

        codes = [line['inventory_code'] for line in parsed['lines']]
        machines = self.env['casino.maquina'].with_context(active_test=False).search(
            [('code', 'in', codes), ('company_id', '=', self.company_id.id)])
        by_code = {m.code: m for m in machines}
        missing = sorted(set(codes) - set(by_code))
        if missing:
            raise UserError(_('Estas máquinas del archivo no existen en el listado de Máquinas: %s. '
                              'Regístrelas (Casino > Máquinas) y vuelva a importar.') % ', '.join(str(c) for c in missing))

        previous = len(self.slot_meter_ids)
        self.slot_meter_ids.unlink()
        vals_list = []
        text_fields = {f for f, is_text in slot_meter_parser.COLUMNS.values() if is_text}
        for line in parsed['lines']:
            vals = {'cuadre_id': self.id, 'maquina_id': by_code[line['inventory_code']].id}
            for field, _is_text in slot_meter_parser.COLUMNS.values():
                value = line.get(field)
                if field == 'gp':
                    value = int(round(value or 0))
                vals[field] = value if field in text_fields or value is not None else 0.0
            vals['extra_data'] = line['extra'] or False
            vals_list.append(vals)
        self.env['casino.slot.meter'].create(vals_list)
        self.write({
            'slot_meter_file': base64.b64encode(content),
            'slot_meter_filename': filename or 'contadores.xls',
            'slot_meter_fingerprint': parsed['fingerprint'],
            'slot_meter_import_date': fields.Datetime.now(),
            'slot_meter_import_user_id': self.env.user.id,
        })
        body = _('Contadores de DRGT importados (%(file)s): %(count)s máquinas, Ganancia según Contadores %(ngwine)s.',
                 file=filename or '', count=len(parsed['lines']), ngwine=self._fmt_amount(self.audit_ngwine))
        if previous:
            body += ' ' + _('Se reemplazaron %s líneas de una importación anterior.') % previous
        self.message_post(body=body)
        self._check_slot_files_match()
        return True

    def import_operation_balance(self, content, filename=False):
        """Importa el reporte "Operation Balance" de DRGT: llena Handpay Liability y Variación de Efectivo."""
        self.ensure_one()
        self._check_slot_meter_import_allowed()
        try:
            parsed = slot_meter_parser.parse_overview(content)
        except slot_meter_parser.SlotMeterFileError as e:
            raise UserError(str(e))
        period = parsed['period']
        if not period:
            raise UserError(_('No se encontró el período ("Period: ...") en el reporte Operation Balance. Expórtelo de '
                              'DRGT sin modificarlo.'))
        if period[0] != self.date or period[1] != self.date:
            raise UserError(_('El reporte Operation Balance es del %(desde)s al %(hasta)s, pero el cuadre es del %(fecha)s.',
                              desde=period[0].strftime('%d/%m/%Y'), hasta=period[1].strftime('%d/%m/%Y'),
                              fecha=self._slot_date_label()))
        values = parsed['values']
        self._check_slot_files_match(egm=values.get('egm_win_loss', 0.0), credito=values['credito_maquina'], has_balance=True)
        self.write({
            'audit_handpay_liability': values['handpay_liability'],
            'audit_variacion_efectivo': values['variacion_efectivo'],
            'audit_balance_credito_maquina': values['credito_maquina'],
            'audit_balance_egm_win_loss': values.get('egm_win_loss', 0.0),
            'audit_balance_file': base64.b64encode(content),
            'audit_balance_filename': filename or 'operation_balance.xls',
        })
        self.message_post(body=_('Operation Balance de DRGT importado (%(file)s): Handpay Liability %(hp)s, Variación de '
                                 'Efectivo %(var)s.', file=filename or '', hp=self._fmt_amount(values['handpay_liability']),
                                 var=self._fmt_amount(values['variacion_efectivo'])))
        return True

    def _slot_files_mismatches(self, egm=None, credito=None, has_balance=None):
        """Diferencias entre el Slot Analysis y el Operation Balance (señal de archivos de días distintos)."""
        self.ensure_one()
        issues = []
        has_balance = bool(self.audit_balance_file) if has_balance is None else has_balance
        if not (self.slot_meter_ids and has_balance):
            return issues
        egm = self.audit_balance_egm_win_loss if egm is None else egm
        credito = self.audit_balance_credito_maquina if credito is None else credito
        currency = self.currency_id or self.company_id.currency_id
        ngwine = currency.round(sum(self.slot_meter_ids.mapped('ngwine')))
        cre = currency.round(sum(self.slot_meter_ids.mapped('cre')))
        if float_compare(ngwine, egm, precision_digits=1) != 0:
            issues.append(_('Ganancia de contadores: Slot Analysis %(a)s, Operation Balance %(b)s.',
                            a=self._fmt_amount(ngwine), b=self._fmt_amount(egm)))
        if float_compare(cre, credito, precision_digits=1) != 0:
            issues.append(_('Crédito en máquina: Slot Analysis %(a)s, Operation Balance %(b)s.',
                            a=self._fmt_amount(cre), b=self._fmt_amount(credito)))
        return issues

    def _check_slot_files_match(self, **kwargs):
        for record in self:
            issues = record._slot_files_mismatches(**kwargs)
            if issues:
                raise UserError(_('El Slot Analysis y el Operation Balance no corresponden al mismo día:\n%s')
                                % '\n'.join(issues))

    def _fmt_amount(self, amount):
        return '{:,.2f}'.format(amount)

    def action_open_slot_meter_import(self):
        self.ensure_one()
        self._check_slot_meter_import_allowed()
        return {
            'name': _('Importar Contadores de DRGT'),
            'type': 'ir.actions.act_window',
            'res_model': 'casino.slot.meter.import',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cuadre_id': self.id},
        }

    def action_open_slot_meters(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('ttg_casino.action_slot_meter')
        action['domain'] = [('cuadre_id', '=', self.id)]
        action['context'] = {}
        action['name'] = _('Contadores del %s') % self._slot_date_label()
        return action

    # ------------------------------------------------------------------------------------------------
    # Validación al presentar a Contabilidad
    # ------------------------------------------------------------------------------------------------
    def _check_slot_audit(self):
        for record in self:
            if not record.slot_meter_ids:
                if record.company_id.casino_slot_audit_required:
                    raise UserError(_('Debe importar el archivo de contadores de DRGT (pestaña "Auditoría de Contadores") '
                                      'antes de presentar el cuadre a Contabilidad.'))
                continue
            if record.audit_fuera_tolerancia and not (record.audit_justificacion or '').strip():
                raise UserError(_('La diferencia entre los contadores y Caja es de %(diff)s, mayor que la tolerancia de '
                                  '%(tol)s. Escriba la justificación en las Observaciones de Auditoría antes de '
                                  'aprobar la auditoría.',
                                  diff=record._fmt_amount(record.audit_diferencia),
                                  tol=record._fmt_amount(record.company_id.casino_slot_audit_tolerance)))

    def _approve_slot_audit(self):
        for record in self.filtered(lambda r: r.slot_meter_ids and not r.audit_approved):
            record.with_context(casino_audit_unlock=True).write({
                'audit_approved': True,
                'audit_approved_date': fields.Datetime.now(),
                'audit_approved_user_id': self.env.user.id,
            })
            body = _('Auditoría de contadores aprobada: Resultado según Contadores %(res)s, Resultado Caja Máquina %(caja)s, '
                     'diferencia %(diff)s (%(estado)s).', res=record._fmt_amount(record.audit_resultado),
                     caja=record._fmt_amount(record.resultado_caja_maquina), diff=record._fmt_amount(record.audit_diferencia),
                     estado=dict(record._fields['audit_estado']._description_selection(self.env))[record.audit_estado])
            if (record.audit_justificacion or '').strip():
                body += ' ' + _('Observaciones: %s') % record.audit_justificacion.strip()
            record.message_post(body=body)

    def action_accounting(self):
        self._compute_all()
        self._check_slot_audit()
        res = super().action_accounting()
        self._approve_slot_audit()
        return res

    def action_approve_slot_audit(self):
        """Aprobar la auditoría de un cuadre que ya pasó a Contabilidad o está cerrado (carga de días anteriores)."""
        if not self.env.user.has_group('ttg_casino.group_casino_audit'):
            raise UserError(_('Solo el Auditor puede aprobar la auditoría de contadores.'))
        for record in self:
            if not record.slot_meter_ids:
                raise UserError(_('Importe el archivo de contadores antes de aprobar la auditoría.'))
        self._check_slot_audit()
        self._approve_slot_audit()
        return True

    def action_draft(self):
        res = super().action_draft()
        approved = self.filtered('audit_approved')
        if approved:
            approved.with_context(casino_audit_unlock=True).write({
                'audit_approved': False, 'audit_approved_date': False, 'audit_approved_user_id': False})
            for record in approved:
                record.message_post(body=_('El cuadre volvió a Borrador: la auditoría de contadores debe aprobarse de nuevo.'))
        return res

    def action_print_slot_audit(self):
        self.ensure_one()
        return self.env.ref('ttg_casino.action_report_slot_audit').report_action(self)
