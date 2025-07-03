from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BudgetRoleMassAssignmentWizard(models.TransientModel):
    """Майстер масового призначення ролей для бюджетів"""
    _name = 'budget.role.mass.assignment.wizard'
    _description = 'Майстер масового призначення ролей'

    # Фільтри для вибору бюджетів
    budget_ids = fields.Many2many(
        'budget.plan',
        string='Бюджети для обробки',
        domain=[('use_role_based_approval', '=', False)]
    )

    filter_by_cbo = fields.Boolean('Фільтрувати за ЦБО', default=False)
    cbo_ids = fields.Many2many(
        'budget.responsibility.center',
        relation='budget_mass_assign_cbo_rel',  # Короткое имя таблицы
        column1='wizard_id',
        column2='cbo_id',
        string='ЦБО'
    )

    filter_by_type = fields.Boolean('Фільтрувати за типом бюджету', default=False)
    budget_type_ids = fields.Many2many('budget.type', string='Типи бюджетів')

    filter_by_period = fields.Boolean('Фільтрувати за періодом', default=False)
    period_ids = fields.Many2many('budget.period', string='Періоди')

    filter_by_state = fields.Boolean('Фільтрувати за статусом', default=True)
    state_filter = fields.Selection([
        ('draft', 'Чернетка'),
        ('planning', 'Планування'),
        ('coordination', 'Узгодження'),
        ('approved', 'Затверджений'),
        ('revision', 'Доопрацювання')
    ], 'Статус бюджету', default='draft')

    # Ролі для призначення
    assignment_mode = fields.Selection([
        ('auto', 'Автоматичне призначення за налаштуваннями'),
        ('manual', 'Ручне призначення ролей'),
        ('template', 'Використати шаблон')
    ], 'Режим призначення', default='auto', required=True)

    # Ручне призначення
    budget_creator_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль складача',
        domain=[('role', 'ilike', 'складач')]
    )

    budget_reviewer_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль перевіряючого',
        domain=[('role', 'ilike', 'перевір')]
    )

    budget_approver_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль затверджуючого',
        domain=[('role', 'ilike', 'затвердж')]
    )

    # Шаблон
    template_id = fields.Many2one('budget.role.template', 'Шаблон ролей')

    # Налаштування обробки
    enable_role_system = fields.Boolean('Увімкнути систему ролей', default=True)
    validate_executors = fields.Boolean('Перевіряти наявність виконавців', default=True)
    send_notifications = fields.Boolean('Відправляти сповіщення', default=False)

    # Результати
    processed_count = fields.Integer('Оброблено бюджетів', readonly=True)
    error_count = fields.Integer('Помилок', readonly=True)
    error_details = fields.Text('Деталі помилок', readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Встановлення значень за замовчуванням"""
        res = super().default_get(fields_list)

        # Якщо викликано з контексту бюджетів
        if self.env.context.get('active_model') == 'budget.plan':
            budget_ids = self.env.context.get('active_ids', [])
            budgets = self.env['budget.plan'].browse(budget_ids)

            # Фільтруємо тільки бюджети без ролей
            budgets_without_roles = budgets.filtered(
                lambda b: not b.use_role_based_approval
            )

            res['budget_ids'] = [(6, 0, budgets_without_roles.ids)]

        return res

    @api.onchange('filter_by_cbo', 'filter_by_type', 'filter_by_period', 'filter_by_state')
    def _onchange_filters(self):
        """Автоматичний пошук бюджетів за фільтрами"""
        domain = [('use_role_based_approval', '=', False)]

        if self.filter_by_cbo and self.cbo_ids:
            domain.append(('cbo_id', 'in', self.cbo_ids.ids))

        if self.filter_by_type and self.budget_type_ids:
            domain.append(('budget_type_id', 'in', self.budget_type_ids.ids))

        if self.filter_by_period and self.period_ids:
            domain.append(('period_id', 'in', self.period_ids.ids))

        if self.filter_by_state and self.state_filter:
            domain.append(('state', '=', self.state_filter))

        budgets = self.env['budget.plan'].search(domain)
        self.budget_ids = [(6, 0, budgets.ids)]

    @api.onchange('template_id')
    def _onchange_template(self):
        """Заповнення ролей з шаблону"""
        if self.template_id:
            self.budget_creator_role_id = self.template_id.budget_creator_role_id
            self.budget_reviewer_role_id = self.template_id.budget_reviewer_role_id
            self.budget_approver_role_id = self.template_id.budget_approver_role_id

    def action_process_budgets(self):
        """Обробка вибраних бюджетів"""
        if not self.budget_ids:
            raise ValidationError('Оберіть бюджети для обробки!')

        processed = 0
        errors = 0
        error_details = []

        for budget in self.budget_ids:
            try:
                self._process_single_budget(budget)
                processed += 1
            except Exception as e:
                errors += 1
                error_details.append(f"Бюджет {budget.display_name}: {str(e)}")

        # Оновлення результатів
        self.write({
            'processed_count': processed,
            'error_count': errors,
            'error_details': '\n'.join(error_details)
        })

        # Відправка сповіщень
        if self.send_notifications and processed > 0:
            self._send_completion_notifications()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'budget.role.mass.assignment.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_results': True}
        }

    def _process_single_budget(self, budget):
        """Обробка одного бюджету"""
        role_data = {}

        if self.assignment_mode == 'auto':
            # Автоматичне призначення за налаштуваннями
            mapping_data = self.env['budget.role.mapping'].get_roles_for_budget(budget)
            role_data.update(mapping_data)

        elif self.assignment_mode == 'manual':
            # Ручне призначення
            role_data = {
                'budget_creator_role_id': self.budget_creator_role_id.id,
                'budget_reviewer_role_id': self.budget_reviewer_role_id.id,
                'budget_approver_role_id': self.budget_approver_role_id.id
            }

        elif self.assignment_mode == 'template':
            # Призначення з шаблону
            if not self.template_id:
                raise ValidationError('Оберіть шаблон для призначення!')
            role_data = {
                'budget_creator_role_id': self.template_id.budget_creator_role_id.id,
                'budget_reviewer_role_id': self.template_id.budget_reviewer_role_id.id,
                'budget_approver_role_id': self.template_id.budget_approver_role_id.id
            }

        # Додаткові налаштування
        if self.enable_role_system:
            role_data['use_role_based_approval'] = True

        # Оновлення бюджету
        budget.write(role_data)

        # Валідація виконавців
        if self.validate_executors and budget.use_role_based_approval:
            budget._validate_role_executors()

    def _send_completion_notifications(self):
        """Відправка сповіщень про завершення"""
        admin_users = self.env['res.users'].search([
            ('groups_id', 'in', [self.env.ref('budget.group_budget_manager').id])
        ])

        for admin in admin_users:
            self.env['mail.activity'].create({
                'res_model': 'budget.role.mass.assignment.wizard',
                'res_id': self.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'user_id': admin.id,
                'summary': 'Масове призначення ролей завершено',
                'note': f'Оброблено {self.processed_count} бюджетів, помилок: {self.error_count}'
            })