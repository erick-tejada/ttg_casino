from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_is_casino_client = fields.Boolean('Es Cliente Casino', help='Indica que es un cliente del Casino')
    casino_categ = fields.Selection(
        [('Bronce', 'Bronce'), ('Plata', 'Plata'), ('Oro', 'Oro')],
        'Categoría Cliente Casino', copy=False, default='Bronce')

    x_is_lender = fields.Boolean('Es Prestamista')
    x_tier2_amount = fields.Float('Meta Monto Prestado para Nivel 2', help='Es el monto mínimo prestado para cambiar el porciento pagado de comisión al Porciento Comisión Nivel 2.')
    x_tier1_percent = fields.Float('Porciento Comision Nivel 1', help='Es el Porcentaje de comisión a pagar al prestamista si las ganancias son menores o iguales al Monto de Comisión Nivel 1.')
    x_tier2_percent = fields.Float('Porciento Comision Nivel 2', help='Es el Porcentaje de comisión a pagar al prestamista si las ganancias son mayores al Monto de Comisión .')
    
    x_deposit_ids = fields.One2many('casino.lender.deposit', 'partner_id', string='Depósitos')
    x_amount_available = fields.Monetary('Monto Disponible para Prestar', compute='_compute_x_amount_available')

    x_marca_maquina_ids = fields.One2many('casino.marca.maquina', 'lender_partner_id', string='Marcas Maquinas')
    x_marca_mesa_ids = fields.One2many('casino.marca.mesa', 'lender_partner_id', string='Marcas Mesas')

    def compute_balance_upto_date(self, date=False, day_only=False):
        '''
            Balance a de depositos y marcas a la fecha.
        '''
        # Total de Depositos
        sql_query = '''
                    SELECT SUM(d.amount)
                    FROM casino_lender_deposit d
                    WHERE d.partner_id = %s AND d.amount >= 0
                '''
        if date and not day_only:
            sql_query = sql_query + " AND d.date <= %s"
        elif date and day_only:
            sql_query = sql_query + " AND d.date = %s"

        if date:
            self.env.cr.execute(sql_query, (self.id, fields.Date.to_string(date).replace('-', '')))
        else:
            self.env.cr.execute(sql_query, (self.id,))
        total_depositos = self.env.cr.dictfetchall()[0].get('sum', 0.0)
        total_depositos = total_depositos if total_depositos else 0.0
        
        # Total de Retiros
        sql_query = '''
                    SELECT SUM(d.amount)
                    FROM casino_lender_deposit d
                    WHERE d.partner_id = %s AND d.amount < 0
                '''
        if date and not day_only:
            sql_query = sql_query + " AND d.date <= %s"
        elif date and day_only:
            sql_query = sql_query + " AND d.date = %s"

        if date:
            self.env.cr.execute(sql_query, (self.id, fields.Date.to_string(date).replace('-', '')))
        else:
            self.env.cr.execute(sql_query, (self.id,))
        total_retiros = self.env.cr.dictfetchall()[0].get('sum', 0.0)
        total_retiros = total_retiros if total_retiros else 0.0

        # Total de Marcas Maquinas
        sql_query = '''
                    SELECT SUM(m.amount)
                    FROM casino_marca_maquina m
                    WHERE m.lender_partner_id = %s
                '''
        if date and not day_only:
            sql_query = sql_query + " AND m.date <= %s"
        elif date and day_only:
            sql_query = sql_query + " AND m.date = %s"

        if date:
            self.env.cr.execute(sql_query, (self.id, fields.Date.to_string(date).replace('-', '')))
        else:
            self.env.cr.execute(sql_query, (self.id,))
        total_marcas_maquina = self.env.cr.dictfetchall()[0].get('sum', 0.0)
        total_marcas_maquina = total_marcas_maquina if total_marcas_maquina else 0.0

        # Total de Marcas Mesas
        sql_query = '''
                    SELECT SUM(m.amount)
                    FROM casino_marca_mesa m
                    WHERE m.lender_partner_id = %s
                '''
        if date and not day_only:
            sql_query = sql_query + " AND m.date <= %s"
        elif date and day_only:
            sql_query = sql_query + " AND m.date = %s"

        if date:
            self.env.cr.execute(sql_query, (self.id, fields.Date.to_string(date).replace('-', '')))
        else:
            self.env.cr.execute(sql_query, (self.id,))
        total_marcas_mesa = self.env.cr.dictfetchall()[0].get('sum', 0.0)
        total_marcas_mesa = total_marcas_mesa if total_marcas_mesa else 0.0

        return total_depositos, total_retiros, total_marcas_maquina, total_marcas_mesa


    @api.depends('x_deposit_ids', 'x_deposit_ids.amount', 'x_marca_maquina_ids', 'x_marca_maquina_ids.amount', 'x_marca_mesa_ids', 'x_marca_mesa_ids.amount')
    def _compute_x_amount_available(self):
        for record in self:

            if record.id and record.x_is_lender:

                total_depositos, total_retiros, total_marcas_maquina, total_marcas_mesa = record.compute_balance_upto_date()

                record.x_amount_available = total_depositos + total_retiros - total_marcas_maquina - total_marcas_mesa
            else:
                record.x_amount_available = 0
    
    def open_lender_deposits(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_lender_deposit")
        action['domain'] = [('partner_id', '=', self.id)]
        context = {
            'default_partner_id': self.id,
        }
        action['context'] = context
        return action