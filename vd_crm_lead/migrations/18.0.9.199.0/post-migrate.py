"""Round 14: dọn legacy vấn đề 'start_time' (THỜI GIAN KHỞI CÔNG).

User spec 2026-05-30: bỏ hoàn toàn auto-sinh vấn đề 'Thời gian khởi công'.
Code mới đã chặn _vd_ensure_default_problems không tạo nữa, nhưng các lead
cũ vẫn còn vấn đề legacy → unlink hết để bảng vấn đề sạch sẽ.

KHÔNG xoá 'cost_diff' (CÂN ĐỐI NGÂN SÁCH) — vẫn còn auto-sinh có giá trị.
"""
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        SELECT COUNT(*) FROM vd_lead_problem WHERE code = 'start_time'
    """)
    n = cr.fetchone()[0]
    if n:
        _logger.info("[round 14] Unlink %s legacy 'start_time' problems", n)
        cr.execute("""
            DELETE FROM vd_lead_problem WHERE code = 'start_time'
        """)
    else:
        _logger.info("[round 14] No legacy 'start_time' problems to clean")
