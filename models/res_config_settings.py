
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    casino_tasa_usd = fields.Float('Tasa USD Caja', related='company_id.casino_tasa_usd', readonly=False, help='Tasa USD utilizada para el cambio de Divisas en el Módulo de Ingresos.')

    # Comisiones de Tarjeta de Credito
    tc_itbis_percent = fields.Float(related='company_id.tc_itbis_percent', readonly=False)
    tc_itbis_account_id = fields.Many2one(related='company_id.tc_itbis_account_id', readonly=False)
    tc_comision_percent = fields.Float(related='company_id.tc_comision_percent', readonly=False)
    tc_comision_account_id = fields.Many2one(related='company_id.tc_comision_account_id', readonly=False)
    
    # Fondos
    dop_boveda_fondo = fields.Float(related='company_id.dop_boveda_fondo', readonly=False, help='Fondo en DOP a mantener en la Bóveda de Pesos.')
    usd_boveda_fondo = fields.Float(related='company_id.usd_boveda_fondo', readonly=False, help='Fondo en USD a mantener en la Bóveda de Dólares.')
    dop_boveda_account_id = fields.Many2one(related='company_id.dop_boveda_account_id', readonly=False, help='Cuenta con valor en Bóveda de Pesos.')
    usd_boveda_account_id = fields.Many2one(related='company_id.usd_boveda_account_id', readonly=False, help='Cuenta con valor en Bóveda de Dólares.')

    # Asiento Contable
    cierre_journal_id = fields.Many2one(related='company_id.cierre_journal_id', readonly=False, help='Diario con el cual se asentarán los ingresos diarios.')
    caja_maquina_account_id = fields.Many2one(related='company_id.caja_maquina_account_id', readonly=False, help='Cuenta de Caja Máquinas DOP.')
    caja_mesa_dop_account_id = fields.Many2one(related='company_id.caja_mesa_dop_account_id', readonly=False, help='Cuenta de Caja Mesa DOP.')
    caja_mesa_usd_account_id = fields.Many2one(related='company_id.caja_mesa_usd_account_id', readonly=False, help='Cuenta de Caja Mesa USD.')

    # Bancos (Depositos)
    banco_dop_journal_id = fields.Many2one(related='company_id.banco_dop_journal_id', readonly=False, help='Diario de Banco DOP.')
    banco_usd_journal_id = fields.Many2one(related='company_id.banco_usd_journal_id', readonly=False, help='Diario de Banco USD.')

    # MAQUINAS
    # ----------------------------------------------------------------------------------------------------------------
    # Ingreso
    maquina_ingreso_account_id = fields.Many2one(related='company_id.maquina_ingreso_account_id', readonly=False, help='Cuenta de Ingreso por Máquinas.')
    maquina_ingreso_recarga_tarjetas_account_id = fields.Many2one(related='company_id.maquina_ingreso_recarga_tarjetas_account_id', readonly=False, help='Cuenta de Ingreso por Recarga de Tarjetas.')
    maquina_ingreso_marcas_account_id = fields.Many2one(related='company_id.maquina_ingreso_marcas_account_id', readonly=False, help='Cuenta de Ingreso por Marcas de Máquinas.')
    maquina_ingreso_sobrante_account_id = fields.Many2one(related='company_id.maquina_ingreso_sobrante_account_id', readonly=False, help='Cuenta de Ingreso por Sobrante en Caja.')
    # Pago
    maquina_tarjeta_cashout_account_id = fields.Many2one(related='company_id.maquina_tarjeta_cashout_account_id', readonly=False, help='Cuenta de Pago por Tarjeta Cashout.')
    maquina_devolucion_account_id = fields.Many2one(related='company_id.maquina_devolucion_account_id', readonly=False, help='Cuenta de Pago por Devoluciones.')
    maquina_otros_pagos_account_id = fields.Many2one(related='company_id.maquina_otros_pagos_account_id', readonly=False, help='Cuenta de Pago por Otros Pagos.')
    maquina_gasto_faltante_account_id = fields.Many2one(related='company_id.maquina_gasto_faltante_account_id', readonly=False, help='Cuenta de Gastp por Faltante en Caja.')
    maquina_premios_account_id = fields.Many2one(related='company_id.maquina_premios_account_id', readonly=False, help='Cuenta de Premios Maquina.')

    # MESAS
    # ----------------------------------------------------------------------------------------------------------------
    # DOP
    # Ingreso
    mesa_ingreso_account_id = fields.Many2one(related='company_id.mesa_ingreso_account_id', readonly=False, help='Cuenta de Ingreso por Mesas.')
    mesa_ingreso_marcas_account_id = fields.Many2one(related='company_id.mesa_ingreso_marcas_account_id', readonly=False, help='Cuenta de Ingreso por Marcas de Mesas.')
    mesa_ingreso_comision_tc_account_id = fields.Many2one(related='company_id.mesa_ingreso_comision_tc_account_id', readonly=False, help='Cuenta de Ingreso por Comision de TC.')
    # Pago
    mesa_pagos_account_id = fields.Many2one(related='company_id.mesa_pagos_account_id', readonly=False, help='Cuenta de Pagos por Apuestas Mesas.')
    mesa_efectivo_tc_account_id = fields.Many2one(related='company_id.mesa_efectivo_tc_account_id', readonly=False, help='Cuenta de Efectivo de TC.')
    mesa_premios_account_id = fields.Many2one(related='company_id.mesa_premios_account_id', readonly=False, help='Cuenta de Premios Mesa.')

    # USD
    mesa_ingreso_usd_account_id = fields.Many2one(related='company_id.mesa_ingreso_usd_account_id', readonly=False, help='Cuenta de Ingreso por Mesas USD.')
    mesa_pagos_usd_account_id = fields.Many2one(related='company_id.mesa_pagos_usd_account_id', readonly=False, help='Cuenta de Pagos por Apuestas Mesas USD.')