from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class BudgetPlanHooks(models.Model):
    """Хуки для інтеграції з основним функціоналом"""
    _inherit = 'budget.plan'

    @api.model_create_multi
    def create(self, vals_list):
        """Розширений метод створення з автопризначенням ролей"""
        records = super().create(vals_list)

        for record in records:
            # Автоматичне призначення ролей якщо налаштовано
            if record.cbo_id and record.budget_type_id and not record.budget_creator_role_id:
                mapping_data = self.env['budget.role.mapping'].get_roles_for_budget(record)
                if mapping_data:
                    record.write(mapping_data)
                    record.write({'use_role_based_approval': True})

            # Синхронізація з старими полями
            if record.use_role_based_approval:
                self.env['budget.role.utils'].sync_role_assignments(record)

        return records

    def write(self, vals):
        """Розширений метод оновлення з валідацією ролей"""
        result = super().write(vals)

        # Валідація при зміні ролей
        if any(field in vals for field in
               ['budget_creator_role_id', 'budget_reviewer_role_id', 'budget_approver_role_id']):
            for record in self:
                if record.use_role_based_approval:
                    errors, warnings = self.env['budget.role.utils'].validate_role_configuration(record)
                    if errors:
                        raise ValidationError('\n'.join(errors))

        # Синхронізація призначень
        if 'use_role_based_approval' in vals or any(field in vals for field in ['cbo_id', 'budget_type_id']):
            for record in self:
                if record.use_role_based_approval:
                    self.env['budget.role.utils'].sync_role_assignments(record)

        return result

    def action_start_planning(self):
        """Розширений початок планування з перевіркою ролей"""
        for record in self:
            if record.use_role_based_approval:
                # Валідація переходу стану
                self.env['budget.role.validators'].validate_budget_workflow_transition(
                    record, record.state, 'planning'
                )

        return super().action_start_planning()

    def action_send_coordination(self):
        """Розширена відправка на узгодження"""
        for record in self:
            if record.use_role_based_approval:
                # Валідація переходу
                self.env['budget.role.validators'].validate_budget_workflow_transition(
                    record, record.state, 'coordination'
                )

                # Додаткова валідація
                errors, warnings = self.env['budget.role.utils'].validate_role_configuration(record)
                if errors:
                    raise ValidationError('\n'.join(errors))

                # Створення активностей для перевіряючих
                for user in record.current_reviewer_ids:
                    self.env['budget.role.notifications'].create_role_activity(
                        user, record, 'coordination',
                        f'Перевірка бюджету: {record.display_name}',
                        f'Бюджет відправлено на узгодження користувачем {self.env.user.name}'
                    )

        return super().action_send_coordination()

    def action_approve(self):
        """Розширене затвердження з перевіркою ролей"""
        for record in self:
            if record.use_role_based_approval:
                # Валідація переходу
                self.env['budget.role.validators'].validate_budget_workflow_transition(
                    record, record.state, 'approved'
                )

        return super().action_approve()

    def action_request_revision(self):
        """Розширена відправка на доопрацювання"""
        for record in self:
            if record.use_role_based_approval:
                # Валідація переходу
                self.env['budget.role.validators'].validate_budget_workflow_transition(
                    record, record.state, 'revision'
                )

        return super().action_request_revision()