from odoo import models, fields, api, _
from datetime import date, timedelta

class BudgetRoleNotifications(models.AbstractModel):
    """Система сповіщень для ролей в бюджетуванні"""
    _name = 'budget.role.notifications'
    _description = 'Сповіщення для ролей'

    @api.model
    def send_role_assignment_notification(self, user, role, budget_plan, assignment_type='assigned'):
        """Відправка сповіщення про призначення ролі"""
        template_id = False

        if assignment_type == 'assigned':
            template_id = self.env.ref('budget_role_integration.mail_template_budget_role_assignment', False)
        elif assignment_type == 'coordination':
            template_id = self.env.ref('budget_role_integration.mail_template_budget_role_coordination', False)

        if template_id:
            template_id.send_mail(
                budget_plan.id,
                force_send=True,
                email_values={'email_to': user.email}
            )

    @api.model
    def create_role_activity(self, user, budget_plan, activity_type, summary, note=None):
        """Створення активності для користувача"""
        activity_type_id = False

        if activity_type == 'coordination':
            activity_type_id = self.env.ref('mail.mail_activity_data_todo')
        elif activity_type == 'approval':
            activity_type_id = self.env.ref('mail.mail_activity_data_call')

        if activity_type_id:
            self.env['mail.activity'].create({
                'res_model': 'budget.plan',
                'res_id': budget_plan.id,
                'activity_type_id': activity_type_id.id,
                'user_id': user.id,
                'summary': summary,
                'note': note or '',
                'date_deadline': fields.Date.today() + timedelta(days=3)
            })

    @api.model
    def notify_role_issues(self, issues):
        """Сповіщення про проблеми з ролями"""
        if not issues:
            return

        # Групуємо проблеми по типах
        critical_issues = [i for i in issues if i.get('type') == 'critical']
        warning_issues = [i for i in issues if i.get('type') == 'warning']

        # Сповіщаємо менеджерів про критичні проблеми
        if critical_issues:
            managers = self.env['res.users'].search([
                ('groups_id', 'in', [self.env.ref('budget.group_budget_manager').id])
            ])

            for manager in managers:
                self.env['mail.activity'].create({
                    'res_model': 'budget.plan',
                    'res_id': critical_issues[0].get('budget_id', False),
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'user_id': manager.id,
                    'summary': f'Критичні проблеми з ролями ({len(critical_issues)} шт.)',
                    'note': '\n'.join([i.get('description', '') for i in critical_issues]),
                    'date_deadline': fields.Date.today()
                })