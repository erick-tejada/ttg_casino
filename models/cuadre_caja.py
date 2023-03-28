from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class CuadreDeCaja(models.Model):
    _name = 'casino.cuadre'
    _description = "Cuadre de Caja"
    _order = 'date desc'
    _rec_name = 'date'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_currency_usd_id(self):
        return self.env['res.currency'].search([('name','=','USD')]).id
    
    def _default_casino_tasa_usd(self):
        casino_tasa_usd = self.env.company.casino_tasa_usd
        return casino_tasa_usd

    
    @api.constrains('company_id', 'date')
    def _date_company_id(self):
        for record in self:
            cant_cuadres = self.env['casino.cuadre'].search_count([('company_id','=',record.company_id.id), ('date','=',record.date)])
            if cant_cuadres > 1:
                raise ValidationError('FECHA REPETIDA: Existe otro cuadre para la misma fecha!')

    date = fields.Date('Fecha', required=True, default=lambda self: fields.Date.context_today(self) - relativedelta(days=1), states={'done': [('readonly', True)]}, copy=False, index=True, tracking=3)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True)
    currency_usd_id = fields.Many2one('res.currency', string='Moneda USD', default=_default_currency_usd_id)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('audit', 'Auditoría'),
        ('accounting', 'Contabilidad'),
        ('done', 'Cerrado'),
        ], string='Estado', readonly=True, copy=False, index=True, tracking=3, default='draft')

    # MAQUINAS
    # ----------------------------------------------------------------------------------------------------------------
    bill_drop_ids = fields.One2many('casino.bill.drop', 'cuadre_id', 'Detalle Bill Drop')
    bill_drop_total = fields.Monetary('Total Bill Drop', compute='_compute_bill_drop', store=True) # Ingreso
    
    tarjetas_cashout = fields.Monetary('Tarjetas Cashout', states={'done': [('readonly', True)]}) # (Pagos) Egreso
    
    devolucion_ids = fields.One2many('casino.devolucion', 'cuadre_id', 'Detalle Devoluciones')
    devolucion_total = fields.Monetary('Total Devoluciones', compute='_compute_devoluciones', store=True) # Egreso
    
    marca_maquina_ids = fields.One2many('casino.marca.maquina', 'cuadre_id', 'Detalle Marcas Maquina')
    marca_maquina_total = fields.Monetary('Total Marcas Maquina', compute='_compute_marcas_maquina', store=True) # Ingreso
    
    recarga_tarjeta = fields.Monetary('Recarga de Tarjeta', states={'done': [('readonly', True)]}) # Ingreso
    
    otros_pagos_ids = fields.One2many('casino.otros.pagos', 'cuadre_id', 'Otros Pagos')
    otros_pagos_total = fields.Monetary('Total Otros Pagos', compute='_compute_otros_pagos', store=True) # Egreso

    # CUADRE
    ingreso_maquina = fields.Monetary('Ingreso Efectivo - Maquina', compute='_compute_cuadre_maquina', store=True)
    egreso_maquina = fields.Monetary('Pagos de Caja - Maquina', compute='_compute_cuadre_maquina', store=True)
    total_maquina = fields.Monetary('Total - Maquina', compute='_compute_cuadre_maquina', store=True)
    deposito_maquinas = fields.Monetary('Deposito Maquinas', compute='_compute_cuadre_maquina', store=True)

    # MESAS
    # ----------------------------------------------------------------------------------------------------------------
    apuestas_mesas = fields.Monetary('Apuestas en Mesas', states={'done': [('readonly', True)]}) # Ingresos
    pago_apuestas_mesas = fields.Monetary('Pago Apuestas', states={'done': [('readonly', True)]}) # Egreso

    apuestas_mesas_usd = fields.Monetary('Apuestas en Mesas USD', currency_field='currency_usd_id', states={'done': [('readonly', True)]}) # Ingresos
    pago_apuestas_mesas_usd = fields.Monetary('Pago Apuestas USD', currency_field='currency_usd_id', states={'done': [('readonly', True)]}) # Egreso
    
    marca_mesa_ids = fields.One2many('casino.marca.mesa', 'cuadre_id', 'Detalle Marcas Mesas')
    marca_mesa_total = fields.Monetary('Total Marcas Mesas', compute='_compute_marcas_mesas', store=True) # Ingreso

    # CUADRE
    total_dop_mesa = fields.Monetary('Ganancia/Perdida DOP - Mesa', compute='_compute_cuadre_mesa', store=True)
    total_usd_mesa = fields.Monetary('Ganancia/Perdida USD - Mesa', currency_field='currency_usd_id', compute='_compute_cuadre_mesa', store=True)

    # DIVISAS
    # ----------------------------------------------------------------------------------------------------------------
    casino_tasa_usd = fields.Float('Tasa USD', default=_default_casino_tasa_usd, help='Tasa USD utilizada para el cambio de Divisas.')    
    cambio_dolares = fields.Monetary('Cambio Dolares', currency_field='currency_usd_id', states={'done': [('readonly', True)]}) # Ingresos
    dop_cambio_dolares = fields.Monetary('DOP Entregado', compute='_compute_dop_cambio_dolares', states={'done': [('readonly', True)]}, store=True) # Egresos
    
    # TERJETA DE CREDITO
    # ----------------------------------------------------------------------------------------------------------------
    cobro_tc_ids = fields.One2many('casino.cobro.tc', 'cuadre_id', 'Detalle Cobros TC')
    cobro_tc_total = fields.Monetary('Total Cobro Tarjeta Crédito', compute='_compute_tc', store=True) # Ingreso
    cobro_tc_comision_total = fields.Monetary('Total Comision TC', compute='_compute_tc', store=True) # Ingreso
    # Liquidacion
    cobro_tc_pagado_total = fields.Monetary('Monto a Reponer TC', compute='_compute_tc', store=True) # Egreso
    itbis_retenido_tc = fields.Monetary('Monto ITBIS Retenido TC', compute='_compute_tc', store=True) # Egreso
    gasto_comision_tc = fields.Monetary('Monto Gasto Comision TC', compute='_compute_tc', store=True) # Egreso
    
    # SOBRANTES Y FALTANTES
    # ----------------------------------------------------------------------------------------------------------------
    faltante_ids = fields.One2many('casino.faltante', 'cuadre_id', 'Detalle Faltantes')
    faltante_total = fields.Monetary('Total Faltante', compute='_compute_faltante', store=True)
    sobrante_ids = fields.One2many('casino.sobrante', 'cuadre_id', 'Detalle Sobrantes')
    sobrante_total = fields.Monetary('Total Sobrante', compute='_compute_sobrante', store=True)

    @api.depends('bill_drop_ids', 'bill_drop_ids.amount_total')
    def _compute_bill_drop(self):
        for record in self:
            total = 0
            for line in record.bill_drop_ids:
                total += line.amount_total
            record.bill_drop_total = total
    
    def open_bill_drop(self):
        bill_drop_ids = self.mapped('bill_drop_ids')
        if self.state != 'done':
            action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_bill_drop")
        else:
            action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_bill_drop_readonly")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action
    
    @api.depends('devolucion_ids', 'devolucion_ids.amount')
    def _compute_devoluciones(self):
        for record in self:
            total = 0
            for line in record.devolucion_ids:
                total += line.amount
            record.devolucion_total = total
    
    def open_devoluciones(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_devolucion")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action
    
    @api.depends('marca_maquina_ids', 'marca_maquina_ids.amount')
    def _compute_marcas_maquina(self):
        for record in self:
            total = 0
            for line in record.marca_maquina_ids:
                total += line.amount
            record.marca_maquina_total = total
    
    def open_marca_maquinas(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_marca_maquina")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action
    
    @api.depends('otros_pagos_ids', 'otros_pagos_ids.amount')
    def _compute_otros_pagos(self):
        for record in self:
            total = 0
            for line in record.otros_pagos_ids:
                total += line.amount
            record.otros_pagos_total = total
    
    def open_otros_pagos(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_otros_pagos")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action
    
    @api.depends('marca_mesa_ids', 'marca_mesa_ids.amount')
    def _compute_marcas_mesas(self):
        for record in self:
            total = 0
            for line in record.marca_mesa_ids:
                total += line.amount
            record.marca_mesa_total = total
    
    def open_marca_mesas(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_marca_mesa")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action

    @api.depends('casino_tasa_usd', 'cambio_dolares')
    def _compute_dop_cambio_dolares(self):
        for record in self:
            record.dop_cambio_dolares = record.casino_tasa_usd * record.cambio_dolares
    
    def action_refresh_tasa_usd(self):
        self.casino_tasa_usd = self.env.company.casino_tasa_usd

    @api.depends('cobro_tc_ids', 'cobro_tc_ids.amount', 'cobro_tc_ids.amount_fee')
    def _compute_tc(self):
        for record in self:
            tc_itbis_percent = record.company_id.tc_itbis_percent
            tc_comision_percent = record.company_id.tc_comision_percent

            if (not tc_itbis_percent or not tc_comision_percent):
                raise ValidationError('COBROS TC NO CONFIGURADOS: Los Cobros con Tarjeta de Crédito no estan configurados.')

            total = 0
            total_fee = 0
            for line in record.cobro_tc_ids:
                total += line.amount
                total_fee += line.amount_fee
            record.cobro_tc_total = total
            record.cobro_tc_comision_total = total_fee
            record.cobro_tc_pagado_total = total - total_fee

            record.itbis_retenido_tc = record.currency_id.round(total * tc_itbis_percent)
            record.gasto_comision_tc = record.currency_id.round(total * tc_comision_percent)
    
    def open_cobros_tc(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_cobro_tc")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action
    
    @api.depends('faltante_ids', 'faltante_ids.amount')
    def _compute_faltante(self):
        for record in self:
            total = 0
            for line in record.faltante_ids:
                total += line.amount
            record.faltante_total = total
    
    def open_faltante(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_faltante")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action
    
    @api.depends('sobrante_ids', 'sobrante_ids.amount')
    def _compute_sobrante(self):
        for record in self:
            total = 0
            for line in record.sobrante_ids:
                total += line.amount
            record.sobrante_total = total
    
    def open_sobrante(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_sobrante")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action
    
    @api.depends('bill_drop_total', 'tarjetas_cashout', 'devolucion_total', 'marca_maquina_total', 'recarga_tarjeta', 'otros_pagos_total', 'faltante_total', 'sobrante_total')
    def _compute_cuadre_maquina(self):
        for record in self:
            total_ingreso = record.bill_drop_total + record.marca_maquina_total + record.recarga_tarjeta
            total_pago = record.tarjetas_cashout + record.devolucion_total + record.otros_pagos_total
            record.write({
                'ingreso_maquina': total_ingreso,
                'egreso_maquina': total_pago,
                'total_maquina': total_ingreso - total_pago,
                'deposito_maquinas': total_ingreso - total_pago + record.sobrante_total - record.faltante_total,
            })
    
    @api.depends('apuestas_mesas', 'pago_apuestas_mesas', 'apuestas_mesas_usd', 'pago_apuestas_mesas_usd', 'marca_mesa_total')
    def _compute_cuadre_mesa(self):
        for record in self:
            total_dop = record.apuestas_mesas + record.marca_mesa_total - record.pago_apuestas_mesas
            total_usd = record.apuestas_mesas_usd - record.pago_apuestas_mesas_usd
            record.write({
                'total_dop_mesa': total_dop,
                'total_usd_mesa': total_usd,
            })

    @api.model
    def create(self, vals):
        cuadre = super(CuadreDeCaja, self).create(vals)
        if not cuadre.bill_drop_ids:
            maquina_ids = self.env['casino.maquina'].search([('company_id','=',cuadre.company_id.id)])
            for maquina in maquina_ids:
                self.env['casino.bill.drop'].create({
                    'cuadre_id': cuadre.id,
                    'maquina_id': maquina.id,
                })
        return cuadre

    def unlink(self):
        if any(cuadre.state != 'draft' for cuadre in self):
            raise ValidationError('CUADRE NO ESTA EN BORRADOR: No puede borrar un Cuadre si no está en borrador.')
        
        res = super(CuadreDeCaja, self).unlink()
        return res