# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EquipmentEmployees(models.Model):
    _inherit = 'hr.employee'

    equipment_ids_allocated = fields.Many2one(
        'maintenance.equipment', string='Equipos')
    equipment_count_total = fields.Integer(
        'Número de equipos', compute='_compute_equipment_count', groups="hr.group_hr_user")

    @api.depends('equipment_ids')
    def _compute_equipment_count(self):
        for employee in self:
            employee.equipment_count_total = len(
                employee.equipment_ids_allocated.search(
                    [
                        ('employee_ids', 'in', self.id)
                    ]
                ))
