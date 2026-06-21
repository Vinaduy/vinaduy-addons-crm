# -*- coding: utf-8 -*-
"""Bang HE SO TINH NHAM bao gia theo vung (Bac/Trung/Nam).

Cong thuc (theo file "Tinh nham.pptx"):
    Tong tien ~= HE SO x Dien tich (san tang 1 / mong) x Don gia/m2

He so phu thuoc: Vung x (So tang + Kieu mai) x Loai mong. Admin chinh trong
Cau hinh -> "He so tinh nham" (CRM > Cau hinh). Widget tren form khach doc bang
nay de tinh nhanh khi tu van.
"""
from odoo import api, fields, models

# 5 cot = (so tang + kieu mai); 3 hang = loai mong.
_COMBOS = ['mb1', 'mb2', 'mn1', 'mn2', 'mt1']   # 1T mai bang, 2T mai bang, 1T mai nhat, 2T mai nhat, 1T mai thai
_FOUNDS = ['don', 'bang', 'coc']                # mong coc(don), mong bang, mong coc


class VdTinhnhamRegion(models.Model):
    _name = 'vd.tinhnham.region'
    _description = 'He so tinh nham bao gia theo vung'
    _order = 'sequence, id'

    name = fields.Char(string='Tên vùng', required=True)
    region = fields.Selection(
        [('bac', 'Miền Bắc'), ('trung', 'Miền Trung'), ('nam', 'Miền Nam')],
        string='Vùng', required=True)
    sequence = fields.Integer(default=10)

    # ----- 15 he so (mong x combo) -----
    hs_don_mb1 = fields.Float('Cốc · 1T Mái bằng', digits=(5, 2))
    hs_don_mb2 = fields.Float('Cốc · 2T Mái bằng', digits=(5, 2))
    hs_don_mn1 = fields.Float('Cốc · 1T Mái Nhật', digits=(5, 2))
    hs_don_mn2 = fields.Float('Cốc · 2T Mái Nhật', digits=(5, 2))
    hs_don_mt1 = fields.Float('Cốc · 1T Mái Thái', digits=(5, 2))
    hs_bang_mb1 = fields.Float('Băng · 1T Mái bằng', digits=(5, 2))
    hs_bang_mb2 = fields.Float('Băng · 2T Mái bằng', digits=(5, 2))
    hs_bang_mn1 = fields.Float('Băng · 1T Mái Nhật', digits=(5, 2))
    hs_bang_mn2 = fields.Float('Băng · 2T Mái Nhật', digits=(5, 2))
    hs_bang_mt1 = fields.Float('Băng · 1T Mái Thái', digits=(5, 2))
    hs_coc_mb1 = fields.Float('Cọc · 1T Mái bằng', digits=(5, 2))
    hs_coc_mb2 = fields.Float('Cọc · 2T Mái bằng', digits=(5, 2))
    hs_coc_mn1 = fields.Float('Cọc · 1T Mái Nhật', digits=(5, 2))
    hs_coc_mn2 = fields.Float('Cọc · 2T Mái Nhật', digits=(5, 2))
    hs_coc_mt1 = fields.Float('Cọc · 1T Mái Thái', digits=(5, 2))

    # ----- Luu y / phat sinh (trieu dong) -----
    note_small_pct = fields.Float('DT < 70m2 cộng (%)', digits=(4, 1), default=5)
    lung_min = fields.Integer('Gác lửng bớt (triệu) từ', default=30)
    lung_max = fields.Integer('đến', default=50)
    tum_min = fields.Integer('Tum phát sinh (triệu) từ', default=120)
    tum_max = fields.Integer('đến', default=150)
    epcoc_min = fields.Integer('Ép cọc (triệu) từ', default=70)
    epcoc_max = fields.Integer('đến', default=150)
    noithat_min = fields.Integer('Nội thất (triệu) từ', default=200)
    noithat_max = fields.Integer('đến', default=400)
    capphep_min = fields.Integer('Cấp phép (triệu) từ', default=10)
    capphep_max = fields.Integer('đến', default=20)

    @api.model
    def vd_get_table(self):
        """Du lieu cho widget tinh nham tren form khach."""
        out = {}
        for r in self.sudo().search([]):
            coefs = {}
            for f in _FOUNDS:
                for c in _COMBOS:
                    coefs['%s_%s' % (f, c)] = r['hs_%s_%s' % (f, c)] or 0.0
            out[r.region] = {
                'name': r.name or '',
                'coefs': coefs,
                'notes': {
                    'small_pct': r.note_small_pct or 0,
                    'lung': [r.lung_min, r.lung_max],
                    'tum': [r.tum_min, r.tum_max],
                    'epcoc': [r.epcoc_min, r.epcoc_max],
                    'noithat': [r.noithat_min, r.noithat_max],
                    'capphep': [r.capphep_min, r.capphep_max],
                },
            }
        return out
