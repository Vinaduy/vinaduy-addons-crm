from odoo import fields, models


class VdDistrict(models.Model):
    _name = 'vd.district'
    _description = 'Phường / Xã'
    _order = 'state_id, name'
    _rec_name = 'name'

    name = fields.Char(string='Tên phường / xã', required=True, index=True)
    state_id = fields.Many2one(
        'res.country.state', string='Tỉnh / Thành',
        required=True, ondelete='cascade', index=True,
        domain="[('country_id.code', '=', 'VN')]",
    )
    state_name = fields.Char(related='state_id.name', store=False)

    _sql_constraints = [
        ('name_state_unique', 'unique(name, state_id)',
         'Phường/Xã đã tồn tại trong tỉnh này.'),
    ]

    def name_get(self):
        return [(rec.id, rec.name) for rec in self]
