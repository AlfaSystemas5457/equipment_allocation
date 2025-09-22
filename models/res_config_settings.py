# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EquipmentSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_return_emails = fields.Boolean(
        'Enviar correos de recordatorio de devolución',
        config_parameter='equipment_allocation.enable_return_emails'
    )


class UsersSettings(models.Model):
    _inherit = 'res.users'

    access_scope_equipment = fields.Boolean(
        'Acceso a todas las opciones de asignaciones de equipos', default=False,
        help='Permite al usuario ver y gestionar todas las asignaciones de equipos sin restricciones.')

    def _update_groups_based_on_scope(self, access_scope=False):
        group_equipment_replacement = self.env.ref(
            'equipment_allocation.group_equipment_replacement_access', raise_if_not_found=False)
        group_equipment_allocations = self.env.ref(
            'equipment_allocation.group_equipment_allocations_access', raise_if_not_found=False)

        for user in self:
            if not group_equipment_replacement or not group_equipment_allocations:
                continue

            if access_scope:
                user.group_ids = user.group_ids | group_equipment_allocations | group_equipment_replacement
            else:
                user.group_ids = user.group_ids - \
                    group_equipment_replacement - group_equipment_allocations

    def write(self, vals):
        if 'access_scope_equipment' in vals:
            self._update_groups_based_on_scope(vals['access_scope_equipment'])
        return super().write(vals)

    def create(self, vals_list):
        if 'access_scope_equipment' in vals_list:
            self._update_groups_based_on_scope(
                vals_list['access_scope_equipment'])
        return super().create(vals_list)
