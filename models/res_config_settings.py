# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EquipmentSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enable_return_emails = fields.Boolean(
        "Enviar correos de recordatorio de devolución",
        config_parameter="equipment_allocation.enable_return_emails",
    )


class UsersSettings(models.Model):
    _inherit = "res.users"

    access_scope_equipment = fields.Boolean(
        "Acceso a todas las opciones de asignaciones de equipos",
        default=False,
        help="Permite al usuario ver y gestionar todas las asignaciones de equipos sin restricciones.",
    )

    def _update_groups_based_on_scope_equipment(self):
        group_rep = self.env.ref(
            "equipment_allocation.group_equipment_replacement_access", False
        )
        group_all = self.env.ref(
            "equipment_allocation.group_equipment_allocations_access", False
        )

        if not group_rep or not group_all:
            return

        for user in self:
            if user.access_scope_equipment:
                user.group_ids = user.group_ids | group_rep | group_all
            else:
                user.group_ids = user.group_ids - group_rep - group_all

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._update_groups_based_on_scope_equipment()
        return users

    def write(self, vals):
        res = super().write(vals)

        if "access_scope_equipment" in vals:
            self._update_groups_based_on_scope_equipment()
        return res
