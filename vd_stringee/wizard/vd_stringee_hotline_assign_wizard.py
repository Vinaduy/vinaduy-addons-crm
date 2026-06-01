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
        help='Chọn NV được gán số tổng đài này. 1 số có thể gán cho NHIỀU NV, '
             '1 NV có nhiều số (mỗi mạng 1 số) — gọi sẽ tự lấy số cùng mạng KH.',
    )
    moved_user_ids = fields.Many2many(
        'res.users', 'vd_stringee_hotline_assign_moved_rel',
        compute='_compute_moved_users',
        string='NV sẽ chuyển từ hotline khác',
    )
    moved_count = fields.Integer(compute='_compute_moved_users')

    @api.depends('user_ids', 'hotline_id')
    def _compute_moved_users(self):
        # Model m2m: gán thêm 1 số KHÔNG đẩy NV khỏi số khác → không còn "move".
        for wiz in self:
            wiz.moved_user_ids = self.env['res.users']
            wiz.moved_count = 0

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
            res['user_ids'] = [(6, 0, hotline.assigned_user_ids.ids)]
        return res

    def action_apply(self):
        self.ensure_one()
        new_users = self.user_ids
        old_users = self.hotline_id.assigned_user_ids
        to_remove = old_users - new_users
        to_add = new_users - old_users
        # m2m: chỉ thêm/bớt số NÀY cho NV, không đụng các số mạng khác của NV.
        for u in to_remove:
            u.stringee_hotline_ids = [(3, self.hotline_id.id)]
        for u in to_add:
            u.stringee_hotline_ids = [(4, self.hotline_id.id)]
        return {'type': 'ir.actions.act_window_close'}
