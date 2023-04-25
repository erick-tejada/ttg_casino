from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import logging
_logger = logging.getLogger(__name__)

from datetime import date

class ComisionMarca(models.Model):
    _name = 'casino.comision.marca'
    _description = "Comision por Marcas"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    def _default_currency_usd_id(self):
        return self.env['res.currency'].search([('name','=','USD')]).id
    
    def _default_year(self):
        today = fields.Date.context_today(self)
        year = today.year 
        return year
    
    def _default_month(self):
        today = fields.Date.context_today(self)
        month = today.month
        return str(month)
    
    def _default_quincena(self):
        today = fields.Date.context_today(self)
        quicena = '1' if today.day > 15 else '2'
        return str(quicena)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Cerrado'),
        ], string='Estado', readonly=True, copy=False, index=True, tracking=3, default='draft')
    name = fields.Char(string='Nombre', required=True, copy=False, tracking=3, readonly=True, index=True, default=lambda self: 'Nuevo')
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True)
    month = fields.Selection([
        ('1', 'Enero'),
        ('2', 'Febrero'),
        ('3', 'Marzo'),
        ('4', 'Abril'),
        ('5', 'Mayo'),
        ('6', 'Junio'),
        ('7', 'Julio'),
        ('8', 'Agosto'),
        ('9', 'Septiembre'),
        ('10', 'Octubre'),
        ('11', 'Noviembre'),
        ('12', 'Diciembre'),
        ], string='Mes', required=True, states={'done': [('readonly', True)]}, copy=False, index=True, tracking=3, default=_default_month)
    month_period = fields.Selection([
        ('1', '1ra Quincena'),
        ('2', '2da Quincena'),
        ], string='Quincena', required=True, copy=False, index=True, tracking=3, default=_default_quincena)
    year = fields.Integer('Año', required=True, default=_default_year)
    lender_partner_id = fields.Many2one('res.partner', string="Prestamista", tracking=3, required=True, domain="[('x_is_lender', '=', True)]")
    note = fields.Text('Notas')

    amount = fields.Monetary('Monto a Pagar', tracking=3, readonly=True)
    line_ids = fields.One2many('casino.comision.marca.linea', 'comision_id', string='Detalle de Comisiones')

    @api.constrains('company_id', 'year', 'month', 'lender_partner_id')
    def _contrains_comision_marca(self):
        today = fields.Date.context_today(self)
        year = today.year 

        for record in self:
            if record.year < 2020 or record.year > year + 1:
                raise ValidationError('AÑO INVÁLIDO: Debe utilizar un año válido.')
            
            count = self.env['casino.comision.marca'].search_count([
                ('company_id','=',record.company_id.id), 
                ('year','=',record.year),
                ('month','=',record.month),
                ('month_period','=',record.month_period), 
                ('lender_partner_id','=',record.lender_partner_id.id)
            ])

            if count > 1:
                raise ValidationError('COMISIÓN DUPLICADA: No puede generar un reporte de Comisiones para el mismo prestamista dentro del mismo periodo.')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('casino.comision.marca') or 'Nuevo'
        result = super(ComisionMarca, self).create(vals)
        return result

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise ValidationError('COMISION CERRADA: No puede borrar una Comision de Marca cerrada.')
        super(ComisionMarca, self).unlink()

    def action_load_comisiones(self):
        record = self
        # Clear old data
        self.env['casino.comision.marca.linea'].search([('comision_id','=',record.id)]).unlink()
        record.amount = 0
        
        # TODO Verify all cuadre are done

        # Date range
        if record.month_period == '1':
            # Primera Quincena: from year-month-01 to < year-month-16
            date_start = '%s-%s-01' % (record.year, str(record.month).zfill(2))
            date_end = '%s-%s-16' % (record.year, str(int(record.month)).zfill(2))
        else:
            # Segunda Quincena: from year-month-16 to < (next_)year-next_month-01
            date_start = '%s-%s-16' % (record.year, str(record.month).zfill(2))
            if record.month == 12:
                date_end = '%s-%s-01' % (record.year + 1, str(1).zfill(2)) # next_year-01-01
            else:
                date_end = '%s-%s-01' % (record.year, str(int(record.month) + 1).zfill(2)) # same_year-next_month-01

        marcas_domain = [
            ('company_id','=',record.company_id.id),
            ('date','>=',date_start),
            ('date','<',date_end),
            ('lender_partner_id','=',record.lender_partner_id.id),
            #('state','=','done'),
        ]
        
        # MESAS
        marca_ids = self.env['casino.marca.mesa'].search(marcas_domain)

        totals_mesas_by_date = {}
        for marca in marca_ids:
            date_key = marca.date.strftime(DF)
            if date_key in totals_mesas_by_date:
                totals_mesas_by_date[date_key]['amount_mesas'] = totals_mesas_by_date[date_key]['amount_mesas'] + marca.amount
            else:
                totals_mesas_by_date[date_key] = {'amount_mesas': marca.amount, 'amount_maquinas': 0.0, 'retencion_maquina': 0}
        
        # MAQUINAS
        marca_ids = self.env['casino.marca.maquina'].search(marcas_domain)

        for marca in marca_ids:
            date_key = marca.date.strftime(DF)
            if date_key in totals_mesas_by_date:
                totals_mesas_by_date[date_key] = {
                    'amount_mesas': totals_mesas_by_date[date_key]['amount_mesas'],
                    'amount_maquinas': totals_mesas_by_date[date_key]['amount_maquinas'] + marca.amount,
                    'retencion_maquina': marca.cuadre_id.retencion_maquina,
                }
            else:
                totals_mesas_by_date[date_key] = {
                    'amount_mesas': 0.0, 
                    'amount_maquinas': marca.amount, 
                    'retencion_maquina': marca.cuadre_id.retencion_maquina
                }
        
        # Calculate Fee
        x_tier1_percent = record.lender_partner_id.x_tier1_percent
        x_tier2_percent = record.lender_partner_id.x_tier2_percent
        x_tier2_amount = record.lender_partner_id.x_tier2_amount

        total = 0
        for date, vals in totals_mesas_by_date.items():
            # MESAS
            mesas_percent_to_use = x_tier2_percent if (x_tier2_amount > 0) and (vals['amount_mesas'] > x_tier2_amount) else x_tier1_percent
            mesas_amount_fee = vals['amount_mesas'] * mesas_percent_to_use

            # MAQUINAS
            maquinas_percent_to_use = x_tier2_percent if (x_tier2_amount > 0) and (vals['amount_maquinas'] > x_tier2_amount) else x_tier1_percent
            maquinas_amount_fee = vals['amount_maquinas'] * (vals['retencion_maquina'] / 100) * maquinas_percent_to_use
            
            self.env['casino.comision.marca.linea'].create({
                'comision_id': record.id,
                'date': date,
                'amount_marcas': vals['amount_mesas'],
                'amount_fee': mesas_amount_fee,
                'amount_percent': mesas_percent_to_use,

                'amount_marcas_maquinas': vals['amount_maquinas'],
                'amount_fee_maquinas': maquinas_amount_fee,
                'retencion_maquina': vals['retencion_maquina'] / 100,
                'amount_percent_maquinas': maquinas_percent_to_use,
            })
            total += mesas_amount_fee + maquinas_amount_fee
        
        record.amount = total



class ComisionMarcaLinea(models.Model):
    _name = 'casino.comision.marca.linea'
    _description = "Linea de Comision por Marcas"
    _order = 'date desc'

    comision_id = fields.Many2one('casino.comision.marca', string='Reporte de Comision', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', string='Moneda', related='comision_id.currency_id', store=True)
    lender_partner_id = fields.Many2one('res.partner', string='Prestamista', related='comision_id.lender_partner_id', store=True)
    state = fields.Selection(related='comision_id.state', store=True)

    date = fields.Date('Fecha')
    amount_marcas = fields.Monetary('Monto Marcas Mesas')
    amount_fee = fields.Monetary('Monto Comision Mesas')
    amount_percent = fields.Float('Porciento de Comision Mesas')

    amount_marcas_maquinas = fields.Monetary('Monto Marcas Máquinas')
    amount_fee_maquinas = fields.Monetary('Monto Comision Máquinas')
    retencion_maquina = fields.Float('Retención Máquinas')
    amount_percent_maquinas = fields.Float('Porciento de Comision Máquinas')
