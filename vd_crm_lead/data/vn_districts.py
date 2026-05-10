# -*- coding: utf-8 -*-
"""
Danh sách Huyện / Quận / Thị xã / Thành phố thuộc tỉnh Việt Nam.
Khoá = TÊN tỉnh/thành phố trong res.country.state (đúng dấu tiếng Việt).
Giá trị = list tên các đơn vị hành chính cấp huyện.

Dữ liệu căn cứ theo chia tách hành chính phổ biến (~705 huyện).
"""

VN_DISTRICTS = {
    # ============ Đồng bằng sông Hồng ============
    "Hà Nội": [
        # 12 quận
        "Ba Đình", "Hoàn Kiếm", "Tây Hồ", "Long Biên", "Cầu Giấy", "Đống Đa",
        "Hai Bà Trưng", "Hoàng Mai", "Thanh Xuân", "Bắc Từ Liêm", "Nam Từ Liêm", "Hà Đông",
        # 1 thị xã
        "Sơn Tây",
        # 17 huyện
        "Ba Vì", "Chương Mỹ", "Đan Phượng", "Đông Anh", "Gia Lâm", "Hoài Đức",
        "Mê Linh", "Mỹ Đức", "Phú Xuyên", "Phúc Thọ", "Quốc Oai", "Sóc Sơn",
        "Thạch Thất", "Thanh Oai", "Thanh Trì", "Thường Tín", "Ứng Hòa",
    ],
    "Hải Phòng": [
        "Hồng Bàng", "Ngô Quyền", "Lê Chân", "Hải An", "Kiến An", "Đồ Sơn", "Dương Kinh",
        "An Dương", "An Lão", "Bạch Long Vĩ", "Cát Hải", "Kiến Thụy", "Tiên Lãng",
        "Thủy Nguyên", "Vĩnh Bảo",
    ],
    "Bắc Ninh": [
        "Bắc Ninh", "Từ Sơn", "Gia Bình", "Lương Tài", "Quế Võ", "Thuận Thành",
        "Tiên Du", "Yên Phong",
    ],
    "Hà Nam": [
        "Phủ Lý", "Duy Tiên", "Bình Lục", "Kim Bảng", "Lý Nhân", "Thanh Liêm",
    ],
    "Hải Dương": [
        "Hải Dương", "Chí Linh", "Kinh Môn", "Bình Giang", "Cẩm Giàng", "Gia Lộc",
        "Kim Thành", "Nam Sách", "Ninh Giang", "Thanh Hà", "Thanh Miện", "Tứ Kỳ",
    ],
    "Hưng Yên": [
        "Hưng Yên", "Mỹ Hào", "Ân Thi", "Khoái Châu", "Kim Động", "Phù Cừ",
        "Tiên Lữ", "Văn Giang", "Văn Lâm", "Yên Mỹ",
    ],
    "Nam Định": [
        "Nam Định", "Giao Thủy", "Hải Hậu", "Mỹ Lộc", "Nam Trực", "Nghĩa Hưng",
        "Trực Ninh", "Vụ Bản", "Xuân Trường", "Ý Yên",
    ],
    "Ninh Bình": [
        "Ninh Bình", "Tam Điệp", "Gia Viễn", "Hoa Lư", "Kim Sơn", "Nho Quan",
        "Yên Khánh", "Yên Mô",
    ],
    "Thái Bình": [
        "Thái Bình", "Đông Hưng", "Hưng Hà", "Kiến Xương", "Quỳnh Phụ",
        "Thái Thụy", "Tiền Hải", "Vũ Thư",
    ],
    "Vĩnh Phúc": [
        "Vĩnh Yên", "Phúc Yên", "Bình Xuyên", "Lập Thạch", "Sông Lô",
        "Tam Đảo", "Tam Dương", "Vĩnh Tường", "Yên Lạc",
    ],

    # ============ Trung du và miền núi phía Bắc ============
    "Hà Giang": [
        "Hà Giang", "Bắc Mê", "Bắc Quang", "Đồng Văn", "Hoàng Su Phì", "Mèo Vạc",
        "Quản Bạ", "Quang Bình", "Vị Xuyên", "Xín Mần", "Yên Minh",
    ],
    "Cao Bằng": [
        "Cao Bằng", "Bảo Lạc", "Bảo Lâm", "Hạ Lang", "Hà Quảng", "Hòa An",
        "Nguyên Bình", "Quảng Hòa", "Thạch An", "Trùng Khánh",
    ],
    "Bắc Kạn": [
        "Bắc Kạn", "Ba Bể", "Bạch Thông", "Chợ Đồn", "Chợ Mới", "Na Rì",
        "Ngân Sơn", "Pác Nặm",
    ],
    "Tuyên Quang": [
        "Tuyên Quang", "Chiêm Hóa", "Hàm Yên", "Lâm Bình", "Na Hang",
        "Sơn Dương", "Yên Sơn",
    ],
    "Lào Cai": [
        "Lào Cai", "Sa Pa", "Bảo Thắng", "Bảo Yên", "Bát Xát", "Bắc Hà",
        "Mường Khương", "Si Ma Cai", "Văn Bàn",
    ],
    "Điện Biên": [
        "Điện Biên Phủ", "Mường Lay", "Điện Biên", "Điện Biên Đông", "Mường Ảng",
        "Mường Chà", "Mường Nhé", "Nậm Pồ", "Tủa Chùa", "Tuần Giáo",
    ],
    "Lai Châu": [
        "Lai Châu", "Mường Tè", "Nậm Nhùn", "Phong Thổ", "Sìn Hồ",
        "Tam Đường", "Tân Uyên", "Than Uyên",
    ],
    "Sơn La": [
        "Sơn La", "Mộc Châu", "Bắc Yên", "Mai Sơn", "Mường La", "Phù Yên",
        "Quỳnh Nhai", "Sông Mã", "Sốp Cộp", "Thuận Châu", "Vân Hồ", "Yên Châu",
    ],
    "Yên Bái": [
        "Yên Bái", "Nghĩa Lộ", "Lục Yên", "Mù Cang Chải", "Trạm Tấu",
        "Trấn Yên", "Văn Chấn", "Văn Yên", "Yên Bình",
    ],
    "Hòa Bình": [
        "Hòa Bình", "Cao Phong", "Đà Bắc", "Kim Bôi", "Lạc Sơn", "Lạc Thủy",
        "Lương Sơn", "Mai Châu", "Tân Lạc", "Yên Thủy",
    ],
    "Thái Nguyên": [
        "Thái Nguyên", "Sông Công", "Phổ Yên", "Đại Từ", "Định Hóa", "Đồng Hỷ",
        "Phú Bình", "Phú Lương", "Võ Nhai",
    ],
    "Lạng Sơn": [
        "Lạng Sơn", "Bắc Sơn", "Bình Gia", "Cao Lộc", "Chi Lăng", "Đình Lập",
        "Hữu Lũng", "Lộc Bình", "Tràng Định", "Văn Lãng", "Văn Quan",
    ],
    "Quảng Ninh": [
        "Hạ Long", "Cẩm Phả", "Móng Cái", "Uông Bí", "Đông Triều", "Quảng Yên",
        "Ba Chẽ", "Bình Liêu", "Cô Tô", "Đầm Hà", "Hải Hà", "Hoành Bồ",
        "Tiên Yên", "Vân Đồn",
    ],
    "Bắc Giang": [
        "Bắc Giang", "Hiệp Hòa", "Lạng Giang", "Lục Nam", "Lục Ngạn",
        "Sơn Động", "Tân Yên", "Việt Yên", "Yên Dũng", "Yên Thế",
    ],
    "Phú Thọ": [
        "Việt Trì", "Phú Thọ", "Cẩm Khê", "Đoan Hùng", "Hạ Hòa", "Lâm Thao",
        "Phù Ninh", "Tam Nông", "Tân Sơn", "Thanh Ba", "Thanh Sơn",
        "Thanh Thủy", "Yên Lập",
    ],

    # ============ Bắc Trung Bộ ============
    "Thanh Hóa": [
        "Thanh Hóa", "Bỉm Sơn", "Sầm Sơn", "Nghi Sơn", "Bá Thước", "Cẩm Thủy",
        "Đông Sơn", "Hà Trung", "Hậu Lộc", "Hoằng Hóa", "Lang Chánh",
        "Mường Lát", "Nga Sơn", "Ngọc Lặc", "Như Thanh", "Như Xuân",
        "Nông Cống", "Quan Hóa", "Quan Sơn", "Quảng Xương", "Thạch Thành",
        "Thiệu Hóa", "Thọ Xuân", "Thường Xuân", "Triệu Sơn", "Vĩnh Lộc", "Yên Định",
    ],
    "Nghệ An": [
        "Vinh", "Cửa Lò", "Hoàng Mai", "Thái Hòa", "Anh Sơn", "Con Cuông",
        "Diễn Châu", "Đô Lương", "Hưng Nguyên", "Kỳ Sơn", "Nam Đàn", "Nghi Lộc",
        "Nghĩa Đàn", "Quế Phong", "Quỳ Châu", "Quỳ Hợp", "Quỳnh Lưu",
        "Tân Kỳ", "Thanh Chương", "Tương Dương", "Yên Thành",
    ],
    "Hà Tĩnh": [
        "Hà Tĩnh", "Hồng Lĩnh", "Kỳ Anh", "Cẩm Xuyên", "Can Lộc", "Đức Thọ",
        "Hương Khê", "Hương Sơn", "Lộc Hà", "Nghi Xuân", "Thạch Hà", "Vũ Quang",
    ],
    "Quảng Bình": [
        "Đồng Hới", "Ba Đồn", "Bố Trạch", "Lệ Thủy", "Minh Hóa", "Quảng Ninh",
        "Quảng Trạch", "Tuyên Hóa",
    ],
    "Quảng Trị": [
        "Đông Hà", "Quảng Trị", "Cam Lộ", "Cồn Cỏ", "Đa Krông", "Gio Linh",
        "Hải Lăng", "Hướng Hóa", "Triệu Phong", "Vĩnh Linh",
    ],
    "Thừa Thiên Huế": [
        "Huế", "Hương Thủy", "Hương Trà", "A Lưới", "Nam Đông", "Phong Điền",
        "Phú Lộc", "Phú Vang", "Quảng Điền",
    ],

    # ============ Duyên hải Nam Trung Bộ ============
    "Đà Nẵng": [
        "Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn", "Liên Chiểu",
        "Cẩm Lệ", "Hòa Vang", "Hoàng Sa",
    ],
    "Quảng Nam": [
        "Tam Kỳ", "Hội An", "Điện Bàn", "Bắc Trà My", "Đại Lộc", "Đông Giang",
        "Duy Xuyên", "Hiệp Đức", "Nam Giang", "Nam Trà My", "Nông Sơn",
        "Núi Thành", "Phú Ninh", "Phước Sơn", "Quế Sơn", "Tây Giang",
        "Thăng Bình", "Tiên Phước",
    ],
    "Quảng Ngãi": [
        "Quảng Ngãi", "Ba Tơ", "Bình Sơn", "Đức Phổ", "Lý Sơn", "Minh Long",
        "Mộ Đức", "Nghĩa Hành", "Sơn Hà", "Sơn Tây", "Sơn Tịnh",
        "Trà Bồng", "Tư Nghĩa",
    ],
    "Bình Định": [
        "Quy Nhơn", "An Nhơn", "Hoài Nhơn", "An Lão", "Hoài Ân", "Phù Cát",
        "Phù Mỹ", "Tây Sơn", "Tuy Phước", "Vân Canh", "Vĩnh Thạnh",
    ],
    "Phú Yên": [
        "Tuy Hòa", "Đông Hòa", "Sông Cầu", "Đồng Xuân", "Phú Hòa", "Sơn Hòa",
        "Sông Hinh", "Tây Hòa", "Tuy An",
    ],
    "Khánh Hòa": [
        "Nha Trang", "Cam Ranh", "Cam Lâm", "Diên Khánh", "Khánh Sơn",
        "Khánh Vĩnh", "Ninh Hòa", "Trường Sa", "Vạn Ninh",
    ],
    "Ninh Thuận": [
        "Phan Rang - Tháp Chàm", "Bác Ái", "Ninh Hải", "Ninh Phước",
        "Ninh Sơn", "Thuận Bắc", "Thuận Nam",
    ],
    "Bình Thuận": [
        "Phan Thiết", "La Gi", "Bắc Bình", "Đức Linh", "Hàm Tân", "Hàm Thuận Bắc",
        "Hàm Thuận Nam", "Phú Quý", "Tánh Linh", "Tuy Phong",
    ],

    # ============ Tây Nguyên ============
    "Kon Tum": [
        "Kon Tum", "Đắk Glei", "Đắk Hà", "Đắk Tô", "Ia H'Drai", "Kon Plông",
        "Kon Rẫy", "Ngọc Hồi", "Sa Thầy", "Tu Mơ Rông",
    ],
    "Gia Lai": [
        "Pleiku", "An Khê", "Ayun Pa", "Chư Păh", "Chư Prông", "Chư Pưh",
        "Chư Sê", "Đắk Đoa", "Đắk Pơ", "Đức Cơ", "Ia Grai", "Ia Pa",
        "K'Bang", "Kông Chro", "Krông Pa", "Mang Yang", "Phú Thiện",
    ],
    "Đắk Lắk": [
        "Buôn Ma Thuột", "Buôn Hồ", "Buôn Đôn", "Cư Kuin", "Cư M'gar",
        "Ea H'leo", "Ea Kar", "Ea Súp", "Krông Ana", "Krông Bông",
        "Krông Búk", "Krông Năng", "Krông Pắc", "Lắk", "M'Đrắk",
    ],
    "Đắk Nông": [
        "Gia Nghĩa", "Cư Jút", "Đắk Glong", "Đắk Mil", "Đắk R'lấp",
        "Đắk Song", "Krông Nô", "Tuy Đức",
    ],
    "Lâm Đồng": [
        "Đà Lạt", "Bảo Lộc", "Bảo Lâm", "Cát Tiên", "Đạ Huoai", "Đạ Tẻh",
        "Đam Rông", "Di Linh", "Đơn Dương", "Đức Trọng", "Lạc Dương", "Lâm Hà",
    ],

    # ============ Đông Nam Bộ ============
    "Hồ Chí Minh": [
        # 16 quận
        "Quận 1", "Quận 3", "Quận 4", "Quận 5", "Quận 6", "Quận 7", "Quận 8",
        "Quận 10", "Quận 11", "Quận 12", "Bình Tân", "Bình Thạnh", "Gò Vấp",
        "Phú Nhuận", "Tân Bình", "Tân Phú",
        # 1 thành phố thuộc TP
        "Thủ Đức",
        # 5 huyện
        "Bình Chánh", "Cần Giờ", "Củ Chi", "Hóc Môn", "Nhà Bè",
    ],
    "Bình Dương": [
        "Thủ Dầu Một", "Bến Cát", "Dĩ An", "Tân Uyên", "Thuận An",
        "Bàu Bàng", "Bắc Tân Uyên", "Dầu Tiếng", "Phú Giáo",
    ],
    "Bình Phước": [
        "Đồng Xoài", "Bình Long", "Phước Long", "Bù Đăng", "Bù Đốp",
        "Bù Gia Mập", "Chơn Thành", "Đồng Phú", "Hớn Quản", "Lộc Ninh", "Phú Riềng",
    ],
    "Tây Ninh": [
        "Tây Ninh", "Hòa Thành", "Trảng Bàng", "Bến Cầu", "Châu Thành",
        "Dương Minh Châu", "Gò Dầu", "Tân Biên", "Tân Châu",
    ],
    "Đồng Nai": [
        "Biên Hòa", "Long Khánh", "Cẩm Mỹ", "Định Quán", "Long Thành",
        "Nhơn Trạch", "Tân Phú", "Thống Nhất", "Trảng Bom", "Vĩnh Cửu", "Xuân Lộc",
    ],
    "Bà Rịa - Vũng Tàu": [
        "Vũng Tàu", "Bà Rịa", "Phú Mỹ", "Châu Đức", "Côn Đảo", "Đất Đỏ",
        "Long Điền", "Xuyên Mộc",
    ],

    # ============ Đồng bằng sông Cửu Long ============
    "Long An": [
        "Tân An", "Kiến Tường", "Bến Lức", "Cần Đước", "Cần Giuộc", "Châu Thành",
        "Đức Hòa", "Đức Huệ", "Mộc Hóa", "Tân Hưng", "Tân Thạnh", "Tân Trụ",
        "Thạnh Hóa", "Thủ Thừa", "Vĩnh Hưng",
    ],
    "Tiền Giang": [
        "Mỹ Tho", "Cai Lậy", "Gò Công", "Cái Bè", "Châu Thành", "Chợ Gạo",
        "Gò Công Đông", "Gò Công Tây", "Tân Phú Đông", "Tân Phước",
    ],
    "Bến Tre": [
        "Bến Tre", "Ba Tri", "Bình Đại", "Châu Thành", "Chợ Lách",
        "Giồng Trôm", "Mỏ Cày Bắc", "Mỏ Cày Nam", "Thạnh Phú",
    ],
    "Trà Vinh": [
        "Trà Vinh", "Duyên Hải", "Càng Long", "Cầu Kè", "Cầu Ngang",
        "Châu Thành", "Tiểu Cần", "Trà Cú",
    ],
    "Vĩnh Long": [
        "Vĩnh Long", "Bình Minh", "Bình Tân", "Long Hồ", "Mang Thít",
        "Tam Bình", "Trà Ôn", "Vũng Liêm",
    ],
    "Đồng Tháp": [
        "TP. Cao Lãnh", "Sa Đéc", "Hồng Ngự", "Huyện Cao Lãnh", "Châu Thành",
        "Lai Vung", "Lấp Vò", "Tam Nông", "Tân Hồng", "Thanh Bình", "Tháp Mười",
    ],
    "An Giang": [
        "Long Xuyên", "Châu Đốc", "Tân Châu", "An Phú", "Châu Phú", "Châu Thành",
        "Chợ Mới", "Phú Tân", "Thoại Sơn", "Tịnh Biên", "Tri Tôn",
    ],
    "Kiên Giang": [
        "Rạch Giá", "Hà Tiên", "Phú Quốc", "An Biên", "An Minh", "Châu Thành",
        "Giang Thành", "Giồng Riềng", "Gò Quao", "Hòn Đất", "Kiên Hải",
        "Kiên Lương", "Tân Hiệp", "U Minh Thượng", "Vĩnh Thuận",
    ],
    "Cần Thơ": [
        "Ninh Kiều", "Bình Thủy", "Cái Răng", "Ô Môn", "Thốt Nốt",
        "Cờ Đỏ", "Phong Điền", "Thới Lai", "Vĩnh Thạnh",
    ],
    "Hậu Giang": [
        "Vị Thanh", "Ngã Bảy", "TX. Long Mỹ", "Châu Thành", "Châu Thành A",
        "Huyện Long Mỹ", "Phụng Hiệp", "Vị Thủy",
    ],
    "Sóc Trăng": [
        "Sóc Trăng", "Vĩnh Châu", "Ngã Năm", "Châu Thành", "Cù Lao Dung",
        "Kế Sách", "Long Phú", "Mỹ Tú", "Mỹ Xuyên", "Thạnh Trị", "Trần Đề",
    ],
    "Bạc Liêu": [
        "Bạc Liêu", "Giá Rai", "Đông Hải", "Hòa Bình", "Hồng Dân",
        "Phước Long", "Vĩnh Lợi",
    ],
    "Cà Mau": [
        "Cà Mau", "Năm Căn", "Cái Nước", "Đầm Dơi", "Ngọc Hiển",
        "Phú Tân", "Thới Bình", "Trần Văn Thời", "U Minh",
    ],
}
