from odoo import models, fields, api, _
from datetime import date, timedelta

class BudgetRoleReportWizard(models.TransientModel):
    """Майстер створення звітів по ролях в бюджетуванні"""
    _name = 'budget.role.report.wizard'
    _description = 'Майстер звітів по ролях'

    # Параметри звіту
    report_type = fields.Selection([
        ('summary', 'Зведений звіт по ролях'),
        ('detailed', 'Детальний звіт по виконавцях'),
        ('usage', 'Звіт використання ролей'),
        ('issues', 'Звіт проблем з ролями')
    ], 'Тип звіту', required=True, default='summary')

    # Фільтри періоду
    date_from = fields.Date('Дата з', default=fields.Date.today().replace(day=1))
    date_to = fields.Date('Дата до', default=fields.Date.today())

    # Фільтри структури
    company_ids = fields.Many2many('res.company', string='Підприємства')
    cbo_ids = fields.Many2many('budget.responsibility.center', string='ЦБО')
    budget_type_ids = fields.Many2many('budget.type', string='Типи бюджетів')

    # Фільтри користувачів та ролей
    user_ids = fields.Many2many('res.users', string='Користувачі')
    role_ids = fields.Many2many('business.role.catalog', string='Ролі')

    # Налаштування виводу
    group_by_cbo = fields.Boolean('Групувати за ЦБО', default=True)
    group_by_role = fields.Boolean('Групувати за ролями', default=False)
    group_by_user = fields.Boolean('Групувати за користувачами', default=False)

    include_inactive = fields.Boolean('Включити неактивні записи', default=False)
    include_statistics = fields.Boolean('Включити статистику', default=True)

    def action_generate_report(self):
        """Генерація звіту"""
        report_data = self._prepare_report_data()

        if self.report_type == 'summary':
            return self._generate_summary_report(report_data)
        elif self.report_type == 'detailed':
            return self._generate_detailed_report(report_data)
        elif self.report_type == 'usage':
            return self._generate_usage_report(report_data)
        elif self.report_type == 'issues':
            return self._generate_issues_report(report_data)

    def _prepare_report_data(self):
        """Підготовка даних для звіту"""
        # Базовий домен для бюджетів
        budget_domain = [
            ('use_role_based_approval', '=', True),
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to)
        ]

        # Додаткові фільтри
        if self.company_ids:
            budget_domain.append(('company_id', 'in', self.company_ids.ids))
        if self.cbo_ids:
            budget_domain.append(('cbo_id', 'in', self.cbo_ids.ids))
        if self.budget_type_ids:
            budget_domain.append(('budget_type_id', 'in', self.budget_type_ids.ids))

        budgets = self.env['budget.plan'].search(budget_domain)

        # Домен для виконавців ролей
        executor_domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ]

        if not self.include_inactive:
            executor_domain.append(('status_role', '=', True))

        if self.user_ids:
            executor_domain.append(('user_id', 'in', self.user_ids.ids))
        if self.role_ids:
            executor_domain.append(('role_id', 'in', self.role_ids.ids))

        executors = self.env['business.role.executor'].search(executor_domain)

        return {
            'budgets': budgets,
            'executors': executors,
            'date_from': self.date_from,
            'date_to': self.date_to
        }

    def _generate_summary_report(self, data):
        """Генерація зведеного звіту"""
        return {
            'type': 'ir.actions.report',
            'report_name': 'budget_role_integration.budget_role_summary_report',
            'report_type': 'qweb-pdf',
            'data': data,
            'context': self.env.context
        }

    def _generate_detailed_report(self, data):
        """Генерація детального звіту"""
        return {
            'type': 'ir.actions.report',
            'report_name': 'budget_role_integration.budget_role_detailed_report',
            'report_type': 'qweb-pdf',
            'data': data,
            'context': self.env.context
        }

    def _generate_usage_report(self, data):
        """Генерація звіту використання"""
        # Додаткові дані для звіту використання
        role_usage = {}
        for budget in data['budgets']:
            for role_field in ['budget_creator_role_id', 'budget_reviewer_role_id', 'budget_approver_role_id']:
                role = getattr(budget, role_field)
                if role:
                    if role.id not in role_usage:
                        role_usage[role.id] = {
                            'role': role,
                            'count': 0,
                            'budgets': []
                        }
                    role_usage[role.id]['count'] += 1
                    role_usage[role.id]['budgets'].append(budget)

        data['role_usage'] = role_usage

        return {
            'type': 'ir.actions.report',
            'report_name': 'budget_role_integration.budget_role_usage_report',
            'report_type': 'qweb-pdf',
            'data': data,
            'context': self.env.context
        }

    def _generate_issues_report(self, data):
        """Генерація звіту проблем"""
        # Запускаємо валідацію для збору проблем
        validation_wizard = self.env['budget.role.validation.wizard'].create({
            'check_missing_roles': True,
            'check_missing_executors': True,
            'check_outdated_assignments': True,
            'company_ids': [(6, 0, self.company_ids.ids)],
            'cbo_ids': [(6, 0, self.cbo_ids.ids)]
        })

        validation_wizard.action_validate_roles()
        data['validation_results'] = validation_wizard.validation_line_ids

        return {
            'type': 'ir.actions.report',
            'report_name': 'budget_role_integration.budget_role_issues_report',
            'report_type': 'qweb-pdf',
            'data': data,
            'context': self.env.context
        }