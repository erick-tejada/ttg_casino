# -*- coding: utf-8 -*-

{
    'name': 'TTG - Casino',
    'author': "Tejada Tech Group EIRL",
    'version': '15.0.2.4',
    'sequence': 100,
    'category': 'Accounting/Accounting',
    'description': """
        Agrega funcionalidades para tener mejor control operativo de los ingresos en Caja del Casino.""",
    'depends': ['account', 'hr'],
    'summary': 'Agrega funcionalidades para tener mejor control operativo de los ingresos en Caja del Casino.',
    'website': 'https://www.tejadatech.com',
    'data': [
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'data/maquinas_data.xml',
        'data/mesas_data.xml',
        'data/ir_sequence_data.xml',
        'data/errores_data.xml',
        'views/maquina_views.xml',
        'views/cuadre_views.xml',
        'views/bill_drop_views.xml',
        'views/devolucion_views.xml',
        'views/marca_maquina_views.xml',
        'views/otros_pagos_views.xml',
        'views/marca_mesa_views.xml',
        'views/res_partner_views.xml',
        'views/cobro_tc_views.xml',
        'views/faltante_views.xml',
        'views/sobrante_views.xml',
        'views/res_config_settings_views.xml',
        'views/comision_marca_views.xml',
        'views/lender_deposit_views.xml',
        'views/encargado_caja_views.xml',
        'views/mesas_views.xml',
        'views/apuesta_mesa_views.xml',
        'views/apuesta_mesa_usd_views.xml',
        'views/tipo_error_views.xml',
        'views/casino_views.xml',
        'report/comision_marca_templates.xml',
        'report/comision_marca_report.xml',
        'report/cuadre_caja_templates.xml',
        'report/cuadre_caja_report.xml',
        'report/detalle_bill_drop_templates.xml',
        'report/detalle_bill_drop_report.xml',
        'report/bill_drop_mesas_report.xml',
        'report/detalle_marcas_por_prestamista.xml',
    ],
    #'demo': ['data/account_ttg_demo.xml'],
    'installable': True,
    'application': True,
    'assets': {
        'web.report_assets_common': [
            'ttg_casino/static/src/scss/casino.scss',
        ],
    },
    'license': 'LGPL-3',
}
