# VINADUY CRM

Module mở rộng `crm` Odoo Community cho nghiệp vụ VINADUY.

## Tính năng

- Thêm field **Nguồn VINADUY** vào Lead/Opportunity (OMICall, Zalo, Website, FB, Khách giới thiệu...)
- Thêm field **Loại công trình** (Nhà phố, Biệt thự, Văn phòng...)
- Field tracking cuộc gọi OMICall (sẽ kết nối ở phase tiếp theo)
- Filter + group by trên search view

## Phụ thuộc

- `crm` (Community)
- `mail` (Community)
- `contacts` (Community)

## Cài đặt

```bash
./run.sh -d CRM_DEV -i vinaduy_crm
```

## Phát triển tiếp

- Phase 2: Controller webhook OMICall (`/vinaduy_crm/omicall/webhook`)
- Phase 3: Click-to-call OMICall từ form lead
- Phase 4: Tích hợp Zalo ZNS gửi tin chăm sóc lead
- Phase 5: Báo cáo theo nguồn / loại công trình

## License

LGPL-3
