from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class BudgetRoleValidators(models.AbstractModel):
    """Валідатори для ролей в бюджетуванні"""
    _name = 'budget.role.validators'
    _description = 'Валідатори ролей'

    @api.model
    def validate_budget_workflow_transition(self, budget_plan, from_state, to_state):
        """Валідація переходів стану бюджету з урахуванням ролей"""
        if not budget_plan.use_role_based_approval:
            return True

        current_user = self.env.user
        permissions = self.env['budget.role.utils'].get_user_budget_permissions(current_user, budget_plan)

        # Правила переходів
        transition_rules = {
            ('draft', 'planning'): ['creator', 'manager'],
            ('planning', 'coordination'): ['creator', 'manager'],
            ('coordination', 'approved'): ['approver', 'manager'],
            ('coordination', 'revision'): ['reviewer', 'approver', 'manager'],
            ('revision', 'planning'): ['creator', 'manager'],
            ('approved', 'executed'): ['manager'],
            ('executed', 'closed'): ['manager']
        }

        required_roles = transition_rules.get((from_state, to_state), [])

        if required_roles and not any(role in permissions['roles'] for role in required_roles):
            allowed_roles_str = ', '.join(required_roles)
            raise UserError(
                f'Користувач {current_user.name} не має прав для переходу з стану "{from_state}" в "{to_state}". '
                f'Необхідні ролі: {allowed_roles_str}'
            )

        return True

    @api.model
    def validate_role_consistency(self, budget_plan):
        """Валідація узгодженості ролей"""
        issues = []

        if not budget_plan.use_role_based_approval:
            return issues

        # Перевірка кругових залежностей
        creator_users = set(budget_plan.current_creator_ids.ids)
        reviewer_users = set(budget_plan.current_reviewer_ids.ids)
        approver_users = set(budget_plan.current_approver_ids.ids)

        if creator_users & reviewer_users:
            issues.append({
                'type': 'warning',
                'message': 'Деякі користувачі виконують ролі і складача, і перевіряючого'
            })

        if reviewer_users & approver_users:
            issues.append({
                'type': 'warning',
                'message': 'Деякі користувачі виконують ролі і перевіряючого, і затверджуючого'
            })

        # Перевірка прав доступу на рівні ЦБО
        if budget_plan.cbo_id:
            cbo_responsible = budget_plan.cbo_id.responsible_user_id
            cbo_approver = budget_plan.cbo_id.approver_user_id

            if cbo_responsible and cbo_responsible not in budget_plan.current_creator_ids:
                issues.append({
                    'type': 'info',
                    'message': f'Відповідальний за ЦБО ({cbo_responsible.name}) не є складачем бюджету'
                })

            if cbo_approver and cbo_approver not in budget_plan.current_approver_ids:
                issues.append({
                    'type': 'info',
                    'message': f'Затверджуючий ЦБО ({cbo_approver.name}) не є затверджуючим бюджету'
                })

        return issues

    @api.model
    def validate_role_addressing(self, role_catalog, addressing_data):
        """Валідація адресації ролі"""
        if not role_catalog.addressed:
            return True

        if role_catalog.first_addressation_id:
            first_model = role_catalog.first_addressation_id.model_id.model
            if addressing_data.get('first_addressation_id') and addressing_data.get(
                    'res_model_address_1') != first_model:
                raise ValidationError(
                    f'Невідповідність моделі адресації. Очікується: {first_model}, '
                    f'отримано: {addressing_data.get("res_model_address_1")}'
                )

        return True