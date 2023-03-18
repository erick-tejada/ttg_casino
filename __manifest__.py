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
        #'security/ir.model.access.csv',
        #'data/account.account.csv',
        'views/casino_views.xml',
    ],
    #'demo': ['data/account_ttg_demo.xml'],
    'installable': True,
    'license': 'LGPL-3',
}
