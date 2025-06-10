# -*- coding: utf-8 -*-

from odoo import models, fields


class EquipmentSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_return_emails = fields.Boolean(
        'Enviar correos de recordatorio de devolución',
        config_parameter='equipment_allocation.enable_return_emails'
    )
