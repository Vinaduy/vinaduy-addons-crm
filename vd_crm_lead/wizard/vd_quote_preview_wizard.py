"""Wizard popup TO ĐÙNG để xem trước file báo giá PDF inline.
Dùng widget pdf_viewer (PDF.js của Odoo) để embed PDF ngay trong modal,
không cần mở tab mới."""

from odoo import fields, models


class VdQuotePreviewWizard(models.TransientModel):
    _name = 'vd.quote.preview.wizard'
    _description = 'Wizard preview PDF báo giá'

    lead_id = fields.Many2one('crm.lead', required=True)
    pdf_data = fields.Binary(string='File báo giá PDF', attachment=True)
    pdf_name = fields.Char(default='preview_baogia.pdf')
