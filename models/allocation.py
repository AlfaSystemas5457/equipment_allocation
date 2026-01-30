# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class Allocations(models.Model):
    _name = "equipment.allocations"
    _description = "Asiganción de equipo"
    _inherit = ["mail.thread"]
    _order = "uid DESC"
    _rec_name = "uid"

    uid = fields.Char("UID", readonly=True, copy=False, index=True)

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        tracking=True,
        required=True,
        ondelete="restrict",
    )
    equipment_ids = fields.Many2many(
        "maintenance.equipment",
        "equipment_allocations_rel",
        "allocation_id",
        "equipment_id",
        string="Equipos",
        tracking=True,
        domain="[('employee_id', '=', False)]",
        required=True,
        ondelete="restrict",
    )

    before_equipment_ids = fields.Many2many(
        "maintenance.equipment",
        "equipment_allocations_before_rel",
        "allocation_id",
        "equipment_id",
        string="Equipos anteriores",
        tracking=True,
        ondelete="restrict",
    )

    allocation_type = fields.Selection(
        [
            ("on_demand", "Bajo demanda"),
            ("permantent", "Permanente"),
        ],
        string="Tipo de asignación",
        tracking=True,
        default="on_demand",
    )
    request_date = fields.Date(
        "Fecha de solicitud", tracking=True, default=lambda self: date.today()
    )
    allocation_date = fields.Date("Fecha de asignación", tracking=True)
    return_date = fields.Date("Fecha prevista de devolución", tracking=True)
    real_return_date = fields.Date("Fecha de devolución", tracking=True)
    duration = fields.Integer("Duración", tracking=True, default=1, required=True)
    duration_type = fields.Selection(
        [("day", "Dias"), ("week", "Semanas"), ("month", "Meses"), ("year", "Años")],
        default="month",
        tracking=True,
        required=True,
        string="Tipo de duración",
    )

    area = fields.Many2one(
        "equipment.area", string="Area", tracking=True, required=True
    )
    description = fields.Html(string="Descripción")
    return_description = fields.Html(string="Descripción de devolución")
    state = fields.Selection(
        [
            ("draft", "Nuevo"),
            ("allocated", "Asignado"),
            ("rejected", "Rechazado"),
            ("returned", "Devuelto"),
        ],
        default="draft",
        tracking=True,
        required=True,
        string="Estado",
    )

    has_replacement = fields.Boolean("Reemplazo?", default=False, tracking=True)

    def copy(self, default=None):
        default = default or {}
        default["state"] = f"draft"
        default["has_replacement"] = False
        default["before_equipment_ids"] = False
        return super(Allocations, self).copy(default)

    def create(self, vals_list):
        if not vals_list.get("uid"):
            vals_list["uid"] = (
                self.env["ir.sequence"].next_by_code("equipment.allocations") or "/"
            )
        return super(Allocations, self).create(vals_list)

    def unlink(self):
        raise exceptions.UserError("No está permitido eliminar registros.")

    def _notify_upcoming_returns(self):
        send_emails = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("equipment_allocation.enable_return_emails")
        )

        today = date.today()
        notify_days = 3
        target_date = today + timedelta(days=notify_days)

        records = self.search(
            [("return_date", "=", target_date), ("state", "=", "allocated")]
        )

        template = self.env.ref(
            "equipment_allocation.mail_template_equipment_return_reminder"
        )

        for record in records:
            if template:
                try:
                    if send_emails and record.employee_id.work_email:
                        template.send_mail(
                            record.id, force_send=True, raise_exception=True
                        )
                    else:
                        record.message_post(
                            body="Recordatorio: debe devolver sus equipos asignados.",
                            subject="🔔 Recordatorio de Devolución",
                            message_type="comment",
                        )
                        _logger.info(
                            f"Internal notification sent to {record.uid} (withoout email)"
                        )

                except Exception as e:
                    _logger.error(
                        f"Error sending email for registration {record.uid}: {str(e)}"
                    )

    @api.depends("duration", "duration_type")
    def update_return_date(self):
        if self.allocation_type == "on_demand" and self.allocation_date:
            if self.duration_type == "year":
                self.return_date = (
                    self.allocation_date
                    + relativedelta(years=+self.duration)
                    - relativedelta(days=1)
                )
            elif self.duration_type == "month":
                self.return_date = (
                    self.allocation_date
                    + relativedelta(months=+self.duration)
                    - relativedelta(days=1)
                )
            elif self.duration_type == "week":
                self.return_date = (
                    self.allocation_date
                    + relativedelta(weeks=+self.duration)
                    - relativedelta(days=1)
                )
            elif self.duration_type == "day":
                self.return_date = (
                    self.allocation_date
                    + relativedelta(days=+self.duration)
                    - relativedelta(days=1)
                )

    def open_return_wizard(self):
        self.ensure_one()
        return {
            "name": "Devolución de Equipos",
            "type": "ir.actions.act_window",
            "res_model": "equipment.return.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_allocation_id": self.id},
        }

    def handle_create_report(self):
        return self.env.ref("equipment_allocation.report_template_id").report_action(
            self
        )

    def handle_allocated(self):
        self.ensure_one()

        self.allocation_date = date.today()

        if self.allocation_type == "on_demand":
            delta = relativedelta()
            if self.duration_type == "year":
                delta = relativedelta(years=self.duration)
            elif self.duration_type == "month":
                delta = relativedelta(months=self.duration)
            elif self.duration_type == "week":
                delta = relativedelta(weeks=self.duration)
            elif self.duration_type == "day":
                delta = relativedelta(days=self.duration)

            self.return_date = self.allocation_date + delta - relativedelta(days=1)

        ids = [data.id for data in self.equipment_ids]
        equipment_ids = self.env["maintenance.equipment"].search([("id", "in", ids)])

        errors = []
        for equipment_line in equipment_ids:
            if equipment_line.employee_id:
                errors.append(
                    f"El equipo {equipment_line.display_name}, ya esta asignado."
                )
            equipment_line.employee_id = self.employee_id

        if errors:
            raise exceptions.UserError("\n".join(errors))

        self.state = "allocated"

    def handle_returned(self):
        self.real_return_date = date.today()

        ids = [data.id for data in self.equipment_ids]
        equipment_ids = self.env["maintenance.equipment"].search([("id", "in", ids)])

        for equipment_line in equipment_ids:
            equipment_line.employee_id = False

        if self.has_replacement:
            replacement = self.env["equipment.replacement"].search(
                [("uid_replacement", "=", self.id)], limit=1
            )
            replacement.write({"state": "returned"})

        self.state = "returned"

    def handle_rejected(self):
        ids = [data.id for data in self.equipment_ids]
        equipment_ids = self.env["maintenance.equipment"].search([("id", "in", ids)])

        for equipment_line in equipment_ids:
            if equipment_line.employee_id.id == self.employee_id.id:
                equipment_line.employee_id = False

        self.state = "rejected"

    def handle_draft(self):
        ids = [data.id for data in self.equipment_ids]
        equipment_ids = self.env["maintenance.equipment"].search([("id", "in", ids)])

        for equipment_line in equipment_ids:
            if equipment_line.employee_id.id == self.employee_id.id:
                equipment_line.employee_id = False

        self.real_return_date = False
        self.state = "draft"
