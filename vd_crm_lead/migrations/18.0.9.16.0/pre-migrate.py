"""Pre-migrate: copy region_ids / foundation / roof_simple / floor_range
từ category xuống template TRƯỚC khi Odoo drop các column này khỏi category.

Phải chạy pre-migrate vì Odoo update schema (drop column) trước khi
post-migrate chạy → nếu chạy ở post, dữ liệu cũ trên category đã mất.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Check các column cũ còn tồn tại trên category không (skip nếu module
    # mới install lần đầu, không có dữ liệu cần migrate)
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'vd_quote_template_category'
          AND column_name IN ('floor_range', 'foundation', 'roof_simple')
    """)
    cols = {r[0] for r in cr.fetchall()}
    if not cols:
        _logger.info("[vd_crm_lead] Không có column dim trên category — skip")
        return

    # Add các column mới trên template (Odoo sẽ tự add khi load model
    # nhưng schema update chạy sau post-migrate → tự thêm bằng SQL ở đây
    # để pre-migrate đọc/ghi được)
    cr.execute("""
        ALTER TABLE vd_quote_template
        ADD COLUMN IF NOT EXISTS foundation varchar,
        ADD COLUMN IF NOT EXISTS roof_simple varchar,
        ADD COLUMN IF NOT EXISTS floor_range varchar;
    """)

    # Copy values từ category sang template
    cr.execute("""
        UPDATE vd_quote_template t
        SET foundation = c.foundation,
            roof_simple = c.roof_simple,
            floor_range = c.floor_range
        FROM vd_quote_template_category c
        WHERE t.category_id = c.id
          AND (c.foundation IS NOT NULL OR c.roof_simple IS NOT NULL OR c.floor_range IS NOT NULL);
    """)
    cr.execute("SELECT COUNT(*) FROM vd_quote_template WHERE foundation IS NOT NULL OR roof_simple IS NOT NULL OR floor_range IS NOT NULL")
    n_dim = cr.fetchone()[0]
    _logger.info("[vd_crm_lead] Copy dim từ category → %d template", n_dim)

    # Copy region_ids: M2M relation table cũ
    # 'vd_quote_template_category_region_rel' (category_id, region_id)
    # → mới 'vd_quote_template_region_rel' (template_id, region_id)
    cr.execute("""
        CREATE TABLE IF NOT EXISTS vd_quote_template_region_rel (
            template_id INTEGER NOT NULL,
            region_id INTEGER NOT NULL,
            PRIMARY KEY (template_id, region_id)
        );
    """)
    cr.execute("""
        INSERT INTO vd_quote_template_region_rel (template_id, region_id)
        SELECT DISTINCT t.id, rel.region_id
        FROM vd_quote_template t
        JOIN vd_quote_template_category_region_rel rel ON rel.category_id = t.category_id
        ON CONFLICT DO NOTHING;
    """)
    cr.execute("SELECT COUNT(*) FROM vd_quote_template_region_rel")
    n_reg = cr.fetchone()[0]
    _logger.info("[vd_crm_lead] Copy region_ids → %d row(s) trên template", n_reg)
