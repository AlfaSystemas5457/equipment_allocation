from odoo import models, fields, api


class Equipment(models.Model):
    _inherit = 'maintenance.equipment'

    employee_ids = fields.Many2many('hr.employee', string='Empleados')
