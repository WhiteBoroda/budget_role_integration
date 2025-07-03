# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class BudgetRolePortal(CustomerPortal):
    # Портал для роботи з ролями в бюджетуванні

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        # Додаємо лічильники для бюджетів з ролями
        if 'budget_count' in counters:
            partner = request.env.user.partner_id

            # Бюджети де користувач є виконавцем ролі
            budget_role_count = request.env['budget.plan'].search_count([
                '|', '|',
                ('current_creator_ids', 'in', [request.env.user.id]),
                ('current_reviewer_ids', 'in', [request.env.user.id]),
                ('current_approver_ids', 'in', [request.env.user.id])
            ])

            values['budget_role_count'] = budget_role_count

        return values

    @http.route(['/my/budget_roles'], type='http', auth="user", website=True)
    def portal_my_budget_roles(self, **kw):
        # Сторінка з бюджетами користувача

        # Отримуємо бюджети де користувач має ролі
        budgets = request.env['budget.plan'].search([
            '|', '|',
            ('current_creator_ids', 'in', [request.env.user.id]),
            ('current_reviewer_ids', 'in', [request.env.user.id]),
            ('current_approver_ids', 'in', [request.env.user.id])
        ])

        values = {
            'budgets': budgets,
            'page_name': 'budget_roles',
            'default_url': '/my/budget_roles',
        }

        return request.render("budget_role_integration.portal_my_budget_roles", values)

    @http.route(['/my/budget_roles/<int:budget_id>'], type='http', auth="user", website=True)
    def portal_budget_role_detail(self, budget_id, **kw):
        # Детальна сторінка бюджету з інформацією про ролі

        budget = request.env['budget.plan'].browse(budget_id)

        # Перевіряємо доступ
        if not budget.exists() or request.env.user not in (
                budget.current_creator_ids |
                budget.current_reviewer_ids |
                budget.current_approver_ids
        ):
            return request.redirect('/my')

        # Визначаємо ролі користувача
        user_roles = []
        if request.env.user in budget.current_creator_ids:
            user_roles.append('Складач бюджету')
        if request.env.user in budget.current_reviewer_ids:
            user_roles.append('Перевіряючий бюджету')
        if request.env.user in budget.current_approver_ids:
            user_roles.append('Затверджуючий бюджету')

        values = {
            'budget': budget,
            'user_roles': user_roles,
            'page_name': 'budget_role_detail',
        }

        return request.render("budget_role_integration.portal_budget_role_detail", values)