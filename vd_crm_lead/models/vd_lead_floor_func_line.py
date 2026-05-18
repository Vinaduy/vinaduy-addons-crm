"""Line model: 1 dòng = 1 (lead, tầng, công năng tag, số lượng).

Cho phép qty > 1: vd "2 phòng ngủ thường" trong cùng tầng = 1 line qty=2.
Filter tag theo tầng qua field fit_floors trên tag.
"""
from odoo import api, fields, models


FLOOR_KEY_SEL = [
    ('f1', 'Tầng 1'),
    ('f2', 'Tầng 2'),
    ('f3', 'Tầng 3'),
    ('f4', 'Tầng 4'),
    ('f5', 'Tầng 5'),
    ('f6', 'Tầng 6'),
    ('f7', 'Tầng 7'),
    ('tum', 'Tum'),
]


class VdLeadFloorFuncLine(models.Model):
    _name = 'vd.lead.floor.func.line'
    _description = 'Dòng công năng tầng của lead'
    _order = 'lead_id, floor_seq, sequence, id'

    lead_id = fields.Many2one(
        'crm.lead', required=True, ondelete='cascade', string='Lead')
    floor_key = fields.Selection(
        FLOOR_KEY_SEL, required=True, default='f1', string='Tầng')
    floor_seq = fields.Integer(
        compute='_compute_floor_seq', store=True,
        help='Số thứ tự tầng để sort (1..7, tum=8)')
    tag_id = fields.Many2one(
        'vd.floor.function.tag', required=True, string='Công năng',
        ondelete='restrict')
    quantity = fields.Integer(
        string='SL', default=1, required=True,
        help='Số lượng cùng loại trong tầng (vd 2 phòng ngủ thường)')
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('qty_positive', 'CHECK(quantity > 0)', 'Số lượng phải > 0'),
    ]

    @api.depends('floor_key')
    def _compute_floor_seq(self):
        order = {k: i for i, (k, _) in enumerate(FLOOR_KEY_SEL, start=1)}
        for rec in self:
            rec.floor_seq = order.get(rec.floor_key, 99)
