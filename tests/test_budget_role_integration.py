from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta


class TestBudgetRoleIntegration(TransactionCase):
    """Тести інтеграції бюджетування з бізнес-ролями"""

    def setUp(self):
        super().setUp()

        # Створення тестових користувачів
        self.user_creator = self.env['res.users'].create({
            'name': 'Test Creator',
            'login': 'test_creator',
            'email': 'creator@test.com',
            'groups_id': [(6, 0, [self.env.ref('budget.group_budget_user').id])]
        })

        self.user_reviewer = self.env['res.users'].create({
            'name': 'Test Reviewer',
            'login': 'test_reviewer',
            'email': 'reviewer@test.com',
            'groups_id': [(6, 0, [self.env.ref('budget.group_budget_user').id])]
        })

        self.user_approver = self.env['res.users'].create({
            'name': 'Test Approver',
            'login': 'test_approver',
            'email': 'approver@test.com',
            'groups_id': [(6, 0, [self.env.ref('budget.group_budget_manager').id])]
        })

        # Створення тестових ролей
        self.role_creator = self.env['business.role.catalog'].create({
            'role': 'Тестовий складач бюджету',
            'addressed': True,
            'personified': True
        })

        self.role_reviewer = self.env['business.role.catalog'].create({
            'role': 'Тестовий перевіряючий бюджету',
            'addressed': True,
            'personified': True
        })

        self.role_approver = self.env['business.role.catalog'].create({
            'role': 'Тестовий затверджуючий бюджету',
            'addressed': True,
            'personified': True
        })

        # Створення тестового ЦБО
        self.cbo = self.env['budget.responsibility.center'].create({
            'name': 'Тестовий ЦБО',
            'code': 'TEST',
            'cbo_type': 'department',
            'budget_level': 'operational'
        })

        # Створення тестового типу бюджету
        self.budget_type = self.env['budget.type'].create({
            'name': 'Тестовий тип бюджету',
            'code': 'TEST',
            'budget_category': 'administrative'
        })

        # Створення тестового періоду
        self.period = self.env['budget.period'].create({
            'name': 'Тестовий період',
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90)
        })

    def test_role_assignment(self):
        """Тест призначення ролей бюджету"""
        budget = self.env['budget.plan'].create({
            'name': 'Тестовий бюджет',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id,
            'period_id': self.period.id,
            'responsible_user_id': self.user_creator.id,
            'use_role_based_approval': True,
            'budget_creator_role_id': self.role_creator.id,
            'budget_reviewer_role_id': self.role_reviewer.id,
            'budget_approver_role_id': self.role_approver.id
        })

        self.assertEqual(budget.budget_creator_role_id, self.role_creator)
        self.assertEqual(budget.budget_reviewer_role_id, self.role_reviewer)
        self.assertEqual(budget.budget_approver_role_id, self.role_approver)

    def test_role_executors_computation(self):
        """Тест обчислення виконавців ролей"""
        # Призначаємо виконавців ролей
        self.env['business.role.executor'].create({
            'date': date.today(),
            'user_id': self.user_creator.id,
            'role_id': self.role_creator.id,
            'status_role': True,
            'res_model_address_1': 'budget.responsibility.center',
            'first_addressation_id': self.cbo.id
        })

        self.env['business.role.executor'].create({
            'date': date.today(),
            'user_id': self.user_reviewer.id,
            'role_id': self.role_reviewer.id,
            'status_role': True,
            'res_model_address_1': 'budget.responsibility.center',
            'first_addressation_id': self.cbo.id
        })

        # Створюємо бюджет
        budget = self.env['budget.plan'].create({
            'name': 'Тестовий бюджет з виконавцями',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id,
            'period_id': self.period.id,
            'responsible_user_id': self.user_creator.id,
            'use_role_based_approval': True,
            'budget_creator_role_id': self.role_creator.id,
            'budget_reviewer_role_id': self.role_reviewer.id,
            'budget_approver_role_id': self.role_approver.id
        })

        # Перевіряємо обчислення виконавців
        self.assertIn(self.user_creator, budget.current_creator_ids)
        self.assertIn(self.user_reviewer, budget.current_reviewer_ids)

    def test_coordination_validation(self):
        """Тест валідації при відправці на узгодження"""
        budget = self.env['budget.plan'].create({
            'name': 'Тестовий бюджет валідації',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id,
            'period_id': self.period.id,
            'responsible_user_id': self.user_creator.id,
            'use_role_based_approval': True,
            'budget_creator_role_id': self.role_creator.id,
            'budget_reviewer_role_id': self.role_reviewer.id,
            'budget_approver_role_id': self.role_approver.id,
            'state': 'planning'
        })

        # Створюємо лінію бюджету
        self.env['budget.plan.line'].create({
            'plan_id': budget.id,
            'name': 'Тестова лінія',
            'planned_amount': 10000
        })

        # Спроба відправки без виконавців ролей повинна викликати помилку
        with self.assertRaises(ValidationError):
            budget.action_send_coordination()

    def test_approval_permissions(self):
        """Тест перевірки прав на затвердження"""
        # Призначаємо виконавця ролі затверджуючого
        self.env['business.role.executor'].create({
            'date': date.today(),
            'user_id': self.user_approver.id,
            'role_id': self.role_approver.id,
            'status_role': True,
            'res_model_address_1': 'budget.responsibility.center',
            'first_addressation_id': self.cbo.id
        })

        budget = self.env['budget.plan'].create({
            'name': 'Тестовий бюджет затвердження',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id,
            'period_id': self.period.id,
            'responsible_user_id': self.user_creator.id,
            'use_role_based_approval': True,
            'budget_approver_role_id': self.role_approver.id,
            'state': 'coordination'
        })

        # Спроба затвердження користувачем без прав
        budget_as_creator = budget.with_user(self.user_creator)
        with self.assertRaises(UserError):
            budget_as_creator.action_approve()

        # Затвердження користувачем з правами
        budget_as_approver = budget.with_user(self.user_approver)
        budget_as_approver.action_approve()

        self.assertEqual(budget.state, 'approved')