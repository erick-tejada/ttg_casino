# -*- coding: utf-8 -*-

{
    'name': 'TTG - Casino',
    'author': "Tejada Tech Group EIRL",
    'version': '15.0.0.6',
    'sequence': 100,
    'category': 'Accounting/Accounting',
    'description': """
        Agrega funcionalidades para tener mejor control operativo de los ingresos en Caja del Casino.""",
    'depends': ['account'],
    'summary': 'Agrega funcionalidades para tener mejor control operativo de los ingresos en Caja del Casino.',
    'website': 'https://www.tejadatech.com',
    'data': [
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'data/maquinas_data.xml',
        'views/maquina_views.xml',
        'views/cuadre_views.xml',
        'views/bill_drop_views.xml',
        'views/devolucion_views.xml',
        'views/marca_maquina_views.xml',
        'views/otros_pagos_views.xml',
        'views/marca_mesa_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/casino_views.xml',
    ],
    #'demo': ['data/account_ttg_demo.xml'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
