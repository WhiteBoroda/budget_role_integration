from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta


class TestBudgetRolePermissions(TransactionCase):
    """Тести прав доступу та безпеки"""

    def setUp(self):
        super().setUp()

        # Створення користувачів різних рівнів
        self.user_basic = self.env['res.users'].create({
            'name': 'Basic User',
            'login': 'basic_user',
            'email': 'basic@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })

        self.user_budget = self.env['res.users'].create({
            'name': 'Budget User',
            'login': 'budget_user',
            'email': 'budget@test.com',
            'groups_id': [(6, 0, [self.env.ref('budget.group_budget_user').id])]
        })

        self.user_manager = self.env['res.users'].create({
            'name': 'Budget Manager',
            'login': 'budget_manager',
            'email': 'manager@test.com',
            'groups_id': [(6, 0, [self.env.ref('budget.group_budget_manager').id])]
        })

        # Створення тестових даних
        self.cbo = self.env['budget.responsibility.center'].create({
            'name': 'ЦБО для тестування прав',
            'code': 'PERMTEST',
            'cbo_type': 'department',
            'budget_level': 'operational'
        })

        self.budget_type = self.env['budget.type'].create({
            'name': 'Тип для тестування прав',
            'code': 'PERMTEST',
            'budget_category': 'administrative'
        })

        self.period = self.env['budget.period'].create({
            'name': 'Період для прав',
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90)
        })

    def test_budget_visibility(self):
        """Тест видимості бюджетів для різних користувачів"""
        # Створюємо бюджет від імені budget_user
        budget = self.env['budget.plan'].with_user(self.user_budget).create({
            'name': 'Бюджет для тестування видимості',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id,
            'period_id': self.period.id,
            'responsible_user_id': self.user_budget.id
        })

        # Користувач може бачити свій бюджет
        budget_as_creator = self.env['budget.plan'].with_user(self.user_budget).search([
            ('id', '=', budget.id)
        ])
        self.assertEqual(len(budget_as_creator), 1)

        # Інший базовий користувач не може бачити чужий бюджет
        budget_as_other = self.env['budget.plan'].with_user(self.user_basic).search([
            ('id', '=', budget.id)
        ])
        self.assertEqual(len(budget_as_other), 0)

        # Менеджер може бачити всі бюджети
        budget_as_manager = self.env['budget.plan'].with_user(self.user_manager).search([
            ('id', '=', budget.id)
        ])
        self.assertEqual(len(budget_as_manager), 1)

    def test_role_mapping_permissions(self):
        """Тест прав доступу до налаштувань ролей"""
        # Звичайний користувач не може створювати налаштування
        with self.assertRaises(Exception):
            self.env['budget.role.mapping'].with_user(self.user_budget).create({
                'name': 'Неавторизоване налаштування',
                'sequence': 999
            })

        # Менеджер може створювати налаштування
        mapping = self.env['budget.role.mapping'].with_user(self.user_manager).create({
            'name': 'Авторизоване налаштування',
            'sequence': 100
        })

        self.assertEqual(mapping.name, 'Авторизоване налаштування')

    def test_role_substitution_integration(self):
        """Тест інтеграції з заміщенням ролей"""
        # Створюємо ролі та їх виконавців
        role = self.env['business.role.catalog'].create({
            'role': 'Роль для заміщення',
            'addressed': True,
            'personified': True
        })

        # Основний виконавець
        main_executor = self.env['business.role.executor'].create({
            'date': date.today() - timedelta(days=10),
            'user_id': self.user_budget.id,
            'role_id': role.id,
            'status_role': True,
            'res_model_address_1': 'budget.responsibility.center',
            'first_addressation_id': self.cbo.id
        })

        # Заміщення
        substitution = self.env['business.role.substitution'].create({
            'registration_number': 'TEST-SUB-001',
            'replaceable_person_id': self.user_budget.id,
            'reason': 'vacation',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=7)
        })

        # Лінія заміщення
        sub_line = self.env['business.role.substitution.lines'].create({
            'task_id': substitution.id,
            'substitute_id': self.user_manager.id,
            'role_id': role.id,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=7),
            'res_model_address_1': 'budget.responsibility.center',
            'first_addressation_id': self.cbo.id
        })

        # Активуємо заміщення
        substitution.action_lifecycle_state__activate_add_in_executor()

        # Створюємо бюджет
        budget = self.env['budget.plan'].create({
            'name': 'Бюджет з заміщенням',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id,
            'period_id': self.period.id,
            'responsible_user_id': self.user_budget.id,
            'use_role_based_approval': True,
            'budget_approver_role_id': role.id
        })

        # Перевіряємо, що заступник став виконавцем ролі
        self.assertIn(self.user_manager, budget.current_approver_ids)