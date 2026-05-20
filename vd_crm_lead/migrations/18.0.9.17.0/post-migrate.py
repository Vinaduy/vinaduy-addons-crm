"""Update đơn giá sàn cho cả 3 vùng theo bảng mới (2026-05-20).

Bảng cũ (mỗi vùng giá khác nhau) → bảng mới (3 vùng dùng chung 1 bảng
sàn, chỉ % móng khác nhau theo vùng).

Bảng mới đơn giá sàn:
| DT sàn     | Ô tô vào    | Ô tô KO vào |
|------------|-------------|-------------|
| ≥75m²      | 6.400.000   | 6.700.000   |
| 65–75m²    | 6.600.000   | 6.900.000   |
| 50–65m²    | 6.800.000   | 7.000.000   |
| 40–50m²    | 7.000.000   | 7.500.000   |
| <40m²      | 7.500.000   | 8.000.000   |

Các field khác (móng %, mái %, xây thô, phụ phí móng) giữ nguyên — đã
match bảng mới.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

NEW_SAN_PRICES = {
    'san_75_oto':  6_400_000,
    'san_75_kxe':  6_700_000,
    'san_65_oto':  6_600_000,
    'san_65_kxe':  6_900_000,
    'san_50_oto':  6_800_000,
    'san_50_kxe':  7_000_000,
    'san_40_oto':  7_000_000,
    'san_40_kxe':  7_500_000,
    'san_lt40_oto': 7_500_000,
    'san_lt40_kxe': 8_000_000,
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Pricing = env['vd.pricing.region']
    regions = Pricing.search([])
    if not regions:
        _logger.warning("[vd_crm_lead] Không có pricing region nào — skip update sàn")
        return
    for r in regions:
        old_75 = r.san_75_oto
        r.write(NEW_SAN_PRICES)
        _logger.info(
            "[vd_crm_lead] Updated sàn pricing cho %s (san_75_oto: %s → %s)",
            r.name, old_75, r.san_75_oto,
        )
