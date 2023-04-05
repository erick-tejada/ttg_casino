from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)


class MarcaMaquina(models.Model):
    _name = 'casino.marca.maquina'
    _description = "Marca Maquinas"
    _rec_name = 'partner_id'
    _order = 'cuadre_id,partner_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True)
    state = fields.Selection(related='cuadre_id.state', string='Estado')

    partner_id = fields.Many2one('res.partner', string="Cliente", required=True, domain="[('x_is_casino_client', '=', True)]")
    ref = fields.Char('Código Cliente', related='partner_id.ref', store=True, index=True)
    amount = fields.Monetary('Monto', required=True)
    lender_partner_id = fields.Many2one('res.partner', string="Prestamista", required=True, domain="[('x_is_lender', '=', True)]")
    note = fields.Char('Nota')

    def _verify_state(self):
        if self.state == 'done':
            raise ValidationError('CUADRE CERRADO: No puede crear/modificar una marca si el Cuadre al que pertenece esta Cerrado.')
    
    def _verify_amount(self):
        if self.amount > self.lender_partner_id.x_amount_available:
            raise ValidationError('MONTO MAYOR AL DISPONIBLE: %s actualmente solo dispone de %.2f.' % (self.lender_partner_id.name, self.lender_partner_id.x_amount_available))
    
    def unlink(self):
        if any(record.state == 'done' for record in self):
            raise ValidationError('CUADRE CERRADO: No puede borrar una Marca si el Cuadre está cerrado.')
        res = super(MarcaMaquina, self).unlink()
        return res

    @api.model
    def create(self, vals):
        marca = super(MarcaMaquina, self).create(vals)
        marca._verify_state()
        marca._verify_amount()
        return marca

    def write(self, vals):
        res = super(MarcaMaquina, self).write(vals)
        for marca in self:
            marca._verify_state()
        return res


class MarcaMesa(models.Model):
    _name = 'casino.marca.mesa'
    _description = "Marca Mesas"
    _rec_name = 'partner_id'
    _order = 'cuadre_id,partner_id'

    cuadre_id = fields.Many2one('casino.cuadre', string='Cuadre de Caja', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', related='cuadre_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='cuadre_id.currency_id', store=True)
    date = fields.Date('Fecha', related='cuadre_id.date', store=True)
    state = fields.Selection(related='cuadre_id.state', string='Estado', store=True)

    partner_id = fields.Many2one('res.partner', string="Cliente", required=True, domain="[('x_is_casino_client', '=', True)]")
    mesa_id = fields.Many2one('casino.mesa', string="Mesa", required=True)
    ref = fields.Char('Código Cliente', related='partner_id.ref', store=True, index=True)
    amount = fields.Monetary('Monto', required=True)
    lender_partner_id = fields.Many2one('res.partner', string="Prestamista", required=True, domain="[('x_is_lender', '=', True)]")
    note = fields.Char('Nota')

    def _verify_state(self):
        for record in self:
            if record.state == 'done':
                raise ValidationError('CUADRE CERRADO: No puede crear/modificar una marca si el Cuadre al que pertenece esta Cerrado.')
    
    def _verify_amount(self):
        if self.amount > self.lender_partner_id.x_amount_available:
            raise ValidationError('MONTO MAYOR AL DISPONIBLE: %s actualmente solo dispone de %.2f.' % (self.lender_partner_id.name, self.lender_partner_id.x_amount_available))

    def unlink(self):
        if any(record.state == 'done' for record in self):
            raise ValidationError('CUADRE CERRADO: No puede borrar una Marca si el Cuadre está cerrado.')
        res = super(MarcaMesa, self).unlink()
        return res
    
    @api.model
    def create(self, vals):
        marca = super(MarcaMesa, self).create(vals)
        marca._verify_state()
        marca._verify_amount()
        return marca

    def write(self, vals):
        res = super(MarcaMesa, self).write(vals)
        for marca in self:
            marca._verify_state()
        return res