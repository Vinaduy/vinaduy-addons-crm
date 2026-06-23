# -*- coding: utf-8 -*-
"""KHO CÂU HỎI KHÓ và KỊCH BẢN TRẢ LỜI SALE (THƯ VIỆN - Câu hỏi khó).

Lưu toàn bộ câu hỏi khó khách hay hỏi khi tư vấn xây nhà trọn gói + 3 câu trả
lời mẫu (nhanh / giải thích sâu / dẫn dắt chốt). Nhân viên tìm theo từ khóa,
lọc theo chủ đề - mức độ - tình huống khách. Hiển thị qua nút filter "THƯ VIỆN
- Câu hỏi khó" cạnh các khóa học trong trang Học online.

Seed idempotent theo PHIÊN BẢN (ir.config_parameter). Bump version -> seed lại.
"""
from odoo import api, fields, models

_HQ_VERSION = 'v1'
_PARAM_KEY = 'vd_elearning.hard_question_seed_version'

TOPICS = [
    ('mong', 'Móng'),
    ('vattu', 'Vật tư'),
    ('kythuat', 'Kỹ thuật'),
    ('hopdong', 'Hợp đồng'),
    ('tho', 'Thợ thi công'),
    ('giaca', 'Giá cả'),
    ('phatsinh', 'Phát sinh'),
    ('baohanh', 'Bảo hành'),
    ('tiendo', 'Tiến độ'),
]
DIFFS = [
    ('de', 'Dễ'),
    ('trungbinh', 'Trung bình'),
    ('kho', 'Khó'),
    ('ratkho', 'Rất khó'),
]
SITUATIONS = [
    ('lo_rui_ro', 'Khách lo rủi ro'),
    ('so_gia', 'Khách so giá'),
    ('nghi_ngo', 'Khách nghi ngờ'),
    ('chuan_bi_ky', 'Khách chuẩn bị ký'),
    ('phan_doi', 'Khách phản đối hợp đồng'),
]
STATES = [
    ('draft', 'Nháp'),
    ('approved', 'Đã duyệt'),
    ('applying', 'Đang áp dụng'),
    ('stopped', 'Ngưng áp dụng'),
]


class VdHardQuestion(models.Model):
    _name = 'vd.hard.question'
    _description = 'Kho câu hỏi khó - kịch bản trả lời sale'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    topic = fields.Selection(TOPICS, string='Chủ đề', required=True, index=True)
    question = fields.Char(string='Câu hỏi khách hàng', required=True)
    difficulty = fields.Selection(DIFFS, string='Mức độ khó', default='kho')
    situation = fields.Selection(SITUATIONS, string='Tình huống khách')
    customer_intent = fields.Text(string='Mục đích thật sự của khách')
    answer1 = fields.Text(string='Trả lời nhanh (gọi điện)')
    answer2 = fields.Text(string='Giải thích sâu (Zalo/trực tiếp)')
    answer3 = fields.Text(string='Dẫn dắt chốt niềm tin')
    keywords = fields.Char(string='Từ khóa tìm kiếm')
    state = fields.Selection(STATES, string='Trạng thái', default='applying')

    @api.model
    def vd_library_load(self):
        """Trả dữ liệu cho Dialog THƯ VIỆN (chỉ câu đang áp dụng / đã duyệt)."""
        recs = self.sudo().search([('state', 'in', ('approved', 'applying'))])
        return {
            'topics': [{'key': k, 'label': v} for k, v in TOPICS],
            'difficulties': [{'key': k, 'label': v} for k, v in DIFFS],
            'situations': [{'key': k, 'label': v} for k, v in SITUATIONS],
            'items': [{
                'id': r.id,
                'topic': r.topic,
                'topic_label': dict(TOPICS).get(r.topic, ''),
                'question': r.question or '',
                'difficulty': r.difficulty or '',
                'difficulty_label': dict(DIFFS).get(r.difficulty, ''),
                'situation': r.situation or '',
                'situation_label': dict(SITUATIONS).get(r.situation, ''),
                'intent': r.customer_intent or '',
                'a1': r.answer1 or '',
                'a2': r.answer2 or '',
                'a3': r.answer3 or '',
                'keywords': r.keywords or '',
            } for r in recs],
        }

    @api.model
    def _vd_seed_hard_questions(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param(_PARAM_KEY) == _HQ_VERSION:
            return True
        # Bump version -> xóa toàn bộ seed cũ và tạo lại (giữ tinh thần idempotent).
        self.sudo().search([]).unlink()
        seq = 10
        for row in _SEED_DATA:
            topic, diff, sit, q, intent, a1, a2, a3, kw = row
            self.sudo().create({
                'sequence': seq, 'topic': topic, 'difficulty': diff,
                'situation': sit or False, 'question': q,
                'customer_intent': intent, 'answer1': a1, 'answer2': a2,
                'answer3': a3, 'keywords': kw, 'state': 'applying',
            })
            seq += 10
        ICP.set_param(_PARAM_KEY, _HQ_VERSION)
        return True


# (topic, difficulty, situation, question, intent, answer1, answer2, answer3, keywords)
_SEED_DATA = [
    # ===================== A. MÓNG =====================
    ('mong', 'kho', 'lo_rui_ro',
     'Móng đơn và móng cọc khác nhau như thế nào em?',
     'Khách đang lo chất lượng móng và muốn hiểu bản chất.',
     'Dạ anh, móng đơn và móng cốc về bản chất khá gần nhau, đều là loại móng chịu '
     'lực tại từng vị trí cột. Cách gọi "móng cốc" thường là cách gọi dân dụng, còn '
     'trong kỹ thuật hay gọi là móng đơn. Quan trọng nhất không phải tên gọi, mà là '
     'nền đất, tải trọng nhà và bản vẽ kết cấu có phù hợp không.',
     'Dạ phần móng không thể chọn theo cảm tính được anh. Nhà 1 tầng, 2 tầng, đất tốt '
     'hay đất yếu sẽ có phương án móng khác nhau. Bên em sẽ khảo sát thực tế, sau đó '
     'kỹ thuật mới tư vấn móng đơn, móng băng hay móng cọc. Làm đúng ngay từ đầu thì '
     'vừa an toàn vừa tránh lãng phí tiền cho anh.',
     'Dạ nếu anh muốn chắc chắn nhất thì bước đầu tiên nên cho bên em khảo sát đất và '
     'hiện trạng khu đất. Sau đó bên em mới tư vấn phương án móng phù hợp, không làm '
     'thiếu nhưng cũng không vẽ móng quá dư để đội chi phí cho anh.',
     'móng đơn, móng cốc, móng cọc, nền đất, kết cấu'),

    ('mong', 'kho', 'so_gia',
     'Móng băng và móng cọc móng nào đắt hơn?',
     'Khách so sánh chi phí giữa các loại móng.',
     'Dạ thông thường móng cọc sẽ đắt hơn móng băng vì có thêm chi phí ép cọc, vật tư '
     'cọc, máy móc và nhân công. Nhưng cũng tùy nền đất và quy mô nhà anh, không phải '
     'công trình nào cũng bắt buộc phải làm móng cọc.',
     'Dạ móng băng thường phù hợp với nền đất tương đối tốt, tải trọng vừa phải. Còn '
     'móng cọc dùng khi đất yếu hoặc công trình cần truyền tải sâu xuống lớp đất tốt '
     'hơn. Vì vậy móng cọc chi phí cao hơn, nhưng trong một số trường hợp thì bắt buộc '
     'phải làm để đảm bảo an toàn.',
     'Dạ bên em sẽ không tư vấn theo kiểu cái gì đắt hơn thì làm, mà tư vấn theo đúng '
     'nhu cầu kỹ thuật. Nếu đất anh làm móng băng được thì không cần ép cọc cho tốn '
     'tiền. Nhưng nếu đất yếu mà cố làm móng băng thì sau này rủi ro lún, nứt còn tốn '
     'kém hơn rất nhiều.',
     'móng băng, móng cọc, giá, ép cọc, đất yếu'),

    ('mong', 'kho', 'so_gia',
     'Móng cọc hết nhiều tiền không em?',
     'Khách sợ phát sinh tiền phần móng.',
     'Dạ móng cọc chắc chắn sẽ phát sinh chi phí cao hơn so với móng thông thường, vì '
     'có thêm cọc, máy ép, nhân công và kiểm tra tải trọng. Nhưng chi phí cụ thể phải '
     'dựa vào số lượng cọc, chiều sâu ép và diện tích nhà anh.',
     'Dạ phần móng cọc không nên báo đại theo mét vuông, vì mỗi khu đất có nền đất '
     'khác nhau. Có nhà ép ít cọc, có nhà phải ép sâu hơn. Bên em cần khảo sát thực '
     'tế rồi mới tính được phương án sát nhất cho anh.',
     'Dạ em hiểu anh đang lo chi phí móng đội lên nhiều. Bên em sẽ tính rõ từng phần '
     'cho anh: cọc bao nhiêu, ép cọc bao nhiêu, đài móng bao nhiêu. Cái gì cần làm thì '
     'làm, cái gì không cần thì bên em không đưa vào để tránh lãng phí cho anh.',
     'móng cọc, chi phí, ép cọc, khảo sát'),

    ('mong', 'kho', 'lo_rui_ro',
     'Móng đơn làm nhà 2 tầng thì có đảm bảo không em?',
     'Khách lo móng đơn không đủ an toàn cho nhà 2 tầng.',
     'Dạ móng đơn vẫn có thể làm được nhà 2 tầng nếu nền đất tốt, tải trọng phù hợp và '
     'kết cấu được tính toán đúng. Không phải cứ nhà 2 tầng là bắt buộc phải móng cọc.',
     'Dạ đảm bảo hay không phụ thuộc vào 3 yếu tố: nền đất, tải trọng công trình và '
     'thiết kế kết cấu. Nếu 3 yếu tố này phù hợp thì móng đơn vẫn an toàn. Nhưng nếu '
     'đất yếu mà vẫn cố làm móng đơn thì bên em sẽ không khuyến khích.',
     'Dạ bên em không tư vấn móng theo cảm tính. Nếu khảo sát thấy đất anh phù hợp làm '
     'móng đơn thì làm sẽ tiết kiệm chi phí. Còn nếu đất yếu, bên em sẽ báo rõ ràng để '
     'anh chuyển sang móng băng hoặc móng cọc cho an toàn lâu dài.',
     'móng đơn, nhà 2 tầng, an toàn, tải trọng, kết cấu'),

    # ===================== B. VẬT TƯ =====================
    ('vattu', 'trungbinh', 'nghi_ngo',
     'Cửa bên em dùng cửa Xingfa Việt, vậy cửa đó là như thế nào?',
     'Khách muốn biết chất lượng loại cửa được báo giá.',
     'Dạ Xingfa Việt là hệ nhôm kính được sản xuất trong nước theo kiểu dáng và hệ '
     'profile Xingfa. Loại này phổ biến, giá hợp lý, đáp ứng tốt nhu cầu nhà dân dụng '
     'nếu chọn đúng độ dày nhôm, phụ kiện và đơn vị gia công chuẩn.',
     'Dạ cửa Xingfa Việt có ưu điểm là chi phí vừa phải, mẫu mã đẹp, dễ bảo hành, dễ '
     'thay thế phụ kiện. Quan trọng là bên em phải dùng đúng hệ nhôm, đúng kính, đúng '
     'phụ kiện, không dùng hàng mỏng hoặc hàng kém chất lượng.',
     'Dạ nếu anh muốn phân khúc cao hơn thì có thể nâng cấp lên Xingfa Quảng Đông. Còn '
     'nếu xét về hiệu quả sử dụng và chi phí hợp lý thì Xingfa Việt vẫn là lựa chọn '
     'phù hợp cho đa số công trình nhà ở.',
     'cửa, xingfa việt, nhôm kính, vật tư'),

    ('vattu', 'trungbinh', 'so_gia',
     'Cửa Xingfa Quảng Đông có đắt hơn không?',
     'Khách so giá giữa 2 phân khúc cửa.',
     'Dạ có anh. Xingfa Quảng Đông thường đắt hơn Xingfa Việt vì là phân khúc cao hơn, '
     'độ hoàn thiện tốt hơn, thương hiệu mạnh hơn và giá vật tư đầu vào cao hơn.',
     'Dạ nếu so về giá thì Xingfa Quảng Đông cao hơn, nhưng đổi lại cảm giác cửa chắc '
     'hơn, độ sắc nét tốt hơn và phù hợp với những công trình muốn nâng cấp vật tư. '
     'Tuy nhiên mình nên cân đối ngân sách tổng thể, không nhất thiết hạng mục nào '
     'cũng phải chọn loại đắt nhất.',
     'Dạ nếu anh thích dùng Xingfa Quảng Đông, bên em có thể bóc tách phần chênh lệch '
     'riêng cho anh. Như vậy anh sẽ biết rõ nâng cấp cửa hết thêm bao nhiêu tiền, '
     'không bị mập mờ trong báo giá.',
     'cửa, xingfa quảng đông, giá, nâng cấp, chênh lệch'),

    ('vattu', 'trungbinh', 'chuan_bi_ky',
     'Anh muốn đổi vật tư sang cửa Xingfa Quảng Đông?',
     'Khách muốn nâng cấp vật tư, cần minh bạch chênh lệch.',
     'Dạ được anh. Phần này bên em có thể đổi vật tư theo nhu cầu của anh. Bên em sẽ '
     'tính phần chênh lệch giữa cửa Xingfa Việt và Xingfa Quảng Đông để anh duyệt '
     'trước khi đưa vào hợp đồng.',
     'Dạ nguyên tắc bên em là vật tư nào thay đổi thì phải thể hiện rõ trong phụ lục '
     'hoặc hợp đồng, ghi đúng chủng loại, quy cách, khối lượng và phần chênh lệch. Như '
     'vậy sau này thi công sẽ rõ ràng, không tranh cãi.',
     'Dạ nếu anh xác định dùng Xingfa Quảng Đông thì em sẽ cho kỹ thuật bóc riêng hạng '
     'mục cửa, sau đó gửi anh bảng so sánh 2 phương án để anh chọn. Cách này minh bạch '
     'nhất và giúp anh kiểm soát ngân sách.',
     'đổi vật tư, xingfa quảng đông, phụ lục, chênh lệch'),

    ('vattu', 'trungbinh', 'chuan_bi_ky',
     'Anh muốn sử dụng thiết bị vệ sinh loại Toto?',
     'Khách muốn nâng cấp thiết bị vệ sinh, cần báo chênh lệch.',
     'Dạ được anh. Toto là thương hiệu tốt, phân khúc cao hơn so với thiết bị vệ sinh '
     'phổ thông. Nếu anh muốn dùng Toto thì bên em sẽ tính phần chênh lệch theo mã sản '
     'phẩm cụ thể.',
     'Dạ thiết bị vệ sinh phải chọn theo mã, vì cùng thương hiệu Toto nhưng có nhiều '
     'phân khúc giá khác nhau. Bên em sẽ gửi anh danh sách mã hàng, hình ảnh, giá '
     'chênh để anh duyệt trước khi thi công.',
     'Dạ phần này rất dễ làm minh bạch. Trong hợp đồng mình ghi rõ thiết bị vệ sinh '
     'tiêu chuẩn là loại nào, nếu nâng lên Toto thì có phụ lục vật tư kèm mã sản phẩm. '
     'Anh kiểm soát được đúng loại hàng, bên em cũng thi công đúng cam kết.',
     'toto, thiết bị vệ sinh, mã sản phẩm, chênh lệch'),

    # ===================== C. KỸ THUẬT =====================
    ('kythuat', 'kho', 'lo_rui_ro',
     'Móng em làm vậy có đảm bảo không?',
     'Khách lo công ty làm móng theo kinh nghiệm, không bài bản.',
     'Dạ phần móng là hạng mục quan trọng nhất nên bên em không làm theo kinh nghiệm '
     'miệng. Móng phải dựa trên hiện trạng đất, tải trọng nhà và bản vẽ kết cấu. Khi '
     'làm đúng các bước này thì anh yên tâm hơn rất nhiều.',
     'Dạ bên em sẽ có kỹ thuật kiểm tra, có bản vẽ kết cấu, có khối lượng vật tư rõ '
     'ràng. Móng không phải chỗ để tiết kiệm sai cách, vì nếu sai thì sửa rất khó và '
     'rất tốn tiền.',
     'Dạ nếu anh còn lo, bên em có thể giải thích rõ cho anh từng phần: kích thước '
     'móng, thép dùng loại nào, bê tông mác bao nhiêu, vì sao chọn phương án đó. Anh '
     'hiểu rõ thì anh sẽ yên tâm hơn.',
     'móng, kỹ thuật, kết cấu, bản vẽ, đảm bảo'),

    ('kythuat', 'kho', 'nghi_ngo',
     'Anh thấy người ta bảo xây nhà trọn gói vật tư kém chất lượng?',
     'Khách nghi ngờ trọn gói dùng vật tư rẻ tiền.',
     'Dạ đúng là thị trường có đơn vị làm không chuẩn nên khách hàng lo là bình '
     'thường. Nhưng bên em làm rõ vật tư ngay từ hợp đồng, ghi chủng loại, thương '
     'hiệu, quy cách, không nói chung chung.',
     'Dạ xây nhà trọn gói không xấu, vấn đề là đơn vị thi công có minh bạch vật tư hay '
     'không. Nếu hợp đồng ghi rõ thép gì, xi măng gì, gạch gì, dây điện gì, thiết bị '
     'gì thì khách hàng hoàn toàn kiểm soát được.',
     'Dạ để anh yên tâm, bên em sẽ gửi bảng vật tư chi tiết. Khi thi công, vật tư về '
     'công trình anh có thể kiểm tra trực tiếp. Bên em không làm kiểu báo một đằng, '
     'đưa vật tư một nẻo.',
     'trọn gói, vật tư kém, minh bạch, hợp đồng'),

    ('kythuat', 'kho', 'lo_rui_ro',
     'Anh thấy xây nhà người ta làm bị nứt tường rất nhiều?',
     'Khách lo nhà bị nứt sau khi xây.',
     'Dạ nứt tường có nhiều nguyên nhân: nền móng, kết cấu, kỹ thuật xây, tô trát, bảo '
     'dưỡng hoặc co ngót vật liệu. Không thể nói cứ xây nhà là sẽ nứt, quan trọng là '
     'kiểm soát đúng kỹ thuật.',
     'Dạ bên em hạn chế nứt bằng cách kiểm soát từ móng, kết cấu, vật liệu xây, kỹ '
     'thuật tô trát và thời gian bảo dưỡng. Những vị trí dễ nứt như tiếp giáp cột - '
     'tường, mép cửa, tường dài đều phải xử lý kỹ hơn.',
     'Dạ nhà mới có thể có một số vết chân chim nhỏ do co ngót vật liệu, nhưng nứt kết '
     'cấu, nứt lớn, nứt bất thường thì phải kiểm tra ngay. Bên em có bảo hành nên anh '
     'không bị bỏ mặc sau khi bàn giao.',
     'nứt tường, co ngót, tô trát, bảo dưỡng, bảo hành'),

    ('kythuat', 'kho', 'lo_rui_ro',
     'Nhiều bên xây nhà toàn bị thấm, anh lo nhất việc đó?',
     'Khách lo nhà bị thấm (mái, WC, sân thượng).',
     'Dạ thấm là lỗi rất nhiều khách hàng lo, đặc biệt ở mái, WC, ban công, sân thượng '
     'và tường ngoài. Bên em sẽ xử lý chống thấm theo từng khu vực chứ không làm chung '
     'chung.',
     'Dạ chống thấm muốn bền thì phải làm đúng quy trình: tạo dốc, xử lý cổ ống, bo '
     'góc, chống thấm đủ lớp, thử nước trước khi lát gạch hoặc hoàn thiện. Nếu bỏ bước '
     'thì sau này rất dễ thấm.',
     'Dạ em nói thật, chống thấm không phải cứ quét vật liệu đắt tiền là xong. Quan '
     'trọng nhất là kỹ thuật thi công. Bên em kiểm soát kỹ từ phần thô để hạn chế rủi '
     'ro thấm sau này cho anh.',
     'thấm, chống thấm, mái, wc, sân thượng, quy trình'),

    ('kythuat', 'trungbinh', 'nghi_ngo',
     'Bê tông và xi măng bên em dùng loại nào, có chất lượng không?',
     'Khách muốn xác minh chất lượng vật tư kết cấu.',
     'Dạ bê tông và xi măng bên em dùng theo tiêu chuẩn đã ghi trong báo giá/hợp đồng. '
     'Các hạng mục kết cấu như móng, cột, dầm, sàn phải dùng đúng mác bê tông và đúng '
     'chủng loại xi măng.',
     'Dạ bê tông không được chọn tùy tiện. Từng hạng mục sẽ có mác bê tông phù hợp. '
     'Khi đổ bê tông, bên em kiểm soát nguồn cấp, thời gian đổ, độ sụt và quy trình '
     'bảo dưỡng sau đổ.',
     'Dạ để anh yên tâm, vật tư chính như thép, xi măng, bê tông đều có thể thể hiện '
     'rõ trong hợp đồng. Anh có quyền kiểm tra khi vật tư về công trình, bên em không '
     'làm mập mờ phần này.',
     'bê tông, xi măng, mác bê tông, kết cấu, chất lượng'),

    # ===================== D. HỢP ĐỒNG =====================
    ('baohanh', 'trungbinh', 'lo_rui_ro',
     'Bên em bảo hành như thế nào?',
     'Khách muốn biết chính sách bảo hành.',
     'Dạ bên em có chính sách bảo hành rõ trong hợp đồng. Các lỗi thuộc trách nhiệm '
     'thi công của bên em thì bên em tiếp nhận và xử lý theo đúng cam kết.',
     'Dạ bảo hành không phải nói miệng. Trong hợp đồng sẽ ghi rõ thời gian bảo hành, '
     'phạm vi bảo hành, hạng mục nào được bảo hành và trường hợp nào không thuộc bảo '
     'hành.',
     'Dạ sau bàn giao, nếu có vấn đề phát sinh thuộc lỗi thi công, anh báo lại cho bên '
     'em. Công ty sẽ kiểm tra nguyên nhân và có phương án xử lý. Đây là lý do mình nên '
     'làm với công ty có pháp nhân, hợp đồng rõ ràng.',
     'bảo hành, hợp đồng, phạm vi, bàn giao'),

    ('hopdong', 'trungbinh', 'chuan_bi_ky',
     'Bên em đặt cọc bao nhiêu?',
     'Khách muốn biết mức và mục đích đặt cọc.',
     'Dạ tiền đặt cọc tùy theo giá trị hợp đồng và tiến độ chuẩn bị hồ sơ, vật tư, '
     'nhân sự. Khoản này sẽ được ghi rõ trong hợp đồng và được khấu trừ vào giá trị '
     'thanh toán, không phải khoản thu riêng.',
     'Dạ đặt cọc là để hai bên xác nhận cam kết triển khai. Sau khi ký hợp đồng, công '
     'ty phải bố trí kỹ thuật, hồ sơ, tiến độ, nhân sự và kế hoạch vật tư cho công '
     'trình của anh.',
     'Dạ bên em sẽ ghi rõ số tiền đặt cọc, mục đích đặt cọc, tiến độ thanh toán và '
     'trách nhiệm hai bên. Anh không phải chuyển tiền khi chưa có hợp đồng rõ ràng.',
     'đặt cọc, hợp đồng, thanh toán, khấu trừ'),

    ('baohanh', 'kho', 'chuan_bi_ky',
     'Bên em cho giữ tiền bảo hành bao nhiêu?',
     'Khách muốn giữ lại tiền bảo hành để yên tâm.',
     'Dạ phần giữ bảo hành sẽ theo chính sách hợp đồng của công ty. Mức giữ phải hợp '
     'lý để vừa bảo vệ quyền lợi của anh, vừa đảm bảo dòng tiền thi công và quyết toán '
     'công trình.',
     'Dạ tiền giữ bảo hành không nên quá cao vì công ty đã phải hoàn thành toàn bộ '
     'công trình, vật tư, nhân công và bàn giao cho anh. Quan trọng là hợp đồng có '
     'điều khoản bảo hành rõ ràng.',
     'Dạ nếu anh muốn giữ bảo hành, bên em có thể trao đổi theo giá trị hợp đồng cụ '
     'thể. Nhưng mình cần giữ ở mức hợp lý, tránh ảnh hưởng đến tiến độ thanh toán và '
     'nghĩa vụ hai bên.',
     'giữ bảo hành, hợp đồng, quyết toán, dòng tiền'),

    ('baohanh', 'kho', 'phan_doi',
     'Bên em cho giữ tiền bảo hành thấp quá?',
     'Khách phản đối vì muốn giữ nhiều tiền bảo hành hơn.',
     'Dạ em hiểu anh muốn giữ tiền để yên tâm. Nhưng bảo hành không chỉ nằm ở số tiền '
     'giữ lại, mà nằm ở pháp nhân công ty, hợp đồng, uy tín và trách nhiệm sau bàn '
     'giao.',
     'Dạ nếu giữ quá cao thì sẽ ảnh hưởng đến dòng tiền hoàn thiện và quyết toán công '
     'trình. Bên em cần một mức hợp lý để hai bên cùng an toàn, không bên nào bị rủi '
     'ro quá lớn.',
     'Dạ mình có thể thống nhất rõ phạm vi bảo hành trong hợp đồng. Như vậy anh vẫn có '
     'cơ sở yêu cầu công ty xử lý nếu có lỗi, còn công ty cũng đảm bảo được chi phí '
     'vận hành sau bàn giao.',
     'giữ bảo hành thấp, phản đối, hợp đồng, pháp nhân'),

    ('hopdong', 'ratkho', 'phan_doi',
     'Anh không đồng ý đặt cọc tiền lúc ký hợp đồng đâu?',
     'Khách phản đối việc đặt cọc khi ký.',
     'Dạ em hiểu tâm lý của anh. Nhưng khi ký hợp đồng, công ty cũng phải bắt đầu bố '
     'trí nhân sự, kỹ thuật, tiến độ và kế hoạch vật tư. Vì vậy khoản đặt cọc là cam '
     'kết hai chiều, không phải bên em thu tiền trước rồi để đó.',
     'Dạ nếu không có đặt cọc thì công ty rất khó giữ lịch thi công, giữ giá vật tư và '
     'triển khai hồ sơ cho anh. Khoản đặt cọc sẽ được ghi rõ trong hợp đồng và khấu '
     'trừ vào giá trị công trình.',
     'Dạ anh có thể yên tâm vì mọi khoản tiền đều đi kèm hợp đồng, phiếu thu hoặc '
     'chuyển khoản công ty. Mình làm rõ ngay từ đầu thì quyền lợi của anh được bảo vệ '
     'tốt hơn.',
     'đặt cọc, không đồng ý, phản đối, hợp đồng'),

    ('hopdong', 'ratkho', 'nghi_ngo',
     'Đặt cọc xong các em trốn đi thì sao anh biết tìm ai?',
     'Khách nghi ngờ bị lừa, sợ mất tiền cọc.',
     'Dạ câu này anh hỏi rất thực tế. Vì vậy anh nên làm với công ty có pháp nhân, địa '
     'chỉ, hợp đồng, tài khoản công ty và người đại diện rõ ràng. Bên em không làm '
     'kiểu cá nhân nhận tiền rồi mất liên lạc.',
     'Dạ khi anh đặt cọc, khoản tiền sẽ được thể hiện trong hợp đồng và chứng từ thanh '
     'toán. Công ty có thông tin pháp lý rõ ràng, văn phòng, đội ngũ và công trình '
     'thực tế để anh kiểm chứng.',
     'Dạ nếu anh còn băn khoăn, bên em có thể gửi hồ sơ pháp lý công ty, hợp đồng mẫu '
     'và một số công trình đã thi công để anh kiểm tra trước khi quyết định.',
     'đặt cọc, trốn đi, pháp nhân, lừa đảo, hồ sơ pháp lý'),

    ('hopdong', 'kho', 'nghi_ngo',
     'Anh thấy người ta bảo xây nhà trọn gói hợp đồng không rõ ràng?',
     'Khách nghi ngờ hợp đồng trọn gói sơ sài.',
     'Dạ đúng là có nhiều đơn vị làm hợp đồng sơ sài nên khách hàng bị rủi ro. Bên em '
     'làm hợp đồng phải có phạm vi công việc, vật tư, tiến độ, thanh toán, bảo hành và '
     'các điều khoản phát sinh rõ ràng.',
     'Dạ hợp đồng càng rõ thì càng tốt cho cả hai bên. Anh biết mình được làm những '
     'gì, dùng vật tư gì, thanh toán ra sao. Công ty cũng có căn cứ để thi công đúng '
     'cam kết.',
     'Dạ trước khi ký, bên em sẽ gửi anh xem kỹ hợp đồng. Điều khoản nào chưa rõ thì '
     'mình chỉnh hoặc giải thích trước, không để đến lúc thi công mới tranh cãi.',
     'hợp đồng, không rõ ràng, phạm vi, điều khoản'),

    ('phatsinh', 'kho', 'lo_rui_ro',
     'Anh thấy họ bảo xây nhà trọn gói hay phát sinh nhiều chi phí lắm?',
     'Khách sợ bị phát sinh chi phí ngoài dự kiến.',
     'Dạ phát sinh thường xảy ra khi hợp đồng không rõ phạm vi, đất thực tế khác khảo '
     'sát, khách đổi vật tư, đổi thiết kế hoặc thêm hạng mục. Bên em sẽ làm rõ ngay từ '
     'đầu để hạn chế phát sinh.',
     'Dạ xây nhà trọn gói không có nghĩa là cái gì cũng miễn phí. Những gì nằm trong '
     'hợp đồng thì bên em làm đúng giá đã chốt. Những gì anh thay đổi thêm ngoài hợp '
     'đồng thì mới tính phát sinh và phải được anh duyệt trước.',
     'Dạ bên em không tự ý làm phát sinh rồi bắt khách trả tiền. Nếu có phát sinh, '
     'phải có lý do, khối lượng, đơn giá và xác nhận của anh trước khi triển khai.',
     'phát sinh, chi phí, trọn gói, duyệt trước'),

    ('hopdong', 'trungbinh', 'chuan_bi_ky',
     'Bên em có cam kết gì không?',
     'Khách muốn nghe cam kết của công ty.',
     'Dạ có anh. Cam kết quan trọng nhất là làm đúng hợp đồng, đúng vật tư, đúng phạm '
     'vi công việc, đúng tiến độ đã thống nhất và bảo hành theo điều khoản hợp đồng.',
     'Dạ bên em không cam kết bằng lời nói suông. Những nội dung quan trọng như vật '
     'tư, tiến độ, thanh toán, bảo hành, phát sinh đều phải thể hiện trong hợp đồng để '
     'hai bên cùng có căn cứ.',
     'Dạ nếu anh cần, bên em sẽ ghi rõ các cam kết chính trong hợp đồng. Làm nhà là '
     'việc lớn nên mọi thứ nên rõ ràng bằng văn bản, không nên chỉ nghe tư vấn miệng.',
     'cam kết, hợp đồng, vật tư, tiến độ, bảo hành'),

    ('giaca', 'trungbinh', 'so_gia',
     'Bên em có khuyến mại gì không?',
     'Khách muốn được giảm giá / ưu đãi.',
     'Dạ tùy từng thời điểm công ty sẽ có chính sách hỗ trợ khác nhau. Nhưng bên em ưu '
     'tiên báo giá thật, vật tư thật, phạm vi thật hơn là nâng giá lên rồi nói khuyến '
     'mại nhiều.',
     'Dạ nếu có chương trình hỗ trợ, bên em sẽ ghi rõ trong báo giá hoặc hợp đồng cho '
     'anh. Còn phần quan trọng nhất vẫn là tổng chi phí cuối cùng, vật tư sử dụng và '
     'chất lượng thi công.',
     'Dạ em có thể kiểm tra chính sách hiện tại cho anh. Nếu công trình của anh đủ '
     'điều kiện áp dụng, bên em sẽ đưa trực tiếp vào báo giá để anh nhìn thấy quyền '
     'lợi cụ thể.',
     'khuyến mại, ưu đãi, giảm giá, báo giá'),

    ('hopdong', 'kho', 'phan_doi',
     'Bên em có cho nợ không?',
     'Khách muốn thanh toán chậm / nợ tiền.',
     'Dạ nguyên tắc của bên em là thanh toán theo tiến độ thi công. Vì công ty phải '
     'ứng vật tư, nhân công và máy móc liên tục nên rất khó cho nợ dài.',
     'Dạ bên em có thể trao đổi phương án thanh toán phù hợp với dòng tiền của anh, '
     'nhưng phải đảm bảo không ảnh hưởng đến tiến độ công trình. Nếu chậm thanh toán '
     'quá lâu thì thi công rất dễ bị gián đoạn.',
     'Dạ mình nên thống nhất tiến độ thanh toán ngay từ đầu. Anh chủ động tài chính, '
     'công ty chủ động vật tư và nhân công, như vậy công trình chạy ổn định hơn.',
     'cho nợ, thanh toán, tiến độ, dòng tiền'),

    ('hopdong', 'ratkho', 'lo_rui_ro',
     'Bên em có bỏ dở công trình không?',
     'Khách sợ công ty nhận tiền rồi bỏ dở.',
     'Dạ bên em là công ty làm lâu dài, có pháp nhân và hợp đồng rõ ràng nên không thể '
     'làm kiểu bỏ dở công trình. Tiến độ và trách nhiệm thi công đều được ghi trong '
     'hợp đồng.',
     'Dạ trường hợp công trình bị dừng thường do tranh chấp phạm vi, chậm thanh toán, '
     'thay đổi thiết kế hoặc phát sinh chưa thống nhất. Vì vậy bên em luôn làm rõ hợp '
     'đồng và tiến độ thanh toán ngay từ đầu.',
     'Dạ nếu hai bên thực hiện đúng hợp đồng thì không có lý do gì công ty bỏ dở. Bên '
     'em cũng cần uy tín, công trình thực tế và khách hàng giới thiệu thêm, nên việc '
     'hoàn thành công trình là lợi ích của cả hai bên.',
     'bỏ dở, công trình, pháp nhân, uy tín'),

    ('tiendo', 'kho', 'lo_rui_ro',
     'Tiến độ bên em làm như thế nào, anh thấy nhiều bên làm chậm, không có thợ, bỏ '
     'dở công trình?',
     'Khách lo chậm tiến độ, thiếu thợ.',
     'Dạ tiến độ sẽ được lập theo từng giai đoạn: phần móng, phần thô, mái, hoàn thiện '
     'và bàn giao. Bên em không nói chung chung mà sẽ có mốc thi công cụ thể để anh '
     'theo dõi.',
     'Dạ chậm tiến độ thường do thiếu thợ, thiếu vật tư, thay đổi thiết kế, thời tiết '
     'hoặc thanh toán không đúng tiến độ. Bên em sẽ chủ động kế hoạch nhân sự và vật '
     'tư trước để hạn chế tình trạng đó.',
     'Dạ trong hợp đồng sẽ có tiến độ dự kiến và trách nhiệm của hai bên. Anh bàn giao '
     'mặt bằng, thanh toán đúng tiến độ; bên em bố trí thợ, vật tư và kỹ thuật để công '
     'trình chạy liên tục.',
     'tiến độ, chậm, thiếu thợ, mốc thi công'),

    # ===================== E. THỢ THI CÔNG =====================
    ('tho', 'trungbinh', 'nghi_ngo',
     'Thợ bên em lấy ở đâu?',
     'Khách muốn biết nguồn thợ có ổn định, có kiểm soát.',
     'Dạ thợ bên em là các đội thợ đã làm quen với quy trình của công ty, không phải '
     'ra ngoài gọi đại từng đội lạ về làm. Công ty cần đội thợ ổn định để kiểm soát '
     'chất lượng.',
     'Dạ xây nhà quan trọng không chỉ là có thợ, mà thợ phải hiểu tiêu chuẩn thi công '
     'của công ty. Đội nào làm không đạt thì bên em không giữ lâu dài, vì ảnh hưởng '
     'trực tiếp đến uy tín công ty.',
     'Dạ bên em có đội kỹ thuật quản lý và kiểm tra công việc của thợ. Thợ thi công, '
     'nhưng công ty chịu trách nhiệm cuối cùng với khách hàng nên không thể để thợ làm '
     'tự do không kiểm soát.',
     'thợ, đội thợ, kiểm soát, quy trình'),

    ('tho', 'de', 'lo_rui_ro',
     'Thợ có ăn ở tại chỗ không?',
     'Khách quan tâm việc thợ ở lại công trình.',
     'Dạ tùy công trình và điều kiện mặt bằng anh. Nếu công trình phù hợp, thợ có thể '
     'ăn ở gần hoặc tại công trình để thuận tiện thi công. Nếu mặt bằng không cho phép '
     'thì công ty sẽ bố trí phương án khác.',
     'Dạ việc thợ ở lại phải đảm bảo an toàn, vệ sinh, không ảnh hưởng hàng xóm và quy '
     'định khu vực. Bên em sẽ xem điều kiện thực tế rồi trao đổi phương án phù hợp với '
     'anh.',
     'Dạ mục tiêu là đảm bảo tiến độ thi công, nhưng vẫn phải gọn gàng, an toàn và '
     'không gây phiền cho gia đình cũng như hàng xóm xung quanh.',
     'thợ, ăn ở, công trình, mặt bằng'),

    ('tho', 'trungbinh', 'nghi_ngo',
     'Thợ bên em tay nghề có cao không?',
     'Khách nghi ngờ tay nghề thợ.',
     'Dạ thợ bên em phải làm theo tiêu chuẩn và quy trình của công ty. Tay nghề không '
     'chỉ nhìn ở việc xây nhanh, mà còn ở độ chính xác, độ phẳng, độ chắc và khả năng '
     'xử lý chi tiết.',
     'Dạ công ty không giao toàn bộ công trình cho thợ tự quyết. Có kỹ thuật kiểm tra '
     'các hạng mục quan trọng nên chất lượng không phụ thuộc hoàn toàn vào cảm tính '
     'của thợ.',
     'Dạ anh có thể xem công trình thực tế hoặc hình ảnh thi công để đánh giá. Bên em '
     'làm lâu dài nên đội thợ phải giữ được chất lượng ổn định, không thể làm ẩu rồi '
     'bỏ đi.',
     'thợ, tay nghề, kỹ thuật, chất lượng'),

    ('tho', 'trungbinh', 'lo_rui_ro',
     'Đi xa thợ em có đi không, công ty có nhận công trình ở xa không?',
     'Khách ở xa, lo công ty không nhận hoặc làm không tới.',
     'Dạ bên em có nhận công trình ở xa nếu điều kiện thi công, quy mô và phương án '
     'nhân sự phù hợp. Khi đi xa thì công ty phải tính kỹ chi phí di chuyển, ăn ở và '
     'quản lý công trình.',
     'Dạ công trình xa không phải bên em ngại, nhưng phải tổ chức bài bản hơn: đội '
     'thợ, kỹ thuật, vật tư, chỗ ở và tiến độ. Nếu làm không kỹ thì rất dễ phát sinh '
     'chi phí và chậm tiến độ.',
     'Dạ anh gửi em vị trí công trình, diện tích và nhu cầu xây dựng. Bên em sẽ kiểm '
     'tra xem có nhận được không và nếu nhận thì báo rõ phương án thi công cho anh '
     'ngay từ đầu.',
     'công trình xa, thợ đi xa, nhân sự, tiến độ'),

    ('tho', 'kho', 'lo_rui_ro',
     'Anh muốn tìm thợ ở gần để sau này bảo hành cho dễ?',
     'Khách muốn thợ gần để dễ bảo hành, ngại làm với công ty xa.',
     'Dạ em hiểu ý anh. Nhưng bảo hành không phụ thuộc hoàn toàn vào thợ ở gần, mà phụ '
     'thuộc vào trách nhiệm của công ty. Thợ gần mà không có hợp đồng rõ ràng thì khi '
     'có vấn đề vẫn rất khó gọi họ quay lại.',
     'Dạ làm với công ty thì anh có đầu mối chịu trách nhiệm rõ ràng. Sau này nếu có '
     'vấn đề, anh làm việc với công ty chứ không phải tự đi tìm từng ông thợ.',
     'Dạ thợ gần có cái tiện, nhưng cái quan trọng hơn là ai chịu trách nhiệm cuối '
     'cùng. Bên em có hợp đồng, bảo hành và quy trình tiếp nhận nên anh yên tâm hơn so '
     'với thuê thợ tự do.',
     'thợ gần, bảo hành, trách nhiệm, công ty'),

    ('tho', 'trungbinh', 'lo_rui_ro',
     'Bên em có kỹ thuật xuống giám sát công trình không?',
     'Khách muốn có người giám sát chất lượng.',
     'Dạ có anh. Bên em có kỹ thuật theo dõi và kiểm tra các giai đoạn thi công quan '
     'trọng, đặc biệt là móng, cột, dầm, sàn, điện nước, chống thấm và hoàn thiện.',
     'Dạ kỹ thuật không nhất thiết lúc nào cũng đứng 24/24 tại công trình, nhưng các '
     'mốc quan trọng phải kiểm tra. Thợ thi công theo đội, kỹ thuật kiểm soát chất '
     'lượng và xử lý vấn đề phát sinh.',
     'Dạ nếu anh cần, bên em có thể thống nhất các mốc nghiệm thu nội bộ để anh cùng '
     'kiểm tra: trước khi đổ bê tông, trước khi tô trát, trước khi chống thấm, trước '
     'khi lát gạch và trước bàn giao.',
     'kỹ thuật, giám sát, nghiệm thu, mốc thi công'),

    ('tho', 'trungbinh', 'chuan_bi_ky',
     'Bên khách hàng có được giám sát chéo không?',
     'Khách muốn được quyền giám sát công trình.',
     'Dạ được anh. Khách hàng hoàn toàn có quyền theo dõi, kiểm tra và phản hồi trong '
     'quá trình thi công. Bên em rất ủng hộ việc giám sát minh bạch.',
     'Dạ anh có thể tự giám sát hoặc nhờ người có chuyên môn kiểm tra. Tuy nhiên mọi '
     'góp ý kỹ thuật nên trao đổi qua đầu mối của công ty để tránh chỉ đạo trực tiếp '
     'thợ gây rối quy trình thi công.',
     'Dạ nguyên tắc là khách hàng được giám sát, công ty chịu trách nhiệm thi công. '
     'Nếu có vấn đề, anh phản ánh cho kỹ thuật hoặc quản lý công trình để xử lý đúng '
     'quy trình, không để mỗi người chỉ đạo một kiểu.',
     'giám sát chéo, khách hàng, kiểm tra, minh bạch'),
]
