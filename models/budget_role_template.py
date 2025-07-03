from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class BudgetRoleTemplate(models.Model):
    """Шаблони ролей для бюджетування"""
    _name = 'budget.role.template'
    _description = 'Шаблони ролей бюджетування'
    _order = 'sequence, name'

    name = fields.Char('Назва шаблону', required=True)
    description = fields.Text('Опис')
    sequence = fields.Integer('Послідовність', default=10)
    active = fields.Boolean('Активний', default=True)

    # Ролі в шаблоні
    budget_creator_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль складача бюджету',
        required=True
    )

    budget_reviewer_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль перевіряючого бюджету',
        required=True
    )

    budget_approver_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль затверджуючого бюджету',
        required=True
    )

    # Додаткові налаштування
    use_cbo_addressing = fields.Boolean(
        'Використовувати адресацію по ЦБО',
        default=True
    )

    auto_validate_executors = fields.Boolean(
        'Автоматично перевіряти виконавців',
        default=True
    )

    # Область застосування
    company_ids = fields.Many2many(
        'res.company',
        string='Підприємства',
        help='Якщо не вказано, шаблон доступний для всіх підприємств'
    )

    budget_type_ids = fields.Many2many(
        'budget.type',
        string='Типи бюджетів',
        help='Якщо не вказано, шаблон підходить для всіх типів'
    )

    # Статистика використання
    usage_count = fields.Integer(
        'Кількість використань',
        compute='_compute_usage_count'
    )

    @api.depends('budget_creator_role_id', 'budget_reviewer_role_id', 'budget_approver_role_id')
    def _compute_usage_count(self):
        """Обчислення кількості використань шаблону"""
        for template in self:
            count = self.env['budget.plan'].search_count([
                ('budget_creator_role_id', '=', template.budget_creator_role_id.id),
                ('budget_reviewer_role_id', '=', template.budget_reviewer_role_id.id),
                ('budget_approver_role_id', '=', template.budget_approver_role_id.id)
            ])
            template.usage_count = count

    def action_apply_to_budgets(self):
        """Застосування шаблону до бюджетів"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Застосування шаблону "{self.name}"',
            'res_model': 'budget.role.mass.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_assignment_mode': 'template',
                'default_template_id': self.id
            }
        }