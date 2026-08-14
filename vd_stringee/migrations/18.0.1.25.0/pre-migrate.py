"""v1.25.0: tạo sẵn cột vd_answered + fill bằng SQL TRƯỚC khi ORM nạp model.

Nếu để Odoo tự thêm cột, nó sẽ mass-compute _compute_vd_answered trên toàn bộ
~29.800 cuộc gọi, tức nạp cả cột raw_events (JSON, mỗi bản ghi vài KB) vào RAM
của một worker 300MB → kéo dài downtime upgrade và có nguy cơ swap trên VM 3.8GB.
Một câu UPDATE làm đúng việc đó trong ~1 giây, và vì cột đã tồn tại + không NULL
nên Odoo bỏ qua bước init column.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE stringee_call
        ADD COLUMN IF NOT EXISTS vd_answered boolean
    """)
    # COALESCE bắt buộc: SQL ba trạng thái làm `false OR NULL` ra NULL, nên bản
    # ghi có raw_events rỗng sẽ đọng NULL thay vì false (đã dính 1.861 bản ghi ở
    # lần chạy đầu). Kết quả lọc vẫn đúng vì NULL không khớp `= true`, nhưng để
    # cột sạch thì ép về false ngay.
    cr.execute("""
        UPDATE stringee_call
           SET vd_answered = COALESCE(answer_time IS NOT NULL
                                      OR raw_events ILIKE '%answered%', false)
         WHERE vd_answered IS NULL
    """)
    _logger.info('vd_answered: backfill %s cuộc gọi', cr.rowcount)
    # Index để lọc theo cột này không còn quét bảng (Odoo cũng tạo, nhưng tạo
    # sẵn ở đây thì lần upgrade này đã có ngay).
    cr.execute("""
        CREATE INDEX IF NOT EXISTS stringee_call_vd_answered_index
            ON stringee_call (vd_answered)
    """)
