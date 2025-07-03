# -*- coding: utf-8 -*-

# Імпорт всіх моделей модуля budget_role_integration

# Основні моделі
from . import budget_plan_roles           # Розширення budget.plan з ролями
from . import budget_role_mapping         # Налаштування зопоставлення ролей
from . import budget_plan_roles_enhanced  # Додаткові методи для ролей

# Допоміжні моделі
from . import budget_role_template        # Шаблони ролей
from . import budget_role_utils           # Утиліти для роботи з ролями
from . import budget_role_validators      # Валідатори ролей
from . import budget_role_notifications   # Сповіщення про ролі