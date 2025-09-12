from odoo import models, fields, api

class EquipmentReturnWizard(models.TransientModel):
    _name = 'equipment.return.wizard'
    _description = 'Asistente para devolución de equipo'

    allocation_id = fields.Many2one('equipment.allocations', string="Asignación", required=True)
    return_description = fields.Html(string="Descripción del estado del equipo", required=True)

    def confirm_return(self):
        self.ensure_one()
        self.allocation_id.return_description = self.return_description
        self.allocation_id.handle_returned()
        
        action = self.allocation_id.handle_create_report()
        
        if isinstance(action, dict):
            action.update({'close_on_report_download': True})
        return action
