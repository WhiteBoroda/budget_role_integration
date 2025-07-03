from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class BudgetRoleMapping(models.Model):
    """Налаштування зопоставлення ролей з типами бюджетів та ЦБО"""
    _name = 'budget.role.mapping'
    _description = 'Зопоставлення бізнес-ролей з бюджетуванням'
    _order = 'sequence, budget_type_id, cbo_type'

    name = fields.Char('Назва налаштування', required=True)
    sequence = fields.Integer('Послідовність', default=10)
    active = fields.Boolean('Активне', default=True)

    # Критерії відбору
    budget_type_id = fields.Many2one('budget.type', 'Тип бюджету')
    cbo_type = fields.Selection([
        ('holding', 'Холдинг'),
        ('cluster', 'Кластер'),
        ('business_direction', 'Напрямок бізнесу'),
        ('brand', 'Бренд'),
        ('enterprise', 'Підприємство'),
        ('department', 'Департамент'),
        ('division', 'Управління'),
        ('office', 'Відділ'),
        ('team', 'Група/Команда'),
        ('project', 'Проект'),
        ('other', 'Інше')
    ], 'Тип ЦБО')

    budget_level = fields.Selection([
        ('strategic', 'Стратегічний'),
        ('tactical', 'Тактичний'),
        ('operational', 'Операційний'),
        ('functional', 'Функціональний')
    ], 'Рівень бюджетування')

    company_id = fields.Many2one('res.company', 'Підприємство')

    # Призначення ролей
    budget_creator_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль складача бюджету'
    )

    budget_reviewer_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль перевіряючого бюджету'
    )

    budget_approver_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль затверджуючого бюджету'
    )

    budget_viewer_role_id = fields.Many2one(
        'business.role.catalog',
        'Роль переглядача бюджету'
    )

    # Налаштування адресації
    use_cbo_addressing = fields.Boolean(
        'Використовувати адресацію по ЦБО',
        default=True,
        help='Ролі будуть адресовані конкретному ЦБО'
    )

    @api.model
    def get_roles_for_budget(self, budget_plan):
        """Отримання ролей для конкретного бюджету на основі налаштувань"""
        domain = [('active', '=', True)]

        # Фільтрація по критеріях
        if budget_plan.budget_type_id:
            domain.append(('budget_type_id', '=', budget_plan.budget_type_id.id))

        if budget_plan.cbo_id and budget_plan.cbo_id.cbo_type:
            domain.append(('cbo_type', '=', budget_plan.cbo_id.cbo_type))

        if budget_plan.cbo_id and budget_plan.cbo_id.budget_level:
            domain.append(('budget_level', '=', budget_plan.cbo_id.budget_level))

        if budget_plan.company_id:
            domain.extend([
                '|',
                ('company_id', '=', False),
                ('company_id', '=', budget_plan.company_id.id)
            ])

        # Шукаємо найбільш відповідне налаштування
        mappings = self.search(domain, order='sequence, id')

        if mappings:
            mapping = mappings[0]  # Беремо перше за послідовністю
            return {
                'budget_creator_role_id': mapping.budget_creator_role_id.id if mapping.budget_creator_role_id else False,
                'budget_reviewer_role_id': mapping.budget_reviewer_role_id.id if mapping.budget_reviewer_role_id else False,
                'budget_approver_role_id': mapping.budget_approver_role_id.id if mapping.budget_approver_role_id else False,
                'budget_viewer_role_id': mapping.budget_viewer_role_id.id if mapping.budget_viewer_role_id else False,
                'use_role_based_approval': True
            }

        return {}