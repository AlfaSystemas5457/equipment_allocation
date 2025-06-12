# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import date


class Replacement(models.Model):
    _name = 'equipment.replacement'
    _description = 'Reemplazo de equipo'
    _inherit = ['mail.thread']

    name = fields.Char('Nombre', tracking=True, required=True)
    uid = fields.Char('UID', readonly=True, copy=False, index=True)
    uid_replacement = fields.Many2one(
        'equipment.allocations',
        string='UID para reemplazar',
        tracking=True,
        required=True,
        domain="[('state', 'not in', ['rejected', 'returned']), ('has_replacement', '=', False)]"
    )

    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', tracking=True, required=True)
    equipment_ids = fields.Many2many(
        'maintenance.equipment', string='Equipos', tracking=True, domain="[('employee_id', '=', False)]", required=True)

    allocation_type = fields.Selection(
        [
            ('on_demand', 'Bajo demanda'),
            ('permantent', 'Permanente'),
        ], string='Tipo de asignación', tracking=True, default='on_demand'
    )
    request_date = fields.Date(
        'Fecha de solicitud', tracking=True, default=date.today())

    area = fields.Many2one('equipment.area', string='Area',
                           tracking=True, required=True)
    description = fields.Text(string='Descripción')
    state = fields.Selection(
        [
            ('draft', 'Nuevo'),
            ('allocated', 'Asignado'),
            ('rejected', 'Rechazado'),
            ('returned', 'Devuelto')
        ],
        default='draft', tracking=True, required=True, string='Estado'
    )

    @api.model
    def create(self, vals):
        if not vals.get('uid'):
            vals['uid'] = self.env['ir.sequence'].next_by_code(
                'equipment.replacement') or '/'

        if vals.get('uid_replacement'):
            allocation = self.env['equipment.allocations'].browse(
                vals['uid_replacement'])
            if allocation:
                vals.setdefault('area', allocation.area.id)
                vals.setdefault('employee_id', allocation.employee_id.id)
                vals.setdefault('equipment_ids', [
                                (6, 0, allocation.equipment_ids.ids)])
                vals.setdefault('allocation_type', allocation.allocation_type)
                vals.setdefault('name', allocation.name)

        return super(Replacement, self).create(vals)

    def write(self, vals):
        result = super(Replacement, self).write(vals)

        if 'uid_replacement' in vals:
            for record in self:
                allocation = record.uid_replacement

                if allocation:
                    if not record.name:
                        record.name = allocation.name

                    if not record.area:
                        record.area = allocation.area

                    if not record.employee_id:
                        record.employee_id = allocation.employee_id.id

                    if not record.equipment_ids:
                        record.equipment_ids = [
                            (6, 0, allocation.equipment_ids.ids)]

                    if not record.allocation_type:
                        record.allocation_type = allocation.allocation_type

        return result

    def unlink(self):
        raise exceptions.UserError("No está permitido eliminar registros.")

    @api.onchange('uid_replacement')
    def adding_data(self):
        if not self.uid_replacement:
            return

        allocation = self.env['equipment.allocations'].search(
            [
                ('uid', '=', self.uid_replacement.uid)
            ], limit=1
        )

        self.name = allocation.name
        self.allocation_type = allocation.allocation_type
        self.area = allocation.area
        self.employee_id = allocation.employee_id
        self.equipment_ids = allocation.equipment_ids

    def handle_allocated(self):
        self.ensure_one()

        allocations = self.env['equipment.allocations'].search(
            [
                ('uid', '=', self.uid_replacement.uid)
            ], limit=1
        )

        allocations.has_replacement = True
        allocations.before_equipment_ids = allocations.equipment_ids

        ids = [data.id for data in allocations.equipment_ids]
        equipment_ids = self.env['maintenance.equipment'].search(
            [
                ('id', 'in', ids)
            ]
        )

        for equipment_line in equipment_ids:
            equipment_line.employee_id = False

        allocations.equipment_ids = self.equipment_ids

        ids = [data.id for data in self.equipment_ids]
        equipment_ids = self.env['maintenance.equipment'].search(
            [
                ('id', 'in', ids)
            ]
        )

        for employee in equipment_ids:
            employee.employee_id = self.employee_id

        self.state = 'allocated'

    def handle_rejected(self):
        replacement = self.env['equipment.allocations'].search(
            [
                ('uid', '=', self.uid_replacement.uid)
            ], limit=1
        )

        # posible bug
        if replacement:
            replacement.write({
                'has_replacement': False
            })
            replacement.equipment_ids = replacement.before_equipment_ids

        self.state = 'rejected'

    def handle_draft(self):
        self.state = 'draft'
