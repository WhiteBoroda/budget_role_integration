from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class BudgetRoleUtils(models.AbstractModel):
    """Допоміжні методи для роботи з ролями в бюджетуванні"""
    _name = 'budget.role.utils'
    _description = 'Utility для ролей бюджетування'

    @api.model
    def validate_role_configuration(self, budget_plan):
        """Валідація налаштувань ролей для бюджету"""
        errors = []
        warnings = []

        if not budget_plan.use_role_based_approval:
            return errors, warnings

        # Перевірка наявності ролей
        if not budget_plan.budget_creator_role_id:
            errors.append('Не призначено роль складача бюджету')

        if not budget_plan.budget_reviewer_role_id:
            errors.append('Не призначено роль перевіряючого бюджету')

        if not budget_plan.budget_approver_role_id:
            errors.append('Не призначено роль затверджуючого бюджету')

        # Перевірка налаштувань адресації ролей
        for role_field in ['budget_creator_role_id', 'budget_reviewer_role_id', 'budget_approver_role_id']:
            role = getattr(budget_plan, role_field)
            if role and role.addressed and not budget_plan.cbo_id:
                warnings.append(f'Роль {role.role} потребує адресації, але ЦБО не вказано')

        # Перевірка наявності виконавців
        if budget_plan.budget_reviewer_role_id and not budget_plan.current_reviewer_ids:
            errors.append(f'Відсутні виконавці для ролі "{budget_plan.budget_reviewer_role_id.role}"')

        if budget_plan.budget_approver_role_id and not budget_plan.current_approver_ids:
            errors.append(f'Відсутні виконавці для ролі "{budget_plan.budget_approver_role_id.role}"')

        return errors, warnings

    @api.model
    def get_user_budget_permissions(self, user, budget_plan):
        """Отримання прав користувача для бюджету"""
        permissions = {
            'can_read': False,
            'can_write': False,
            'can_coordinate': False,
            'can_approve': False,
            'roles': []
        }

        if not budget_plan.use_role_based_approval:
            # Старий механізм прав
            if user == budget_plan.responsible_user_id:
                permissions.update({'can_read': True, 'can_write': True})
            if user == budget_plan.coordinator_user_id:
                permissions.update({'can_read': True, 'can_coordinate': True})
            if user == budget_plan.approver_user_id:
                permissions.update({'can_read': True, 'can_approve': True})
            return permissions

        # Новий механізм на основі ролей
        if user in budget_plan.current_creator_ids:
            permissions.update({
                'can_read': True,
                'can_write': True,
                'roles': permissions['roles'] + ['creator']
            })

        if user in budget_plan.current_reviewer_ids:
            permissions.update({
                'can_read': True,
                'can_coordinate': True,
                'roles': permissions['roles'] + ['reviewer']
            })

        if user in budget_plan.current_approver_ids:
            permissions.update({
                'can_read': True,
                'can_approve': True,
                'roles': permissions['roles'] + ['approver']
            })

        # Менеджери завжди мають доступ
        if user.has_group('budget.group_budget_manager'):
            permissions.update({
                'can_read': True,
                'can_write': True,
                'can_coordinate': True,
                'can_approve': True,
                'roles': permissions['roles'] + ['manager']
            })

        return permissions

    @api.model
    def sync_role_assignments(self, budget_plan):
        """Синхронізація призначень ролей з поточним станом"""
        if not budget_plan.use_role_based_approval:
            return

        # Встановлюємо відповідальних на основі ролей
        if budget_plan.current_creator_ids and not budget_plan.responsible_user_id:
            budget_plan.responsible_user_id = budget_plan.current_creator_ids[0]

        # Синхронізуємо з старими полями для зворотної сумісності
        if budget_plan.current_reviewer_ids and not budget_plan.coordinator_user_id:
            budget_plan.coordinator_user_id = budget_plan.current_reviewer_ids[0]

        if budget_plan.current_approver_ids and not budget_plan.approver_user_id:
            budget_plan.approver_user_id = budget_plan.current_approver_ids[0]

    @api.model
    def get_role_substitutions(self, role_catalog, target_date=None):
        """Отримання активних заміщень для ролі"""
        if not target_date:
            target_date = date.today()

        # Шукаємо активні заміщення
        substitutions = self.env['business.role.substitution'].search([
            ('lifecycle_state', '=', 'active'),
            ('start_date', '<=', target_date),
            ('end_date', '>=', target_date)
        ])

        active_substitutions = []
        for substitution in substitutions:
            for line in substitution.substitution_line_ids:
                if line.role_id == role_catalog and line.start_date <= target_date <= line.end_date:
                    active_substitutions.append({
                        'original_user': substitution.replaceable_person_id,
                        'substitute_user': line.substitute_id,
                        'reason': substitution.reason,
                        'start_date': line.start_date,
                        'end_date': line.end_date
                    })

        return active_substitutions

    @api.model
    def cleanup_outdated_role_assignments(self, days_threshold=365):
        """Очищення застарілих призначень ролей"""
        cutoff_date = date.today() - timedelta(days=days_threshold)

        old_executors = self.env['business.role.executor'].search([
            ('date', '<', cutoff_date),
            ('status_role', '=', False),
            ('role_id.role', 'ilike', 'бюджет')
        ])

        _logger.info(f'Видалення {len(old_executors)} застарілих призначень ролей')
        old_executors.unlink()

        return len(old_executors)

    @api.model
    def generate_role_statistics(self, date_from=None, date_to=None):
        """Генерація статистики по ролях"""
        if not date_from:
            date_from = date.today().replace(day=1)
        if not date_to:
            date_to = date.today()

        stats = {}

        # Загальна статистика
        total_budgets = self.env['budget.plan'].search_count([
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to)
        ])

        budgets_with_roles = self.env['budget.plan'].search_count([
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
            ('use_role_based_approval', '=', True)
        ])

        stats['general'] = {
            'total_budgets': total_budgets,
            'budgets_with_roles': budgets_with_roles,
            'role_adoption_percent': (budgets_with_roles / total_budgets * 100) if total_budgets > 0 else 0
        }

        # Статистика по ролях
        budget_roles = self.env['business.role.catalog'].search([
            ('role', 'ilike', 'бюджет')
        ])

        role_stats = {}
        for role in budget_roles:
            executors_count = self.env['business.role.executor'].search_count([
                ('role_id', '=', role.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('status_role', '=', True)
            ])

            usage_count = 0
            for field in ['budget_creator_role_id', 'budget_reviewer_role_id', 'budget_approver_role_id']:
                usage_count += self.env['budget.plan'].search_count([
                    (field, '=', role.id),
                    ('create_date', '>=', date_from),
                    ('create_date', '<=', date_to)
                ])

            role_stats[role.id] = {
                'role': role,
                'executors_count': executors_count,
                'usage_count': usage_count
            }

        stats['roles'] = role_stats

        # Статистика по ЦБО
        cbo_stats = {}
        cbos = self.env['budget.responsibility.center'].search([])

        for cbo in cbos:
            cbo_budgets = self.env['budget.plan'].search_count([
                ('cbo_id', '=', cbo.id),
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to)
            ])

            cbo_with_roles = self.env['budget.plan'].search_count([
                ('cbo_id', '=', cbo.id),
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to),
                ('use_role_based_approval', '=', True)
            ])

            cbo_stats[cbo.id] = {
                'cbo': cbo,
                'total_budgets': cbo_budgets,
                'budgets_with_roles': cbo_with_roles,
                'role_adoption_percent': (cbo_with_roles / cbo_budgets * 100) if cbo_budgets > 0 else 0
            }

        stats['cbos'] = cbo_stats

        return stats