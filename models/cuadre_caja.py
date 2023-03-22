from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class CuadreDeCaja(models.Model):
    _name = 'casino.cuadre'
    _description = "Cuadre de Caja"
    _order = 'date'
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

    date = fields.Date('Fecha', required=True, default=lambda self: fields.Date.context_today(self), states={'done': [('readonly', True)]}, copy=False, index=True, tracking=3)
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

    # MESAS
    # ----------------------------------------------------------------------------------------------------------------
    apuestas_mesas = fields.Monetary('Apuestas en Mesas', states={'done': [('readonly', True)]}) # Ingresos
    pago_apuestas_mesas = fields.Monetary('Pago Apuestas', states={'done': [('readonly', True)]}) # Egreso

    apuestas_mesas_usd = fields.Monetary('Apuestas en Mesas USD', currency_field='currency_usd_id', states={'done': [('readonly', True)]}) # Ingresos
    pago_apuestas_mesas_usd = fields.Monetary('Pago Apuestas USD', currency_field='currency_usd_id', states={'done': [('readonly', True)]}) # Egreso
    
    marca_mesa_ids = fields.One2many('casino.marca.mesa', 'cuadre_id', 'Detalle Marcas Mesas')
    marca_mesa_total = fields.Monetary('Total Marcas Mesas', compute='_compute_marcas_mesas', store=True) # Ingreso

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
    cobro_tc_pagado_total = fields.Monetary('Total Efectivo Pagado por TC', compute='_compute_tc', store=True) # Egreso
    

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
    
    @api.depends('marca_maquina_ids', 'marca_maquina_ids.amount')
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
            total = 0
            total_fee = 0
            for line in record.cobro_tc_ids:
                total += line.amount
                total_fee += line.amount_fee
            record.cobro_tc_total = total
            record.cobro_tc_comision_total = total_fee
            record.cobro_tc_pagado_total = total - total_fee
    
    def open_cobros_tc(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_cobro_tc")
        action['domain'] = [('cuadre_id', '=', self.id)]
        context = {
            'default_cuadre_id': self.id,
        }
        action['context'] = context
        return action

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