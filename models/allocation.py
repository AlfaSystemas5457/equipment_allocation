# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta


class Allocations(models.Model):
    _name = 'equipment.allocations'
    _description = 'Asiganción de equipo'
    _inherit = ['mail.thread']

    name = fields.Char('Nombre', tracking=True, required=True)
    uid = fields.Char('UID', readonly=True, copy=False, index=True)

    employee_ids = fields.Many2many(
        'hr.employee', string='Empleados', tracking=True, required=True)
    equipment_ids = fields.Many2many(
        'maintenance.equipment',
        'equipment_allocations_rel',
        'allocation_id',
        'equipment_id',
        string='Equipos',
        tracking=True,
        domain="[('employee_ids', '=', False)]",
        required=True
    )

    before_equipment_ids = fields.Many2many(
        'maintenance.equipment',
        'equipment_allocations_before_rel',
        'allocation_id',
        'equipment_id',
        string='Equipos anteriores',
        tracking=True
    )

    allocation_type = fields.Selection(
        [
            ('on_demand', 'Bajo demanda'),
            ('permantent', 'Permanente'),
        ], string='Tipo de asignación', tracking=True, default='on_demand'
    )
    request_date = fields.Date(
        'Fecha de solicitud', tracking=True, default=date.today())
    allocation_date = fields.Date('Fecha de asignación', tracking=True)
    return_date = fields.Date('Fecha prevista de devolución', tracking=True)
    real_return_date = fields.Date('Fecha de devolución', tracking=True)
    duration = fields.Integer(
        "Duración", tracking=True, default=1, required=True)
    duration_type = fields.Selection(
        [
            ('day', 'Dias'),
            ('week', 'Semanas'),
            ('month', 'Meses'),
            ('year', 'Años')
        ], default="month", tracking=True, required=True, string='Tipo de duración'
    )

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

    has_replacement = fields.Boolean(
        'Reemplazo?', default=False, tracking=True)

    @api.model
    def create(self, vals):
        if not vals.get('uid'):
            vals['uid'] = self.env['ir.sequence'].next_by_code(
                'equipment.allocations') or '/'
        return super(Allocations, self).create(vals)

    @api.onchange('duration', 'duration_type')
    def update_return_date(self):
        if self.allocation_type == 'on_demand' and self.allocation_date:
            if self.duration_type == 'year':
                self.return_date = self.allocation_date + relativedelta(years=+self.duration) - \
                    relativedelta(days=1)
            elif self.duration_type == 'month':
                self.return_date = self.allocation_date + relativedelta(months=+self.duration) - \
                    relativedelta(days=1)
            elif self.duration_type == 'week':
                self.return_date = self.allocation_date + relativedelta(weeks=+self.duration) - \
                    relativedelta(days=1)
            elif self.duration_type == 'day':
                self.return_date = self.allocation_date + relativedelta(days=+self.duration) - \
                    relativedelta(days=1)

    def handle_create_report(self):
        return self.env.ref('equipment_allocation.report_template_id').report_action(self)

    def handle_allocated(self):
        self.ensure_one()

        self.allocation_date = date.today()

        if self.allocation_type == 'on_demand':
            delta = relativedelta()
            if self.duration_type == 'year':
                delta = relativedelta(years=self.duration)
            elif self.duration_type == 'month':
                delta = relativedelta(months=self.duration)
            elif self.duration_type == 'week':
                delta = relativedelta(weeks=self.duration)
            elif self.duration_type == 'day':
                delta = relativedelta(days=self.duration)

            self.return_date = self.allocation_date + \
                delta - relativedelta(days=1)

        ids = [data.id for data in self.equipment_ids]
        equipment_ids = self.env['maintenance.equipment'].search(
            [
                ('id', 'in', ids)
            ]
        )

        for employee in equipment_ids:
            employee.employee_ids = self.employee_ids

        self.state = 'allocated'

    def handle_returned(self):
        self.real_return_date = date.today()

        ids = [data.id for data in self.equipment_ids]
        equipment_ids = self.env['maintenance.equipment'].search(
            [
                ('id', 'in', ids)
            ]
        )

        for equipment_line in equipment_ids:
            equipment_line.employee_ids = [(5, 0, 0)]

        if self.has_replacement:
            replacement = self.env['equipment.replacement'].search(
                [
                    ('uid_replacement', '=', self.id)
                ], limit=1
            )
            replacement.write(
                {
                    'state': 'returned'
                }
            )

        self.state = 'returned'

    def handle_rejected(self):
        ids = [data.id for data in self.equipment_ids]
        equipment_ids = self.env['maintenance.equipment'].search(
            [
                ('id', 'in', ids)
            ]
        )

        for equipment_line in equipment_ids:
            equipment_line.employee_ids = [(5, 0, 0)]

        self.state = 'rejected'

    def handle_draft(self):
        self.real_return_date = False
        self.state = 'draft'
