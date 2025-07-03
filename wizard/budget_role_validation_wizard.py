from odoo import models, fields, api, _
from datetime import date, timedelta

class BudgetRoleValidationWizard(models.TransientModel):
    """Майстер валідації ролей в бюджетуванні"""
    _name = 'budget.role.validation.wizard'
    _description = 'Майстер валідації ролей'

    # Налаштування перевірки
    check_missing_roles = fields.Boolean('Перевірити відсутні ролі', default=True)
    check_missing_executors = fields.Boolean('Перевірити відсутніх виконавців', default=True)
    check_outdated_assignments = fields.Boolean('Перевірити застарілі призначення', default=True)
    check_duplicate_executors = fields.Boolean('Перевірити дублікати виконавців', default=False)

    # Фільтри
    company_ids = fields.Many2many('res.company', string='Підприємства')
    cbo_ids = fields.Many2many('budget.responsibility.center', string='ЦБО')
    period_ids = fields.Many2many('budget.period', string='Періоди')

    # Результати перевірки
    validation_line_ids = fields.One2many(
        'budget.role.validation.line',
        'wizard_id',
        'Результати перевірки'
    )

    total_issues = fields.Integer('Загальна кількість проблем', compute='_compute_totals')
    critical_issues = fields.Integer('Критичні проблеми', compute='_compute_totals')
    warning_issues = fields.Integer('Попередження', compute='_compute_totals')

    @api.depends('validation_line_ids')
    def _compute_totals(self):
        """Обчислення загальної статистики"""
        for wizard in self:
            total = len(wizard.validation_line_ids)
            critical = len(wizard.validation_line_ids.filtered(lambda l: l.issue_type == 'critical'))
            warning = len(wizard.validation_line_ids.filtered(lambda l: l.issue_type == 'warning'))

            wizard.total_issues = total
            wizard.critical_issues = critical
            wizard.warning_issues = warning

    def action_validate_roles(self):
        """Виконання валідації ролей"""
        # Очищаємо попередні результати
        self.validation_line_ids.unlink()

        validation_lines = []

        if self.check_missing_roles:
            validation_lines.extend(self._check_missing_roles())

        if self.check_missing_executors:
            validation_lines.extend(self._check_missing_executors())

        if self.check_outdated_assignments:
            validation_lines.extend(self._check_outdated_assignments())

        if self.check_duplicate_executors:
            validation_lines.extend(self._check_duplicate_executors())

        # Створення ліній результатів
        for line_data in validation_lines:
            line_data['wizard_id'] = self.id
            self.env['budget.role.validation.line'].create(line_data)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'budget.role.validation.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_results': True}
        }

    def _get_budget_domain(self):
        """Формування домену для пошуку бюджетів"""
        domain = [('use_role_based_approval', '=', True)]

        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        if self.cbo_ids:
            domain.append(('cbo_id', 'in', self.cbo_ids.ids))
        if self.period_ids:
            domain.append(('period_id', 'in', self.period_ids.ids))

        return domain

    def _check_missing_roles(self):
        """Перевірка відсутніх ролей"""
        results = []
        budgets = self.env['budget.plan'].search(self._get_budget_domain())

        for budget in budgets:
            issues = []
            if not budget.budget_creator_role_id:
                issues.append('складач')
            if not budget.budget_reviewer_role_id:
                issues.append('перевіряючий')
            if not budget.budget_approver_role_id:
                issues.append('затверджуючий')

            if issues:
                results.append({
                    'budget_id': budget.id,
                    'issue_type': 'critical',
                    'issue_description': f'Відсутні ролі: {", ".join(issues)}',
                    'suggested_action': 'Призначити відповідні ролі в налаштуваннях бюджету'
                })

        return results

    def _check_missing_executors(self):
        """Перевірка відсутніх виконавців"""
        results = []
        budgets = self.env['budget.plan'].search(self._get_budget_domain())

        for budget in budgets:
            issues = []
            if budget.budget_reviewer_role_id and not budget.current_reviewer_ids:
                issues.append('перевіряючий')
            if budget.budget_approver_role_id and not budget.current_approver_ids:
                issues.append('затверджуючий')

            if issues:
                results.append({
                    'budget_id': budget.id,
                    'issue_type': 'critical',
                    'issue_description': f'Відсутні виконавці ролей: {", ".join(issues)}',
                    'suggested_action': 'Призначити користувачів на відповідні ролі'
                })

        return results

    def _check_outdated_assignments(self):
        """Перевірка застарілих призначень"""
        results = []
        cutoff_date = fields.Date.today() - timedelta(days=365)

        old_executors = self.env['business.role.executor'].search([
            ('date', '<', cutoff_date),
            ('status_role', '=', True),
            ('role_id.role', 'ilike', 'бюджет')
        ])

        for executor in old_executors:
            results.append({
                'budget_id': False,
                'issue_type': 'warning',
                'issue_description': f'Застаріле призначення: {executor.user_id.name} на роль {executor.role_id.role}',
                'suggested_action': 'Перевірити актуальність призначення'
            })

        return results

    def _check_duplicate_executors(self):
        """Перевірка дублікатів виконавців"""
        results = []

        # Пошук дублікатів по комбінації користувач+роль+адресація
        duplicates_query = """
                           SELECT user_id, role_id, first_addressation_id, COUNT(*)
                           FROM business_role_executor
                           WHERE status_role = true
                             AND date >= current_date - interval '30 days'
                             AND role_id IN (
                               SELECT id FROM business_role_catalog
                               WHERE role ILIKE '%бюджет%'
                               )
                           GROUP BY user_id, role_id, first_addressation_id
                           HAVING COUNT (*) > 1 \
                           """

        self.env.cr.execute(duplicates_query)
        duplicates = self.env.cr.fetchall()

        for user_id, role_id, addr_id, count in duplicates:
            user = self.env['res.users'].browse(user_id)
            role = self.env['business.role.catalog'].browse(role_id)

            results.append({
                'budget_id': False,
                'issue_type': 'warning',
                'issue_description': f'Дублікат призначення: {user.name} на роль {role.role} ({count} записів)',
                'suggested_action': 'Видалити зайві записи призначень'
            })

        return results


class BudgetRoleValidationLine(models.TransientModel):
    """Лінії результатів валідації ролей"""
    _name = 'budget.role.validation.line'
    _description = 'Результати валідації ролей'

    wizard_id = fields.Many2one('budget.role.validation.wizard', 'Майстер')
    budget_id = fields.Many2one('budget.plan', 'Бюджет')

    issue_type = fields.Selection([
        ('critical', 'Критична'),
        ('warning', 'Попередження'),
        ('info', 'Інформація')
    ], 'Тип проблеми', required=True)

    issue_description = fields.Text('Опис проблеми', required=True)
    suggested_action = fields.Text('Рекомендована дія')

    is_resolved = fields.Boolean('Вирішено', default=False)
    resolution_notes = fields.Text('Примітки до вирішення')

    def action_resolve_issue(self):
        """Позначити проблему як вирішену"""
        self.write({
            'is_resolved': True,
            'resolution_notes': f'Вирішено {fields.Datetime.now()}'
        })