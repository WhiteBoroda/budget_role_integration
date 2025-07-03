# -*- coding: utf-8 -*-
{
    'name': 'Budget Role Integration',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Budget',
    'summary': 'Інтеграція модуля бюджетування з системою бізнес-ролей',
    'description': """

                                      Budget Role Integration / Інтеграція бюджетування з бізнес-ролями
                                      ================================================================

                                      Цей модуль розширює функціонал системи бюджетування, додаючи підтримку
                                      бізнес-ролей для управління процесом затвердження бюджетів.

                                      Основні можливості:
                                      - Призначення ролей складача, перевіряючого та затверджуючого бюджетів
                                      - Автоматичне визначення виконавців ролей на основі ЦБО та типу бюджету
                                      - Контроль доступу до дій з бюджетами на основі ролей
                                      - Гнучкі налаштування зопоставлення ролей
                                      - Історія призначень та заміщень виконавців ролей
                                      - Сповіщення виконавців про необхідність дій

                                      Ролі в бюджетуванні:
                                      - **Складач бюджету** - відповідає за створення та планування бюджету
                                      - **Перевіряючий бюджету** - здійснює контроль та валідацію бюджету
                                      - **Затверджуючий бюджету** - приймає рішення про затвердження
                                      - **Переглядач бюджету** - контролює залишки та виконання

                                      Адресація ролей:
                                      - Ролі можуть бути адресовані конкретному ЦБО
                                      - Підтримка додаткової адресації по типу бюджету
                                      - Автоматичне визначення поточних виконавців
                                          """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        # Основні залежності
        'base',                      # Базовий модуль Odoo
        'budget',                    # Основний модуль бюджетування
        'business_role_executor',    # ОБОВ'ЯЗКОВО: Модуль бізнес-ролей

        # Додаткові залежності
        'mail',                      # Для сповіщень
        'hr',                        # Для організаційної структури
        'web',                       # Для веб-інтерфейсу
        'portal',                    # Для порталу користувачів

        # Технічні залежності (можуть бути потрібні для business_role_executor)
        'generic_m2o',               # Для generic many2one полів
        'generic_mixin',             # Для generic mixins
    ],
    'data': [
        # =====================================================================
        # 1. БЕЗПЕКА (завжди першою!)
        # =====================================================================
        'security/ir.model.access.csv',
        'security/budget_role_security.xml',
        'security/budget_role_groups.xml',

        # =====================================================================
        # 2. БАЗОВІ ДАНІ (послідовності, типи, каталоги)
        # =====================================================================
        'data/budget_role_sequence.xml',           # Послідовності
        'data/addressing_type_budget.xml',         # Типи адресації
        'data/budget_role_catalog_data.xml',       # Стандартні ролі

        # =====================================================================
        # 3. НАЛАШТУВАННЯ ТА КОНФІГУРАЦІЯ
        # =====================================================================
        'data/budget_role_mapping_data.xml',       # Налаштування зопоставлення ролей
        'data/mail_template_budget_roles.xml',     # Шаблони пошти
        'data/budget_role_automation.xml',         # Автоматизація
        'data/ir_cron_budget_roles.xml',          # Cron завдання

        # =====================================================================
        # 4. ПРЕДСТАВЛЕННЯ (VIEWS)
        # =====================================================================
        # Основні views
        'views/budget_plan_roles_views.xml',
        'views/budget_role_mapping_views.xml',

        # Wizard views
        'views/budget_role_executor_wizard_views.xml',
        'views/budget_role_wizard_views.xml',      # Інші wizard'и

        # Дашборди та звіти
        'views/budget_dashboards_roles.xml',
        'reports/budget_role_reports.xml',

        # Портал
        'views/portal_budget_roles.xml',

        # =====================================================================
        # 5. МЕНЮ (в самому кінці після всіх views!)
        # =====================================================================
        'data/budget_role_menu.xml',
    ],
    'demo': [
        'demo/budget_role_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'budget_role_integration/static/src/css/budget_role_styles.css',
        ],
        'web.assets_frontend': [
            'budget_role_integration/static/src/css/budget_role_styles.css',
        ],
    },
    'external_dependencies': {
        'python': [],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': '_uninstall_hook',
}