from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestBudgetRoleMapping(TransactionCase):
    """Тести налаштувань зопоставлення ролей"""

    def setUp(self):
        super().setUp()

        # Створення тестових даних
        self.role_creator = self.env['business.role.catalog'].create({
            'role': 'Створювач тестових бюджетів',
            'addressed': True,
            'personified': True
        })

        self.budget_type = self.env['budget.type'].create({
            'name': 'Тестовий тип для маппінгу',
            'code': 'TESTMAP',
            'budget_category': 'administrative'
        })

        self.cbo = self.env['budget.responsibility.center'].create({
            'name': 'ЦБО для маппінгу',
            'code': 'MAPTEST',
            'cbo_type': 'department',
            'budget_level': 'operational'
        })

    def test_mapping_creation(self):
        """Тест створення налаштувань зопоставлення"""
        mapping = self.env['budget.role.mapping'].create({
            'name': 'Тестове зопоставлення',
            'budget_type_id': self.budget_type.id,
            'cbo_type': 'department',
            'budget_level': 'operational',
            'budget_creator_role_id': self.role_creator.id,
            'sequence': 10
        })

        self.assertEqual(mapping.name, 'Тестове зопоставлення')
        self.assertEqual(mapping.budget_creator_role_id, self.role_creator)

    def test_mapping_search(self):
        """Тест пошуку налаштувань для бюджету"""
        # Створюємо налаштування
        mapping = self.env['budget.role.mapping'].create({
            'name': 'Маппінг для пошуку',
            'budget_type_id': self.budget_type.id,
            'cbo_type': 'department',
            'budget_level': 'operational',
            'budget_creator_role_id': self.role_creator.id,
            'sequence': 20
        })

        # Створюємо бюджет
        budget = self.env['budget.plan'].create({
            'name': 'Бюджет для тестування маппінгу',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id,
            'budget_level': 'operational'
        })

        # Тестуємо пошук ролей
        roles = self.env['budget.role.mapping'].get_roles_for_budget(budget)

        self.assertEqual(roles.get('budget_creator_role_id'), self.role_creator.id)

    def test_auto_assign_roles(self):
        """Тест автоматичного призначення ролей"""
        # Створюємо налаштування
        self.env['budget.role.mapping'].create({
            'name': 'Автопризначення',
            'budget_type_id': self.budget_type.id,
            'cbo_type': 'department',
            'budget_creator_role_id': self.role_creator.id,
            'sequence': 30
        })

        # Створюємо бюджет
        budget = self.env['budget.plan'].create({
            'name': 'Бюджет автопризначення',
            'cbo_id': self.cbo.id,
            'budget_type_id': self.budget_type.id
        })

        # Виконуємо автопризначення
        result = budget.action_auto_assign_roles()

        # Перевіряємо результат
        self.assertEqual(budget.budget_creator_role_id, self.role_creator)
        self.assertTrue(budget.use_role_based_approval)