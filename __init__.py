from . import models
from . import wizard

# Імпорти для хуків
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def _post_init_hook(cr, registry):
    """Хук після встановлення модуля"""
    _logger.info('Виконання post_init_hook для budget_role_integration')

    env = api.Environment(cr, SUPERUSER_ID, {})

    try:
        # 1. Автоматичне призначення ролей для існуючих бюджетів
        existing_budgets = env['budget.plan'].search([
            ('use_role_based_approval', '=', False)
        ])

        updated_count = 0
        for budget in existing_budgets:
            # Спробуємо автоматично призначити ролі
            mapping_data = env['budget.role.mapping'].get_roles_for_budget(budget)
            if mapping_data:
                budget.write({
                    'budget_creator_role_id': mapping_data.get('budget_creator_role_id'),
                    'budget_reviewer_role_id': mapping_data.get('budget_reviewer_role_id'),
                    'budget_approver_role_id': mapping_data.get('budget_approver_role_id'),
                    'use_role_based_approval': True
                })
                updated_count += 1

        _logger.info(f'Автоматично оновлено {updated_count} існуючих бюджетів з ролями')

        # 2. Перевірка наявності стандартних ролей
        role_catalog = env['business.role.catalog']

        standard_roles = [
            'Складач бюджету',
            'Перевіряючий бюджету',
            'Затверджуючий бюджету'
        ]

        for role_name in standard_roles:
            existing_role = role_catalog.search([('role', '=', role_name)], limit=1)
            if not existing_role:
                _logger.warning(f'Стандартна роль "{role_name}" не знайдена. Створіть її вручну.')

        # 3. Перевірка типів адресації
        addressing_type = env['addressing.type']
        cbo_addressing = addressing_type.search([
            ('name', '=', 'Центр бюджетної відповідальності')
        ], limit=1)

        if not cbo_addressing:
            _logger.warning('Тип адресації "Центр бюджетної відповідальності" не знайдений')

        # 4. Створення початкових налаштувань якщо їх немає
        mapping_count = env['budget.role.mapping'].search_count([])
        if mapping_count == 0:
            _logger.info('Налаштування ролей будуть створені з demo/початкових даних')

        _logger.info('post_init_hook успішно завершений')

    except Exception as e:
        _logger.error(f'Помилка в post_init_hook: {str(e)}')
        # Не викидаємо виключення щоб не перервати встановлення


def _uninstall_hook(cr, registry):
    """Хук при видаленні модуля"""
    _logger.info('Виконання uninstall_hook для budget_role_integration')

    env = api.Environment(cr, SUPERUSER_ID, {})

    try:
        # 1. Відключаємо систему ролей для всіх бюджетів
        all_budgets = env['budget.plan'].search([
            ('use_role_based_approval', '=', True)
        ])

        if all_budgets:
            all_budgets.write({
                'use_role_based_approval': False,
                'budget_creator_role_id': False,
                'budget_reviewer_role_id': False,
                'budget_approver_role_id': False
            })
            _logger.info(f'Відключено систему ролей для {len(all_budgets)} бюджетів')

        # 2. Очищення налаштувань ролей (опційно)
        # mappings = env['budget.role.mapping'].search([])
        # if mappings:
        #     mappings.unlink()
        #     _logger.info(f'Видалено {len(mappings)} налаштувань ролей')

        # 3. Очищення шаблонів ролей
        templates = env['budget.role.template'].search([])
        if templates:
            templates.unlink()
            _logger.info(f'Видалено {len(templates)} шаблонів ролей')

        # 4. Відновлення старих полей відповідальних (якщо потрібно)
        budgets_with_roles = env['budget.plan'].search([
            '|', '|',
            ('current_creator_ids', '!=', False),
            ('current_reviewer_ids', '!=', False),
            ('current_approver_ids', '!=', False)
        ])

        for budget in budgets_with_roles:
            # Встановлюємо старі поля на основі ролей
            if budget.current_creator_ids and not budget.responsible_user_id:
                budget.responsible_user_id = budget.current_creator_ids[0]

            if budget.current_reviewer_ids and not budget.coordinator_user_id:
                budget.coordinator_user_id = budget.current_reviewer_ids[0]

            if budget.current_approver_ids and not budget.approver_user_id:
                budget.approver_user_id = budget.current_approver_ids[0]

        _logger.info('uninstall_hook успішно завершений')

    except Exception as e:
        _logger.error(f'Помилка в uninstall_hook: {str(e)}')
        # Не викидаємо виключення
