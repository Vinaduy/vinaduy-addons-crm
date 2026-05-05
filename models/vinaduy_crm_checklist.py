from odoo import api, fields, models


class VinaduyCrmChecklistTemplate(models.Model):
    _name = 'vinaduy.crm.checklist.template'
    _description = 'Checklist mẫu cho stage CRM'
    _order = 'stage_id, sequence, id'

    name = fields.Char(string='Tên việc', required=True, translate=True)
    stage_id = fields.Many2one(
        'crm.stage', string='Stage', required=True, ondelete='cascade',
        help='Checklist này thuộc stage nào',
    )
    sequence = fields.Integer(default=10)
    description = fields.Char(string='Mô tả thêm', translate=True)
    required = fields.Boolean(
        string='Bắt buộc',
        default=True,
        help='Nếu bật, lead phải hoàn thành item này trước khi chuyển sang stage tiếp theo',
    )
    field_name = fields.Char(
        string='Field auto-tick',
        help='Tên field trên crm.lead. Khi field có giá trị, item sẽ tự tick. '
             'Vd: vd_address, vd_area, vd_budget',
    )
    active = fields.Boolean(default=True)


class VinaduyCrmChecklistItem(models.Model):
    _name = 'vinaduy.crm.checklist.item'
    _description = 'Checklist item gắn với 1 lead'
    _order = 'sequence, id'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade', index=True)
    template_id = fields.Many2one(
        'vinaduy.crm.checklist.template', required=True, ondelete='restrict',
    )
    name = fields.Char(related='template_id.name', store=True, readonly=True)
    sequence = fields.Integer(related='template_id.sequence', store=True, readonly=True)
    description = fields.Char(related='template_id.description', readonly=True)
    required = fields.Boolean(related='template_id.required', store=True, readonly=True)
    stage_id = fields.Many2one(related='template_id.stage_id', store=True, readonly=True)

    done = fields.Boolean(string='Hoàn thành')
    done_date = fields.Datetime(string='Ngày hoàn thành', readonly=True)
    done_by = fields.Many2one('res.users', string='Người hoàn thành', readonly=True)

    def write(self, vals):
        if 'done' in vals:
            if vals['done']:
                vals.setdefault('done_date', fields.Datetime.now())
                vals.setdefault('done_by', self.env.user.id)
            else:
                vals['done_date'] = False
                vals['done_by'] = False
        return super().write(vals)
