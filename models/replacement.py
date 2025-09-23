# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import date


class Replacement(models.Model):
    _name = 'equipment.replacement'
    _description = 'Reemplazo de equipo'
    _inherit = ['mail.thread']
    _order = 'uid DESC'

    name = fields.Char('Nombre', track_visibility='onchange', track_sequence=2, required=True)
    uid = fields.Char('UID', readonly=True, copy=False, index=True)
    uid_replacement = fields.Many2one(
        'equipment.allocations',
        string='UID para reemplazar',
        track_visibility='onchange', track_sequence=2,
        required=True,
        domain="[('state', 'not in', ['draft', 'rejected', 'returned']), ('has_replacement', '=', False)]"
    )

    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', track_visibility='onchange', track_sequence=2, required=True)
    equipment_ids = fields.Many2many(
        'maintenance.equipment', string='Equipos', track_visibility='onchange', track_sequence=2, domain="[('employee_id', '=', False)]", required=True)

    allocation_type = fields.Selection(
        [
            ('on_demand', 'Bajo demanda'),
            ('permantent', 'Permanente'),
        ], string='Tipo de asignación', track_visibility='onchange', track_sequence=2, default='on_demand'
    )
    request_date = fields.Date(
        'Fecha de solicitud', track_visibility='onchange', track_sequence=2, default=lambda self: date.today())

    area = fields.Many2one('equipment.area', string='Area',
                           track_visibility='onchange', track_sequence=2, required=True)
    description = fields.Html(string='Descripción')
    state = fields.Selection(
        [
            ('draft', 'Nuevo'),
            ('allocated', 'Asignado'),
            ('rejected', 'Rechazado'),
            ('returned', 'Devuelto')
        ],
        default='draft', track_visibility='onchange', track_sequence=2, required=True, string='Estado'
    )

    @api.model
    def create(self, vals_list):
        if not vals_list.get('uid'):
            vals_list['uid'] = self.env['ir.sequence'].next_by_code(
                'equipment.replacement') or '/'

        if vals_list.get('uid_replacement'):
            allocation = self.env['equipment.allocations'].browse(
                vals_list['uid_replacement'])
            if allocation:
                vals_list.setdefault('area', allocation.area.id)
                vals_list.setdefault('employee_id', allocation.employee_id.id)
                vals_list.setdefault('equipment_ids', [
                                (6, 0, allocation.equipment_ids.ids)])
                vals_list.setdefault('allocation_type', allocation.allocation_type)
                vals_list.setdefault('name', allocation.name)

        return super(Replacement, self).create(vals_list)

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
        
        if self.uid_replacement.state != 'allocated':
            raise exceptions.UserError("No se ha asignado ningún equipo.")

        allocations = self.env['equipment.allocations'].search(
            [
                ('uid', '=', self.uid_replacement.uid)
            ], limit=1
        )

        allocations.has_replacement = True
        allocations.before_equipment_ids = allocations.equipment_ids
        
        filtered_equipment = allocations.equipment_ids.filtered(lambda x: x.employee_id.id == self.employee_id.id)

        ids = [data.id for data in filtered_equipment]
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
        
        errors = []
        for employee_equipment in equipment_ids:
            if employee_equipment.employee_id:
                errors.append(f"El equipo {employee_equipment.display_name}, ya esta asignado.")
            employee_equipment.employee_id = self.employee_id
        
        if errors:
            raise exceptions.UserError("\n".join(errors))

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
