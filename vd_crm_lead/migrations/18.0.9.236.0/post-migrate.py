# -*- coding: utf-8 -*-
"""User spec 2026-06-13: gộp inbox — bình luận thành hội thoại kind='comment'.
Chuyển dữ liệu vd.fb.comment cũ sang vd.fb.conversation + message (qua
_ingest_comment, tự dedup theo comment_id). Giữ lại record comment cũ (không
xoá) phòng cần đối chiếu — UI mới không dùng tới."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    comments = env['vd.fb.comment'].search([])
    for c in comments:
        if not c.page_id or not c.comment_id:
            continue
        try:
            c.page_id._ingest_comment(
                comment_id=c.comment_id,
                post_id=c.post_id,
                parent_id=c.parent_comment_id,
                from_id=c.from_id,
                from_name=c.from_name,
                body=c.body or '',
                created_at=c.created_time,
            )
        except Exception:
            # 1 comment lỗi không được chặn cả migration
            continue
