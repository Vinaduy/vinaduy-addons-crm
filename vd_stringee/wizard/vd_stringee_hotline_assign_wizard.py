from odoo import _, api, fields, models


class VdStringeeHotlineAssignWizard(models.TransientModel):
    _name = 'vd.stringee.hotline.assign.wizard'
    _description = 'Gán NV cho số tổng đài Stringee'

    hotline_id = fields.Many2one(
        'vd.stringee.hotline', string='Số tổng đài',
        required=True, readonly=True, ondelete='cascade',
    )
    hotline_number = fields.Char(related='hotline_id.number', readonly=True)
    hotline_carrier = fields.Selection(related='hotline_id.carrier', readonly=True)
    user_ids = fields.Many2many(
        'res.users', string='NV dùng số này',
        domain="[('share','=',False),('active','=',True)]",
        help='Chọn NV sẽ dùng số tổng đài này để gọi ra. Mỗi NV chỉ dùng 1 số — '
             'NV đang dùng số khác sẽ được chuyển sang số này.',
    )
    moved_user_ids = fields.Many2many(
        'res.users', 'vd_stringee_hotline_assign_moved_rel',
        compute='_compute_moved_users',
        string='NV sẽ chuyển từ hotline khác',
    )
    moved_count = fields.Integer(compute='_compute_moved_users')

    @api.depends('user_ids', 'hotline_id')
    def _compute_moved_users(self):
        for wiz in self:
            moved = wiz.user_ids.filtered(
                lambda u: u.stringee_from_number_id
                and u.stringee_from_number_id != wiz.hotline_id
            )
            wiz.moved_user_ids = moved
            wiz.moved_count = len(moved)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        hotline_id = ctx.get('default_hotline_id') or (
            ctx.get('active_id') if ctx.get('active_model') == 'vd.stringee.hotline' else False
        )
        if hotline_id:
            hotline = self.env['vd.stringee.hotline'].browse(hotline_id)
            res['hotline_id'] = hotline.id
            res['user_ids'] = [(6, 0, hotline.user_ids.ids)]
        return res

    def action_apply(self):
        self.ensure_one()
        new_users = self.user_ids
        old_users = self.hotline_id.user_ids
        to_remove = old_users - new_users
        to_add = new_users - old_users
        if to_remove:
            to_remove.write({'stringee_from_number_id': False})
        if to_add:
            to_add.write({'stringee_from_number_id': self.hotline_id.id})
        return {'type': 'ir.actions.act_window_close'}
