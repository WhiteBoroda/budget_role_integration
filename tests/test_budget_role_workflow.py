from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta

class TestBudgetRoleWorkflow(TransactionCase):
    """Тест повного робочого процесу з ролями"""

    def setUp(self):
        super().setUp()

        # Повне налаштування тестового середовища
        self.setup_users()
        self.setup_roles()
        self.setup_structure()
        self.setup_budget_data()

    def setup_users(self):
        """Налаштування користувачів"""
        self.creator = self.env['res.users'].create({
            'name': 'Workflow Creator',
            'login': 'wf_creator',
            'email': 'creator@workflow.com',
            'groups_id': [(6, 0, [self.env.ref('budget.group_budget_user').id])]
        })

        self.reviewer = self.env['res.users'].create({
            'name': 'Workflow Reviewer',
            'login': 'wf_reviewer',
            'email': 'reviewer@workflow.com',
            'groups_id': [(6, 0, [self.env.ref('budget.group_budget_user').id])]
        })

        self.approver = self.env['res.users'].create({
            'name': 'Workflow Approver',
            'login': 'wf_approver',
            'email': 'approver@workflow.com',
            'groups_id': [(6, 0, [self.env.ref('budget.group_budget_manager').id])]
        })

    def setup_roles(self):
        """Налаштування ролей"""
        self.role_creator = self.env['business.role.catalog'].create({
            'role': 'Workflow Creator Role',
            'addressed': True,
            'personified': True
        })

        self.role_reviewer = self.env['business.role.catalog'].create({
            'role': 'Workflow Reviewer Role',
            'addressed': True,
            'personified': True
        })

        self.role_approver = self.env['business.role.catalog'].create({
            'role': 'Workflow Approver Role',
            'addressed': True,
            'personified': True
        })

    def setup_structure(self):
        """Налаштування організаційної структури"""
        self.cbo = self.env['budget.responsibility.center'].create({
            'name': 'Workflow ЦБО',
            'code': 'WF',
            'cbo_type': 'department',
            'budget_level': 'operational'
        })

        self.budget_type = self.env['budget.type'].create({
            'name': 'Workflow Budget Type',
            'code': 'WF',
            'budget_category': 'administrative'
        })

        self.period = self.env['budget.period'].create({
            'name': 'Workflow Period',
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90)
        })

    def setup_budget_data(self):
        """Налаштування бюджетних даних"""
        # Призначення виконавців ролей
        today = date.today()

        self.env['business.role.executor'].create({
            'date': today,
            'user_id': self.creator.id,
            'role_id': self.role_creator.id,
            'status_role': True,
            'res_model_address_1': 'budget.responsibility.center',
            'first_addressation_id': self.cbo.id
        })

        self.env['business.role.executor'].create({
            'date': today,
            'user_id': self.reviewer.id,
            'role_id': self.role_reviewer.id,
            'status_role': True,
            'res_model_address_1': 'budget.responsibility.center',
            'first_addressation_id': self.cbo.id
        })

        self.env['business.role.executor'].create({
            'date': today,
            'user_id': self.approver.id,
            'role_id': self.role_approver.id,
            'status_role': True,
            'res_model_address_1': 'budget.responsibility.center',
            'first_addressation_id': self.cbo.id
        })

    def test_full_workflow(self):
        """Тест повного робочого процесу"""
        # 1. Створення бюджету складачем
        budget = self.env['budget.plan'].with_user(self.creator).create({
            'name': 'Workflow Test Budget',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id,
            'period_id': self.period.id,
            'responsible_user_id': self.creator.id,
            'use_role_based_approval': True,
            'budget_creator_role_id': self.role_creator.id,
            'budget_reviewer_role_id': self.role_reviewer.id,
            'budget_approver_role_id': self.role_approver.id
        })

        # Додаємо лінію бюджету
        self.env['budget.plan.line'].create({
            'plan_id': budget.id,
            'name': 'Workflow Test Line',
            'planned_amount': 50000
        })

        # 2. Початок планування
        budget.with_user(self.creator).action_start_planning()
        self.assertEqual(budget.state, 'planning')

        # 3. Відправка на узгодження
        budget.with_user(self.creator).action_send_coordination()
        self.assertEqual(budget.state, 'coordination')

        # 4. Спроба затвердження перевіряючим (повинна пройти)
        budget.with_user(self.approver).action_approve()
        self.assertEqual(budget.state, 'approved')

        # Перевіряємо, що призначено затверджуючого
        self.assertEqual(budget.approved_by_id, self.approver)
        self.assertTrue(budget.approval_date)

    def test_revision_workflow(self):
        """Тест процесу доопрацювання"""
        # Створюємо бюджет на узгодженні
        budget = self.env['budget.plan'].create({
            'name': 'Revision Test Budget',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id,
            'period_id': self.period.id,
            'responsible_user_id': self.creator.id,
            'use_role_based_approval': True,
            'budget_reviewer_role_id': self.role_reviewer.id,
            'budget_approver_role_id': self.role_approver.id,
            'state': 'coordination'
        })

        # Додаємо лінію
        self.env['budget.plan.line'].create({
            'plan_id': budget.id,
            'name': 'Revision Test Line',
            'planned_amount': 25000
        })

        # Відправка на доопрацювання затверджуючим
        budget.with_user(self.approver).action_request_revision()
        self.assertEqual(budget.state, 'revision')

        # Повторна відправка на узгодження після доопрацювання
        budget.with_user(self.creator).action_send_coordination()
        self.assertEqual(budget.state, 'coordination')

        # Затвердження
        budget.with_user(self.approver).action_approve()
        self.assertEqual(budget.state, 'approved')