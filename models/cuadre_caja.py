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
    ingreso_maquina = fields.Monetary('Ingreso Efectivo de Maquina', compute='_compute_cuadre_maquina', store=True)
    egreso_maquina = fields.Monetary('Pagos de Maquina', compute='_compute_cuadre_maquina', store=True)
    total_maquina = fields.Monetary('Ganancia/Perdida Maquina', compute='_compute_cuadre_maquina', store=True)
    resultado_caja_maquina = fields.Monetary('Resultado Caja Maquina', compute='_compute_cuadre_maquina', store=True)
    reposicion_caja_maquina = fields.Monetary('Reposicion a Caja Maquinas', compute='_compute_cuadre_maquina', store=True)

    # MESAS
    # ----------------------------------------------------------------------------------------------------------------
    apuestas_mesas = fields.Monetary('Apuestas en Mesas', states={'done': [('readonly', True)]}) # Ingresos
    pago_apuestas_mesas = fields.Monetary('Pago Apuestas', states={'done': [('readonly', True)]}) # Egreso

    apuestas_mesas_usd = fields.Monetary('Apuestas en Mesas USD', currency_field='currency_usd_id', states={'done': [('readonly', True)]}) # Ingresos
    pago_apuestas_mesas_usd = fields.Monetary('Pago Apuestas USD', currency_field='currency_usd_id', states={'done': [('readonly', True)]}) # Egreso
    
    marca_mesa_ids = fields.One2many('casino.marca.mesa', 'cuadre_id', 'Detalle Marcas Mesas')
    marca_mesa_total = fields.Monetary('Total Marcas Mesas', compute='_compute_marcas_mesas', store=True) # Ingreso

    # CUADRE
    total_dop_mesa = fields.Monetary('Ganancia/Perdida DOP de Mesa', compute='_compute_cuadre_mesa', store=True)
    total_usd_mesa = fields.Monetary('Ganancia/Perdida USD de Mesa', currency_field='currency_usd_id', compute='_compute_cuadre_mesa', store=True)
    resultado_caja_mesa = fields.Monetary('Resultado Caja Mesa', compute='_compute_cuadre_mesa', store=True)
    reposicion_caja_mesa = fields.Monetary('Reposicion a Caja Mesa', compute='_compute_cuadre_mesa', store=True)
    resultado_usd_caja_mesa = fields.Monetary('Resultado USD Caja Mesa', currency_field='currency_usd_id', compute='_compute_cuadre_mesa', store=True)
    reposicion_usd_caja_mesa = fields.Monetary('Reposicion USD a Caja Mesa', currency_field='currency_usd_id', compute='_compute_cuadre_mesa', store=True)

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

    # FONDOS
    # ----------------------------------------------------------------------------------------------------------------
    # DOP
    dop_boveda_fondo = fields.Monetary('Fondo Boveda DOP', compute='_compute_fondos', store=True)
    dop_boveda_fondo_diponible = fields.Monetary('Fondo Disponible Boveda DOP', compute='_compute_fondos', store=True)
    dop_boveda_account_id = fields.Many2one('account.account', 'Cuenta de Boveda DOP', compute='_compute_fondos', store=True)
    # USD
    usd_boveda_fondo = fields.Monetary('Fondo Boveda USD', currency_field='currency_usd_id', compute='_compute_fondos', store=True, help='Fondo en USD a mantener en la Bóveda de Dólares.')
    usd_boveda_fondo_diponible = fields.Monetary('Fondo Disponible Boveda USD', currency_field='currency_usd_id', compute='_compute_fondos', store=True)
    usd_boveda_account_id = fields.Many2one('account.account', 'Cuenta de Boveda USD', compute='_compute_fondos', store=True, help='Cuenta con valor en Bóveda de Dólares.')

    # DEPOSITOS
    # ----------------------------------------------------------------------------------------------------------------
    # DOP
    dop_boveda_deposito = fields.Monetary('Deposito a Fondo Boveda DOP', compute='_compute_depositos', store=True)
    dop_boveda_total_despues_cierre = fields.Monetary('Total en Fondo Boveda DOP', compute='_compute_depositos', store=True)
    dop_boveda_a_depositar_banco = fields.Monetary('A Depositar al Banco DOP', compute='_compute_depositos', store=True)
    dop_boveda_fondo_al_cierre = fields.Monetary('Fondo en Boveda Despues del Cuadre DOP', compute='_compute_depositos', store=True)
    # USD
    usd_boveda_deposito = fields.Monetary('Deposito a Fondo Boveda USD', currency_field='currency_usd_id', compute='_compute_depositos', store=True)
    usd_boveda_total_despues_cierre = fields.Monetary('Total en Fondo Boveda USD', currency_field='currency_usd_id', compute='_compute_depositos', store=True)
    usd_boveda_a_depositar_banco = fields.Monetary('A Depositar al Banco USD', currency_field='currency_usd_id', compute='_compute_depositos', store=True)
    usd_boveda_fondo_al_cierre = fields.Monetary('Fondo en Boveda Despues del Cuadre USD', currency_field='currency_usd_id', compute='_compute_depositos', store=True)

    # ASIENTOS
    # ----------------------------------------------------------------------------------------------------------------
    cajas_move_id = fields.Many2one('account.move', 'Asiento de Operaciones de Caja')
    bovedas_move_id = fields.Many2one('account.move', 'Asiento de Transferencias/Reposicion Bovedas')
    depositos_move_id = fields.Many2one('account.move', 'Asiento de Depositos a Bancos')

    def action_draft(self):
        self._delete_moves()
        self.state = 'draft'

    def action_audit(self):
        next_state = 'audit'
        self.state = next_state
        self._redirect_if_needed(next_state)

    def action_accounting(self):
        next_state = 'accounting'
        self.state = next_state
        self._redirect_if_needed(next_state)

    def action_done(self):
        # Clear Moves
        self._delete_moves()

        # Create Moves
        self._create_moves()
        # TODO REMOVE COMMENT TO CHANGE STATE PROPERLY
        #self.state = 'done'

    def _delete_moves(self):
        if self.cajas_move_id:
            self.cajas_move_id.button_cancel()
            self.cajas_move_id.unlink()
            self.cajas_move_id = False
        if self.bovedas_move_id:
            self.bovedas_move_id.button_cancel()
            self.bovedas_move_id.unlink()
            self.bovedas_move_id = False
        if self.depositos_move_id:
            self.depositos_move_id.button_cancel()
            self.depositos_move_id.unlink()
            self.depositos_move_id = False

    def create_aml_dict(self, list_of_aml_vals, account_debit, account_credit, amount_dbcr, invert_dbcr, description, amount_currency=0.0, foreign_currency=False, credit_currency_description=''):
            '''
            account_debit: account used for debit (if not inverted)
            account_credit: account used for credit (if not inverted)
            amount_dbcr: amount for debit/credit
            invert_dbcr: invert debit/credit accounts
            description: name/description of the move line
            amount_currency: amount in foreign currency (if needed)
            foreign_currency: foreign currency (if needed)
            '''
            if amount_dbcr:
                db_account_id = account_debit if not invert_dbcr else account_credit
                cr_account_id = account_credit if not invert_dbcr else account_debit
                foreign_currency = self.env.company.currency_id if not foreign_currency else foreign_currency

                # Debit
                debit_aml = {
                    'account_id': db_account_id.id,
                    'name': description,
                    'debit': amount_dbcr,
                    'credit': 0,
                    'amount_currency': amount_currency,
                    'currency_id': foreign_currency.id,
                }
                list_of_aml_vals.append(debit_aml)

                # Credit
                credit_aml = {
                    'account_id': cr_account_id.id,
                    'name': credit_currency_description if amount_currency and credit_currency_description else description,
                    'debit': 0,
                    'credit': amount_dbcr,
                    'amount_currency': -1 * amount_currency if amount_currency else 0.0,
                    'currency_id': foreign_currency.id,
                }
                list_of_aml_vals.append(credit_aml)
    
    def create_move(self, aml_list, name=''):
        # Move name
        ref = 'INGRESOS %s%02d%02d' % (self.date.year, self.date.month, self.date.day)
        if name:
            ref = ref + ' - ' + name

        # Create Move Lines
        tuple_list = []
        #aml_object = self.env['account.move.line']
        for aml_vals in aml_list:
            tuple_list.append(
                (0, 0, aml_vals)
            )

        # Create Move
        move_id = self.env['account.move'].create({
            'ref': ref,
            'date': self.date,
            'journal_id': self.company_id.cierre_journal_id.id,
            'line_ids': tuple_list
        })

        return move_id

    def _create_moves(self):
        
        # ASIENTO 1: OPERACIONES
        # ----------------------------------------------------------------------------------------------------------------
        list_of_aml_vals = []
        # ******** INGRESOS MAQUINAS ********
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.caja_maquina_account_id,
            self.company_id.maquina_ingreso_account_id,
            self.bill_drop_total,
            False,
            'MAQUINAS: Ingreso por Bill Drop',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.caja_maquina_account_id,
            self.company_id.maquina_ingreso_recarga_tarjetas_account_id,
            self.recarga_tarjeta,
            False,
            'MAQUINAS: Ingreso por Recarga de Tarjeta',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.caja_maquina_account_id,
            self.company_id.maquina_ingreso_marcas_account_id,
            self.marca_maquina_total,
            False,
            'MAQUINAS: Ingreso por Marcas',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.caja_maquina_account_id,
            self.company_id.maquina_ingreso_sobrante_account_id,
            self.sobrante_total,
            False,
            'MAQUINAS: Ingreso por Sobrante en Caja',
        )
        # ******** PAGOS MAQUINAS ********
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.maquina_tarjeta_cashout_account_id,
            self.company_id.caja_maquina_account_id,
            self.tarjetas_cashout,
            False,
            'MAQUINAS: Pagos por Tarjeta Cashout',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.maquina_devolucion_account_id,
            self.company_id.caja_maquina_account_id,
            self.devolucion_total,
            False,
            'MAQUINAS: Pagos por Devolución',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.maquina_otros_pagos_account_id,
            self.company_id.caja_maquina_account_id,
            self.otros_pagos_total,
            False,
            'MAQUINAS: Pagos por Otros Pagos',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.maquina_gasto_faltante_account_id,
            self.company_id.caja_maquina_account_id,
            self.faltante_total,
            False,
            'MAQUINAS: Pagos por Faltante en Caja',
        )
        # ******** INGRESOS MESAS DOP ********
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.caja_mesa_dop_account_id,
            self.company_id.mesa_ingreso_account_id,
            self.apuestas_mesas,
            False,
            'MESAS DOP: Ingreso por Apuestas en Mesa',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.caja_mesa_dop_account_id,
            self.company_id.mesa_ingreso_marcas_account_id,
            self.marca_mesa_total,
            False,
            'MESAS DOP: Ingreso por Marcas en Mesa',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.caja_mesa_dop_account_id,
            self.company_id.mesa_ingreso_comision_tc_account_id,
            self.cobro_tc_comision_total,
            False,
            'MESAS DOP: Ingreso por Comision de TC',
        )
        # ******** PAGOS MESAS DOP ********
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.mesa_pagos_account_id,
            self.company_id.caja_mesa_dop_account_id,
            self.pago_apuestas_mesas,
            False,
            'MESAS DOP: Pagos por Apuestas de Mesas',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.mesa_efectivo_tc_account_id,
            self.company_id.caja_mesa_dop_account_id,
            self.cobro_tc_total,
            False,
            'MESAS DOP: Pagos por Efectivo TC',
        )
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.caja_mesa_usd_account_id,
            self.company_id.caja_mesa_dop_account_id,
            self.dop_cambio_dolares,
            False,
            'MESAS USD: Ingreso por Cambio de Dólares',
            self.cambio_dolares,
            self.currency_usd_id,
            'MESAS DOP: Pago por Cambio de Dólares',
        )

        
        # ******** INGRESOS MESAS USD ********
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.caja_mesa_usd_account_id,
            self.company_id.mesa_ingreso_usd_account_id,
            self.currency_usd_id.round(self.apuestas_mesas_usd * self.casino_tasa_usd),
            False,
            'MESAS USD: Ingreso por Apuestas en Mesa',
            self.apuestas_mesas_usd,
            self.currency_usd_id
        )
        # ******** PAGOS MESAS USD ********
        self.create_aml_dict(
            list_of_aml_vals,
            self.company_id.mesa_pagos_usd_account_id,
            self.company_id.caja_mesa_usd_account_id,
            self.currency_usd_id.round(self.pago_apuestas_mesas_usd * self.casino_tasa_usd),
            False,
            'MESAS USD: Pagos por Apuestas en Mesa',
            self.pago_apuestas_mesas_usd,
            self.currency_usd_id
        )
        _logger.warning('------------------------------------')
        for l in list_of_aml_vals:
            _logger.warning(l)
        _logger.warning('------------------------------------')
        self.cajas_move_id = self.create_move(list_of_aml_vals, name='OPERACIONES DE CAJAS')
        self.cajas_move_id.action_post()

        # ASIENTO 2: TRANSFERENCIA A / REPOSICION DE BOVEDA
        # ----------------------------------------------------------------------------------------------------------------
        # ASIENTO 3: DEPOSITOS A BANCO
        # ----------------------------------------------------------------------------------------------------------------
    
    def _redirect_if_needed(self, next_state):
        ''''Redirects the user to the list view if the user
            does not have the role for the next state.'''
        
        if ((next_state == 'audit' and not self.env.user.has_group('ttg_casino.group_casino_audit')) or
            (next_state == 'accounting' and not self.env.user.has_group('ttg_casino.group_casino_accountant'))):
            return self.env["ir.actions.actions"]._for_xml_id("ttg_casino.action_cuadre")
    
    @api.depends('resultado_caja_mesa', 'resultado_caja_maquina', 'dop_boveda_fondo', 'dop_boveda_fondo_diponible', 'reposicion_caja_maquina', 'reposicion_caja_mesa', 
                 'usd_boveda_fondo', 'usd_boveda_fondo_diponible', 'resultado_usd_caja_mesa', 'reposicion_usd_caja_mesa')
    def _compute_depositos(self):
        for record in self:
            # DOP
            resultado_del_dia = record.resultado_caja_mesa + record.resultado_caja_maquina
            a_depositar_boveda = resultado_del_dia if resultado_del_dia > 0.0 else 0.0
            nuevo_balance_boveda = record.dop_boveda_fondo_diponible + a_depositar_boveda - record.reposicion_caja_maquina - record.reposicion_caja_mesa
            a_depositar_banco = nuevo_balance_boveda - record.dop_boveda_fondo if nuevo_balance_boveda > record.dop_boveda_fondo else 0.0
            dop_boveda_fondo_al_cierre = nuevo_balance_boveda - a_depositar_banco

            # USD
            a_depositar_boveda_usd = record.resultado_usd_caja_mesa if record.resultado_usd_caja_mesa > 0.0 else 0.0
            nuevo_balance_boveda_usd = record.usd_boveda_fondo_diponible + a_depositar_boveda_usd - record.reposicion_usd_caja_mesa
            a_depositar_banco_platino = nuevo_balance_boveda_usd - record.usd_boveda_fondo if nuevo_balance_boveda_usd > record.usd_boveda_fondo else 0.0
            usd_boveda_fondo_al_cierre = nuevo_balance_boveda_usd - a_depositar_banco_platino

            record.write({
                'dop_boveda_deposito': a_depositar_boveda,
                'dop_boveda_total_despues_cierre': nuevo_balance_boveda,
                'dop_boveda_a_depositar_banco': a_depositar_banco,
                'dop_boveda_fondo_al_cierre': dop_boveda_fondo_al_cierre,

                'usd_boveda_deposito': a_depositar_boveda_usd,
                'usd_boveda_total_despues_cierre': nuevo_balance_boveda_usd,
                'usd_boveda_a_depositar_banco': a_depositar_banco_platino,
                'usd_boveda_fondo_al_cierre': usd_boveda_fondo_al_cierre,

            })

    def _compute_balance_at_date(self, account_id, date, is_foreign_currency=False):
        if is_foreign_currency:
            sql_query = '''
                    SELECT SUM(aml.amount_currency)
                    FROM account_move_line aml
                    WHERE aml.account_id = %s AND aml.date < %s
                    '''
        else:
            sql_query = '''
                        SELECT SUM(aml.balance)
                        FROM account_move_line aml
                        WHERE aml.account_id = %s AND aml.date < %s
                        '''
        self.env.cr.execute(sql_query, (account_id.id, date))
        balance = self.env.cr.dictfetchall()[0].get('sum', 0.0)
        return balance if balance else 0.0

    
    @api.depends('date')
    def _compute_fondos(self):
        for record in self:
            dop_boveda_fondo = 0.0
            dop_boveda_fondo_diponible = 0.0
            dop_boveda_account_id = False
            usd_boveda_fondo = 0.0
            usd_boveda_fondo_diponible = 0.0
            usd_boveda_account_id = False

            if record.date:
                # DOP
                dop_boveda_fondo = record.company_id.dop_boveda_fondo
                dop_boveda_account_id = record.company_id.dop_boveda_account_id
                if dop_boveda_account_id:
                    dop_boveda_fondo_diponible = record._compute_balance_at_date(dop_boveda_account_id, record.date)
                
                # USD
                usd_boveda_fondo = record.company_id.usd_boveda_fondo
                usd_boveda_account_id = record.company_id.usd_boveda_account_id
                if usd_boveda_account_id:
                    usd_boveda_fondo_diponible = record._compute_balance_at_date(usd_boveda_account_id, record.date, True)
            
            record.write({
                'dop_boveda_fondo': dop_boveda_fondo,
                'dop_boveda_fondo_diponible': dop_boveda_fondo_diponible,
                'dop_boveda_account_id': dop_boveda_account_id,
                'usd_boveda_fondo': usd_boveda_fondo,
                'usd_boveda_fondo_diponible': usd_boveda_fondo_diponible,
                'usd_boveda_account_id': usd_boveda_account_id,
            })
    
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
            total_maquina = total_ingreso - total_pago
            resultado_caja_maquina = total_maquina + record.sobrante_total - record.faltante_total
            record.write({
                'ingreso_maquina': total_ingreso,
                'egreso_maquina': total_pago,
                'total_maquina': total_maquina,
                'resultado_caja_maquina': resultado_caja_maquina,
                'reposicion_caja_maquina': resultado_caja_maquina * -1 if resultado_caja_maquina < 0.0 else 0.0,
            })
    
    @api.depends('apuestas_mesas', 'pago_apuestas_mesas', 'apuestas_mesas_usd', 'pago_apuestas_mesas_usd', 'marca_mesa_total', 'cobro_tc_comision_total', 'cobro_tc_total', 'dop_cambio_dolares', 'cambio_dolares')
    def _compute_cuadre_mesa(self):
        for record in self:
            total_dop = record.apuestas_mesas + record.marca_mesa_total - record.pago_apuestas_mesas
            total_usd = record.apuestas_mesas_usd - record.pago_apuestas_mesas_usd
            resultado_caja_mesa = total_dop + record.cobro_tc_comision_total - record.cobro_tc_total - record.dop_cambio_dolares
            reposicion_caja_mesa = resultado_caja_mesa * -1 if resultado_caja_mesa < 0.0 else 0.0

            resultado_usd_caja_mesa = total_usd + record.cambio_dolares
            reposicion_usd_caja_mesa = resultado_usd_caja_mesa * -1 if resultado_usd_caja_mesa < 0.0 else 0.0
            record.write({
                'total_dop_mesa': total_dop,
                'total_usd_mesa': total_usd,
                'resultado_caja_mesa': resultado_caja_mesa,
                'reposicion_caja_mesa': reposicion_caja_mesa,
                'resultado_usd_caja_mesa': resultado_usd_caja_mesa,
                'reposicion_usd_caja_mesa': reposicion_usd_caja_mesa,
            })
    
    def _compute_all(self):
        for record in self:
            record._compute_fondos()
            record._compute_bill_drop()
            record._compute_devoluciones()
            record._compute_marcas_maquina()
            record._compute_otros_pagos()
            record._compute_marcas_mesas()
            record._compute_dop_cambio_dolares()
            record._compute_tc()
            record._compute_faltante()
            record._compute_sobrante()
            record._compute_cuadre_maquina()
            record._compute_cuadre_mesa()
            record._compute_depositos()

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