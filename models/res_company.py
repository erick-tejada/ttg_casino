
from odoo import fields, models, api


class ResComapany(models.Model):
    _inherit = 'res.company'

    casino_refresh_future = fields.Boolean('Refrescar Balances Futuros', default=True, help='Si está activo, al Cerrar un Cuadre, si existen cuadres futuros, se actualizarán los balances automáticamente.')
    casino_tasa_usd = fields.Float('Tasa USD Caja', default=55.0, help='Tasa USD utilizada para el cambio de Divisas en el Módulo de Ingresos.')

    # Comisiones de Tarjeta de Credito
    tc_itbis_percent = fields.Float('% Retencion ITBIS', default=0.02, help='%% de ITBIS Retenido en los cobros de Tarjeta de Crédito.')
    tc_itbis_account_id = fields.Many2one('account.account', 'Cuenta de Retencion ITBIS', help='Cuenta donde se registrará el ITBIS Retenido en los cobros de Tarjeta de Crédito.')
    tc_comision_percent = fields.Float('% Gasto de Comision', default=0.0345, help='%% de Comisión Retenida en los cobros de Tarjeta de Crédito.')
    tc_comision_account_id = fields.Many2one('account.account', 'Cuenta de Gasto de Comisión', help='Cuenta donde se registrará la Comisión Retenida en los cobros de Tarjeta de Crédito.')
    tc_partner_id = fields.Many2one('res.partner', 'Proveedor de Tarjeta de Credito', help='Proveedor de Tarjeta de Crédito utilizado para los cobros de Tarjeta de Crédito.')

    # Fondos
    dop_boveda_fondo = fields.Float('Fondo Boveda DOP', default=2000000, help='Fondo en DOP a mantener en la Bóveda de Pesos.')
    dop_boveda_account_id = fields.Many2one('account.account', 'Cuenta de Boveda DOP', help='Cuenta con valor en Bóveda de Pesos.')
    usd_boveda_fondo = fields.Float('Fondo Boveda USD', default=10000, help='Fondo en USD a mantener en la Bóveda de Dólares.')
    usd_boveda_account_id = fields.Many2one('account.account', 'Cuenta de Boveda USD', help='Cuenta con valor en Bóveda de Dólares.')

    # Asiento Contable
    cierre_journal_id = fields.Many2one('account.journal', 'Diario de Ingresos', help='Diario con el cual se asentarán los ingresos diarios.')
    caja_maquina_account_id = fields.Many2one('account.account', 'Cuenta de Caja Máquinas DOP', help='Cuenta de Caja Máquinas DOP.')
    caja_mesa_dop_account_id = fields.Many2one('account.account', 'Cuenta de Caja Mesa DOP', help='Cuenta de Caja Mesa DOP.')
    caja_mesa_usd_account_id = fields.Many2one('account.account', 'Cuenta de Caja Mesa USD', help='Cuenta de Caja Mesa USD.')

    # Bancos (Depositos)
    banco_dop_journal_id = fields.Many2one('account.journal', 'Diario de Banco DOP', help='Diario de Banco DOP.')
    banco_usd_journal_id = fields.Many2one('account.journal', 'Diario de Banco USD', help='Diario de Banco USD.')

    # MAQUINAS
    # ----------------------------------------------------------------------------------------------------------------
    # Ingreso
    maquina_ingreso_account_id = fields.Many2one('account.account', 'Cuenta de Ingreso por Máquinas', help='Cuenta de Ingreso por Máquinas.')
    maquina_ingreso_recarga_tarjetas_account_id = fields.Many2one('account.account', 'Cuenta de Ingreso por Recarga de Tarjetas', help='Cuenta de Ingreso por Recarga de Tarjetas.')
    maquina_ingreso_marcas_account_id = fields.Many2one('account.account', 'Cuenta de Ingreso por Marcas Maquina', help='Cuenta de Ingreso por Marcas de Máquinas.')
    maquina_ingreso_sobrante_account_id = fields.Many2one('account.account', 'Cuenta de Sobrante en Caja', help='Cuenta de Ingreso por Sobrante en Caja.')
    # Pago
    maquina_tarjeta_cashout_account_id = fields.Many2one('account.account', 'Cuenta de Pago por Tarjeta Cashout', help='Cuenta de Pago por Tarjeta Cashout.')
    maquina_devolucion_account_id = fields.Many2one('account.account', 'Cuenta de Pago por Devoluciones', help='Cuenta de Pago por Devoluciones.')
    maquina_otros_pagos_account_id = fields.Many2one('account.account', 'Cuenta de Pago por Pago Manual', help='Cuenta de Pago por Otros Pagos.')
    maquina_gasto_faltante_account_id = fields.Many2one('account.account', 'Cuenta de Faltante en Caja', help='Cuenta de Gasto por Faltante en Caja.')
    maquina_premios_account_id = fields.Many2one('account.account', 'Cuenta de Premios Maquina', help='Cuenta de Premios Maquina.')

    # MESAS
    # ----------------------------------------------------------------------------------------------------------------
    # DOP
    # Ingreso
    mesa_ingreso_account_id = fields.Many2one('account.account', 'Cuenta de Ingreso por Apuestas Mesas DOP', help='Cuenta de Ingreso por Mesas.')
    mesa_ingreso_marcas_account_id = fields.Many2one('account.account', 'Cuenta de Ingreso por Marcas Mesa', help='Cuenta de Ingreso por Marcas de Mesas.')
    mesa_ingreso_comision_tc_account_id = fields.Many2one('account.account', 'Cuenta de Ingreso por Comision de TC', help='Cuenta de Ingreso por Comision de TC.')
    # Pago
    mesa_pagos_account_id = fields.Many2one('account.account', 'Cuenta de Pagos por Apuestas Mesas DOP', help='Cuenta de Pagos por Apuestas Mesas.')
    mesa_efectivo_tc_account_id = fields.Many2one('account.account', 'Cuenta de Efectivo de TC', help='Cuenta de Efectivo de TC.')
    mesa_premios_account_id = fields.Many2one('account.account', 'Cuenta de Premios Mesa', help='Cuenta de Premios Mesa.')

    # USD
    mesa_ingreso_usd_account_id = fields.Many2one('account.account', 'Cuenta de Ingreso por Apuestas Mesas USD', help='Cuenta de Ingreso por Mesas USD.')
    mesa_pagos_usd_account_id = fields.Many2one('account.account', 'Cuenta de Pagos por Apuestas Mesas USD', help='Cuenta de Pagos por Apuestas Mesas USD.')