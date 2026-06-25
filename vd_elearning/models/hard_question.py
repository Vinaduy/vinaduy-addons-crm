# -*- coding: utf-8 -*-
"""KHO CÂU HỎI KHÓ và KỊCH BẢN TRẢ LỜI SALE (THƯ VIỆN - Câu hỏi khó).

Lưu toàn bộ câu hỏi khó khách hay hỏi khi tư vấn xây nhà trọn gói + 3 câu trả
lời mẫu (nhanh / giải thích sâu / dẫn dắt chốt). Nhân viên tìm theo từ khóa,
lọc theo chủ đề - mức độ - tình huống khách. Hiển thị qua nút filter "THƯ VIỆN
- Câu hỏi khó" cạnh các khóa học trong trang Học online.

Seed idempotent theo PHIÊN BẢN (ir.config_parameter). Bump version -> seed lại.
"""
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

_HQ_VERSION = 'v2'
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

    def _vd_is_admin(self):
        return (self.env.user.has_group('base.group_system')
                or self.env.user.has_group('vd_crm_lead.vd_crm_group_admin'))

    def _vd_question_payload(self, r):
        """1 câu hỏi -> dict cho Dialog (dùng chung load + save)."""
        return {
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
        }

    @api.model
    def vd_library_load(self):
        """Trả dữ liệu cho Dialog THƯ VIỆN (chỉ câu đang áp dụng / đã duyệt)."""
        recs = self.sudo().search([('state', 'in', ('approved', 'applying'))])
        return {
            'is_admin': self._vd_is_admin(),
            'topics': [{'key': k, 'label': v} for k, v in TOPICS],
            'difficulties': [{'key': k, 'label': v} for k, v in DIFFS],
            'situations': [{'key': k, 'label': v} for k, v in SITUATIONS],
            'items': [self._vd_question_payload(r) for r in recs],
        }

    @api.model
    def vd_save_question(self, qid, vals):
        """Admin sửa NỘI DUNG 1 câu hỏi + 3 câu trả lời. Trả lại payload đã cập nhật
        để Dialog thay tại chỗ (không cần load lại toàn bộ). Chỉ admin."""
        if not self._vd_is_admin():
            raise AccessError('Chỉ admin được sửa câu hỏi.')
        rec = self.sudo().browse(int(qid))
        if not rec.exists():
            raise ValidationError('Câu hỏi không tồn tại.')
        vals = vals or {}
        field_map = {
            'question': 'question',
            'intent': 'customer_intent',
            'a1': 'answer1',
            'a2': 'answer2',
            'a3': 'answer3',
            'keywords': 'keywords',
        }
        write_vals = {fld: (vals[key] or '')
                      for key, fld in field_map.items() if key in vals}
        if 'question' in write_vals and not write_vals['question'].strip():
            raise ValidationError('Câu hỏi không được để trống.')
        if write_vals:
            rec.write(write_vals)
        return self._vd_question_payload(rec)

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
    ('mong', 'kho', 'so_gia',
     'Móng băng và móng cọc móng nào đắt hơn?',
     'Khách so sánh chi phí giữa các loại móng.',
     'Dạ em nói thật với anh, hai loại móng này phần dầm móng, đế móng, đài móng thì '
     'khối lượng bê tông với sắt thép gần như tương đương nhau. Cái khác là móng cọc '
     'có thêm phần cọc ép xuống đất. Cho nên móng cọc chắc chắn đắt hơn móng băng, '
     'nhưng chỉ đắt hơn đúng ở phần cọc thôi anh ạ.',
     'Dạ anh cứ hình dung cho dễ: phần móng nổi lên trên hai loại làm gần như nhau, '
     'tốn vật tư như nhau. Móng băng dùng khi đất tương đối tốt, còn móng cọc là khi '
     'đất yếu phải đóng cọc xuống lớp đất cứng bên dưới cho chắc. Vì có thêm cọc nên '
     'móng cọc đội thêm tiền, nhưng đổi lại nhà đứng vững, không lo lún nứt về sau.',
     'Dạ anh yên tâm, bên em không tư vấn kiểu cái nào đắt thì làm đâu. Đất nhà anh '
     'làm móng băng được thì em khuyên làm móng băng cho đỡ tốn. Còn nếu đất yếu mà cố '
     'làm móng băng thì sau này lún nứt sửa còn tốn gấp mấy lần. Bên em khảo sát xong '
     'sẽ nói thẳng với anh nên làm loại nào.',
     'móng băng, móng cọc, giá, ép cọc, đất yếu'),

    ('mong', 'kho', 'so_gia',
     'Móng cọc hết nhiều tiền không em?',
     'Khách sợ phát sinh tiền phần móng.',
     'Dạ móng cọc thì chắc chắn đắt hơn móng băng kha khá đấy anh, tại vì phát sinh '
     'thêm cái phần cọc ép xuống dưới đất. Nhưng anh đừng lo, đắt là đắt đúng phần cọc '
     'thôi, chứ phần móng bên trên vẫn như bình thường.',
     'Dạ tiền cọc nhiều hay ít còn tùy đất nhà mình ép nông hay sâu, số lượng cọc bao '
     'nhiêu nữa anh. Có nhà ép vài mét đã tới đất cứng, có nhà phải ép sâu hơn. Bên em '
     'phải xuống xem đất thực tế rồi mới tính sát được cho anh, chứ báo đại theo mét '
     'vuông là không chuẩn đâu.',
     'Dạ em hiểu anh lo phần móng đội tiền lên. Bên em làm là tính rõ ràng từng khoản '
     'cho anh xem: cọc bao nhiêu, công ép bao nhiêu, đài móng bao nhiêu. Cái gì cần '
     'thì mình làm cho chắc, cái gì không cần em không vẽ thêm để anh đỡ tốn.',
     'móng cọc, chi phí, ép cọc, khảo sát'),

    ('mong', 'kho', 'so_gia',
     'Tiền cọc hết bao nhiêu tiền em?',
     'Khách muốn biết chi phí ép cọc cụ thể.',
     'Dạ thật ra giờ chưa thể chốt chính xác tiền ép cọc được anh ạ, tại nguyên tắc ép '
     'cọc là phải ép cho tới nền đất cứng mới dừng, mà chiều sâu thì phải ép rồi mới '
     'biết. Nhưng để anh dễ hình dung, thông thường nó rơi vào khoảng tầm 70 đến 100 '
     'triệu cho phần ép cọc.',
     'Dạ muốn biết chính xác thì có hai cách: một là ép thử, hai là khoan địa chất. '
     'Nhưng khoan địa chất tốn kém lắm nên bên em ưu tiên ép thử, hoặc nhìn nhà hàng '
     'xóm xung quanh người ta ép sâu bao nhiêu thì nhà mình áng theo. Thông thường một '
     'đoạn cọc tối thiểu dài tầm 5 đến 6 mét anh ạ.',
     'Dạ em tính nhẩm cho anh dễ hiểu nhé: ví dụ nhà mình có 10 đài cọc, mỗi đài ép 3 '
     'cọc là 30 cọc, mỗi cọc 5 mét thì khoảng 150 mét dài, nhân với đơn giá tầm 250 '
     'nghìn một mét, cộng thêm chi phí cá ép nữa thì rơi vào khoảng 70 triệu tối thiểu, '
     'nhiều thì tới 100 triệu. Khảo sát xong em báo con số sát nhất cho anh.',
     'tiền cọc, ép cọc, chi phí, khoan địa chất, ép thử'),

    ('mong', 'kho', 'lo_rui_ro',
     'Móng đơn làm nhà 2 tầng thì có đảm bảo không em?',
     'Khách lo móng đơn không đủ an toàn cho nhà 2 tầng.',
     'Dạ đảm bảo chứ anh, anh cứ yên tâm. Bên em làm rất nhiều nhà 2 tầng móng đơn rồi, '
     'vẫn chắc chắn bình thường, với điều kiện là nền đất nhà mình phải cứng. Không '
     'phải cứ nhà 2 tầng là bắt buộc móng cọc đâu anh.',
     'Dạ nói thật với anh, móng đơn làm nhà 2 tầng là quá ổn nếu đất tốt. Còn nếu anh '
     'có điều kiện đầu tư thêm một chút thì làm móng băng sẽ chắc chắn hơn nữa. Riêng '
     'đất yếu thì bên em chắc chắn phải ép cọc cho anh, chứ không làm liều.',
     'Dạ bên em xuống khảo sát đất xong sẽ nói thẳng. Đất cứng thì móng đơn là đủ, làm '
     'cho anh tiết kiệm. Đất yếu thì em khuyên anh chuyển móng băng hoặc móng cọc cho '
     'an toàn lâu dài, chứ em không bao giờ để nhà anh có rủi ro.',
     'móng đơn, nhà 2 tầng, an toàn, móng băng, ép cọc'),

    ('mong', 'trungbinh', 'lo_rui_ro',
     'Nhà anh 2 đến 3 tầng có nên ép cọc khoan nhồi không, cọc khoan nhồi có đắt không?',
     'Khách phân vân giữa cọc ép sẵn và cọc khoan nhồi.',
     'Dạ nhà 2 đến 3 tầng thì anh làm cọc ép sẵn là đủ chắc rồi, không cần khoan nhồi '
     'đâu anh. Cọc khoan nhồi tốn kém, thường chỉ nhà từ 5 tầng trở lên người ta mới '
     'làm.',
     'Dạ cọc khoan nhồi chịu tải rất lớn nên hợp với nhà cao tầng, công trình lớn. Còn '
     'nhà dân 2 đến 3 tầng mà làm khoan nhồi là thừa, phí tiền của anh. Bên em khuyên '
     'làm cọc ép sẵn cho vừa chắc vừa hợp lý chi phí.',
     'Dạ anh cứ yên tâm, nhà mình 2 đến 3 tầng bên em làm cọc ép sẵn là chuẩn nhất '
     'rồi. Em không tư vấn anh làm khoan nhồi cho tốn tiền, cái gì cần mới làm thôi '
     'anh ạ.',
     'cọc khoan nhồi, cọc ép, nhà 2-3 tầng, nhà 5 tầng'),

    # ===================== B. VẬT TƯ =====================
    ('vattu', 'trungbinh', 'nghi_ngo',
     'Cửa bên em dùng cửa Xingfa Việt, vậy cửa đó là như thế nào?',
     'Khách muốn biết chất lượng loại cửa được báo giá.',
     'Dạ cửa Xingfa Việt là hệ nhôm kính sản xuất trong nước theo kiểu Xingfa, dùng '
     'cho nhà dân mình là đẹp và bền anh ạ. Quan trọng là chọn đúng độ dày nhôm, đúng '
     'phụ kiện thì dùng rất ổn, anh cứ yên tâm.',
     'Dạ loại này được cái giá hợp lý, mẫu mã đẹp, sau này hỏng phụ kiện thì thay cũng '
     'dễ. Bên em luôn dùng đúng hệ nhôm, đúng kính, đúng phụ kiện chứ không bao giờ '
     'lắp hàng mỏng, hàng kém cho anh đâu.',
     'Dạ nếu anh muốn sang hơn nữa thì mình nâng lên Xingfa Quảng Đông. Còn xét cho '
     'nhà ở bình thường thì Xingfa Việt là quá hợp lý rồi anh, vừa đẹp vừa tiết kiệm.',
     'cửa, xingfa việt, nhôm kính, vật tư'),

    ('vattu', 'trungbinh', 'so_gia',
     'Cửa Xingfa Quảng Đông có đắt hơn không?',
     'Khách so giá giữa 2 phân khúc cửa.',
     'Dạ có đắt hơn anh, cửa Xingfa Quảng Đông thường đắt hơn Xingfa Việt khoảng 300 '
     'đến 500 nghìn thôi, nhưng đổi lại cửa chắc tay hơn, sắc nét hơn, thương hiệu '
     'mạnh hơn.',
     'Dạ chênh tầm 300 đến 500 nghìn nhưng cảm giác đóng mở chắc chắn hơn hẳn, nhìn '
     'sang hơn, hợp với nhà muốn đầu tư đẹp. Tuy nhiên anh cứ cân đối tổng thể, không '
     'nhất thiết hạng mục nào cũng phải chọn loại đắt nhất đâu.',
     'Dạ nếu anh thích Quảng Đông, bên em bóc riêng phần chênh lệch cho anh xem rõ '
     'ràng, nâng cấp hết thêm bao nhiêu anh nắm được hết, không mập mờ tí nào.',
     'cửa, xingfa quảng đông, giá, 300k, 500k, chênh lệch'),

    ('vattu', 'trungbinh', 'chuan_bi_ky',
     'Anh muốn đổi vật tư sang cửa Xingfa Quảng Đông?',
     'Khách muốn nâng cấp vật tư, cần minh bạch chênh lệch.',
     'Dạ được anh, cái này dễ thôi. Anh thích Quảng Đông thì bên em đổi, em tính phần '
     'chênh lệch giữa Xingfa Việt và Quảng Đông cho anh duyệt rồi đưa vào hợp đồng cho '
     'rõ ràng.',
     'Dạ nguyên tắc bên em là đổi vật tư gì thì ghi rõ trong phụ lục hợp đồng: đúng '
     'chủng loại, quy cách, khối lượng, phần chênh bao nhiêu đều minh bạch. Sau này '
     'thi công khỏi tranh cãi, anh yên tâm.',
     'Dạ em cho kỹ thuật bóc riêng hạng mục cửa, gửi anh bảng so sánh hai phương án để '
     'anh chọn. Cách này anh nắm được tiền nong rõ ràng nhất.',
     'đổi vật tư, xingfa quảng đông, phụ lục, chênh lệch'),

    ('vattu', 'trungbinh', 'chuan_bi_ky',
     'Anh muốn sử dụng thiết bị vệ sinh loại Toto?',
     'Khách muốn nâng cấp thiết bị vệ sinh, cần báo chênh lệch.',
     'Dạ được anh, Toto là hàng tốt, sang hơn loại phổ thông. Anh muốn dùng Toto thì '
     'bên em tính phần chênh lệch theo đúng mã sản phẩm cho anh.',
     'Dạ thiết bị vệ sinh phải chọn theo mã anh ạ, vì cùng là Toto nhưng nhiều mức giá '
     'lắm. Bên em gửi anh danh sách mã hàng, hình ảnh, giá chênh để anh chọn rồi mới '
     'thi công.',
     'Dạ phần này làm minh bạch rất dễ. Hợp đồng ghi rõ thiết bị tiêu chuẩn là loại '
     'nào, nâng lên Toto thì có phụ lục kèm mã sản phẩm. Anh nắm đúng loại hàng, bên '
     'em làm đúng cam kết.',
     'toto, thiết bị vệ sinh, mã sản phẩm, chênh lệch'),

    # ===================== C. KỸ THUẬT =====================
    ('kythuat', 'kho', 'lo_rui_ro',
     'Móng em làm vậy có đảm bảo không?',
     'Khách lo công ty làm móng không đảm bảo.',
     'Dạ anh hoàn toàn yên tâm, móng bên em làm là đảm bảo. Bên em cam kết bảo hành '
     'kết cấu cho anh tận 5 năm, kết cấu được tính toán chịu được rung lắc, động đất, '
     'tải trọng cao nên anh cứ yên tâm.',
     'Dạ phần móng là quan trọng nhất nên bên em không làm theo kinh nghiệm miệng đâu '
     'anh. Có bản vẽ kết cấu, có kỹ thuật tính toán đàng hoàng, đảm bảo nhà đứng vững '
     'lâu dài. Bên em còn cam kết bảo hành kết cấu 5 năm bằng hợp đồng hẳn hoi.',
     'Dạ anh còn lo thì em giải thích kỹ cho anh từng phần: móng kích thước bao nhiêu, '
     'thép loại gì, bê tông mác bao nhiêu. Anh hiểu rõ rồi thì anh sẽ yên tâm là bên '
     'em làm chắc thật chứ không nói suông.',
     'móng, đảm bảo, bảo hành kết cấu, 5 năm, động đất, chịu tải'),

    ('kythuat', 'kho', 'nghi_ngo',
     'Anh thấy người ta bảo xây nhà trọn gói vật tư kém chất lượng?',
     'Khách nghi ngờ trọn gói dùng vật tư rẻ tiền.',
     'Dạ anh yên tâm, bên em làm việc có thương hiệu, có uy tín trên thị trường, nhiều '
     'người biết đến. Vật tư bên em cam kết đúng theo hợp đồng, anh cứ đọc danh mục '
     'vật tư là thấy, toàn hàng chất lượng cao.',
     'Dạ thị trường thì cũng có chỗ làm ăn không đàng hoàng nên anh lo là đúng thôi. '
     'Nhưng bên em khác, vật tư ghi rõ trong hợp đồng từng loại thép, xi măng, gạch, '
     'dây điện, thiết bị. Bên em còn mong làm xong nhà đẹp để hàng xóm láng giềng '
     'người ta thấy rồi giới thiệu thêm khách cho em nữa cơ mà.',
     'Dạ bên em khẳng định cam kết vật tư tốt, đúng hợp đồng. Khi vật tư về công trình '
     'anh kiểm tra trực tiếp được hết. Bên em làm thương hiệu lâu dài nên không bao '
     'giờ báo một đằng đưa vật tư một nẻo đâu anh.',
     'trọn gói, vật tư, thương hiệu, uy tín, hợp đồng'),

    ('kythuat', 'kho', 'lo_rui_ro',
     'Anh thấy xây nhà người ta làm bị nứt tường rất nhiều?',
     'Khách lo nhà bị nứt sau khi xây.',
     'Dạ cái này anh yên tâm, bên em làm tất cả những điểm tiếp giáp giữa bê tông với '
     'tường xây đều đóng lưới cẩn thận hết. Nhờ vậy mà hạn chế nứt rất tốt anh ạ.',
     'Dạ nứt tường phần lớn là do thợ làm ẩu không đóng lưới ở chỗ tiếp giáp. Bên em '
     'thì những đường dây điện khi đục tường ra cũng đóng lưới lại cẩn thận trước khi '
     'tô. Em thấy nhiều thợ địa phương họ bỏ qua bước này nên nhà mới xây đã nứt.',
     'Dạ nhà mới đôi khi có vài vết chân chim nhỏ do co ngót là bình thường, nhưng nứt '
     'do kỹ thuật ẩu thì bên em không để xảy ra. Bên em làm kỹ từ đầu, lại có bảo hành '
     'nên anh cứ yên tâm, không bị bỏ mặc sau bàn giao đâu.',
     'nứt tường, đóng lưới, tiếp giáp, dây điện, bảo hành'),

    ('kythuat', 'kho', 'lo_rui_ro',
     'Nhiều bên xây nhà toàn bị thấm, anh lo nhất việc đó?',
     'Khách lo nhà bị thấm (mái, WC, sân thượng).',
     'Dạ anh yên tâm về vấn đề này, bên em làm chống thấm rất cẩn thận. Thật ra bên em '
     'cũng không muốn để xảy ra bảo hành thấm chút nào, vì bảo hành thấm khổ lắm, phải '
     'đục hết nền nhà vệ sinh, tháo thiết bị ra làm lại từ đầu.',
     'Dạ trong quá trình xây, bên em chống thấm bằng màng PE hai lớp với sika đàng '
     'hoàng, rồi ngâm nước thử nguyên 7 ngày. Trong 7 ngày đó mà không có một hiện '
     'tượng thấm nào thì bên em mới cho ốp lát, chứ không làm vội.',
     'Dạ em nói thật, chống thấm không phải cứ quét vật liệu đắt tiền là xong, quan '
     'trọng nhất là làm đúng quy trình và thử nước kỹ. Bên em làm kỹ ngay từ phần thô '
     'nên anh cứ yên tâm, vấn đề chống thấm bên em làm rất tốt.',
     'thấm, chống thấm, màng pe, sika, ngâm nước 7 ngày'),

    ('kythuat', 'trungbinh', 'nghi_ngo',
     'Bê tông bên em dùng loại nào, có chất lượng không?',
     'Khách muốn xác minh chất lượng vật tư kết cấu.',
     'Dạ bên em dùng bê tông mác 300 anh ạ, đây là mác tốt nhất hiện nay trên thị '
     'trường, độ cứng rất cao. Anh cứ yên tâm về phần này.',
     'Dạ nhiều thợ địa phương xây nhà dân họ vẫn dùng mác 200, 250 thôi, nhưng bên em '
     'làm mác 300 cho chắc chắn. Các hạng mục kết cấu như móng, cột, dầm, sàn đều dùng '
     'đúng mác này hết.',
     'Dạ để anh yên tâm, vật tư chính như thép, xi măng, bê tông bên em đều ghi rõ '
     'trong hợp đồng. Khi đổ bê tông bên em kiểm soát kỹ nguồn cấp, độ sụt, bảo dưỡng '
     'sau đổ. Anh kiểm tra lúc nào cũng được, bên em không mập mờ đâu.',
     'bê tông, mác 300, xi măng, kết cấu, chất lượng'),

    # ===================== D. HỢP ĐỒNG - BẢO HÀNH - PHÁT SINH - TIẾN ĐỘ =====================
    ('baohanh', 'trungbinh', 'lo_rui_ro',
     'Bên em bảo hành như thế nào?',
     'Khách muốn biết chính sách bảo hành.',
     'Dạ bên em bảo hành kết cấu cho anh 5 năm, còn vật tư cơ bản là 2 năm anh ạ. Cái '
     'này ghi rõ trong hợp đồng hẳn hoi.',
     'Dạ anh cứ yên tâm, kết cấu mà qua được khoảng 1 năm đầu không có vấn đề gì thì về '
     'sau gần như không bao giờ có vấn đề nữa. Còn mấy thứ lặt vặt như bóng đèn, bóng '
     'điện hỏng thì bên em thay cho anh.',
     'Dạ làm nhà là việc lớn nên bảo hành phải rõ ràng bằng hợp đồng. Sau bàn giao có '
     'gì thuộc lỗi thi công anh cứ báo, bên em về xử lý. Đây cũng là lý do anh nên làm '
     'với công ty có pháp nhân, hợp đồng đàng hoàng.',
     'bảo hành, kết cấu 5 năm, vật tư 2 năm, bóng đèn'),

    ('hopdong', 'trungbinh', 'chuan_bi_ky',
     'Bên em đặt cọc bao nhiêu?',
     'Khách muốn biết mức và mục đích đặt cọc.',
     'Dạ khi đã ký hợp đồng thì chắc chắn hai bên phải có đặt cọc anh ạ, thì bên em mới '
     'làm hồ sơ bản vẽ thiết kế cho anh được. Chi phí đặt cọc bên em là 50 triệu, '
     'khoản này khấu trừ vào giá trị công trình chứ không phải thu riêng.',
     'Dạ anh cứ hình dung như mua đất hay mua ô tô, mình cũng phải đặt cọc rồi ký hợp '
     'đồng thì cái hợp đồng đó mới có giá trị. Đặt cọc là để bên em biết gia đình mình '
     'có thiện chí làm thật, thì phòng thiết kế và phòng thi công mới sắp xếp thợ '
     'thuyền được cho anh.',
     'Dạ nói thật với anh, riêng tiền thuê thiết kế không thôi nó cũng đã tốn cỡ một '
     'nửa số tiền cọc này rồi. Bên em vẫn cần một khoản chắc chắn để biết anh có thiện '
     'chí xây, lúc đó phòng thiết kế và thi công mới tổ chức làm cho anh được.',
     'đặt cọc, 50 triệu, hợp đồng, thiết kế, khấu trừ'),

    ('hopdong', 'ratkho', 'phan_doi',
     'Anh không đồng ý đặt cọc tiền lúc ký hợp đồng đâu?',
     'Khách phản đối việc đặt cọc khi ký.',
     'Dạ em giải thích cho anh thế này, đặt cọc là để thể hiện sự thiện chí giữa hai '
     'bên thôi anh. Bên em có trụ sở văn phòng, có thương hiệu uy tín trên thị trường '
     'nên anh cứ yên tâm.',
     'Dạ anh có thể qua văn phòng ký hợp đồng, hoặc bên em về tận nơi khảo sát cũng '
     'được, nhưng việc đặt cọc thì phải có. Vì nếu không đặt cọc thì bên em cũng không '
     'biết anh có xây thật hay không để mà chuẩn bị thợ, lại còn bỏ công lên bản vẽ hồ '
     'sơ thiết kế cho anh nữa.',
     'Dạ anh thông cảm, nhiều khách cũng muốn bên em thiết kế xong, đưa thợ đưa vật tư '
     'về rồi mới cọc. Nhưng có trường hợp bên em thiết kế xong khách lấy hồ sơ bản vẽ '
     'in ra tự thi công, nên bên em rất khó. Mong anh chị thông cảm cho em.',
     'đặt cọc, không đồng ý, phản đối, thiện chí, hồ sơ'),

    ('hopdong', 'ratkho', 'nghi_ngo',
     'Đặt cọc xong các em trốn đi thì sao anh biết tìm ai?',
     'Khách nghi ngờ bị lừa, sợ mất tiền cọc.',
     'Dạ anh hỏi thế cũng đúng thôi, nhưng anh yên tâm, bên em là thương hiệu lớn, '
     'hoạt động bao nhiêu năm nay, bao nhiêu khách hàng biết đến. Anh qua trực tiếp '
     'văn phòng bên em ký hợp đồng cũng được, văn phòng đầy đủ hết.',
     'Dạ bên em làm căn nhà cho anh là để có lợi nhuận lâu dài và lấy uy tín, chứ đâu '
     'phải vì mấy đồng tiền cọc mà trốn đi. Bên em còn mong làm xong anh hài lòng rồi '
     'giới thiệu thêm khách cho em nữa.',
     'Dạ nếu anh còn băn khoăn, bên em sẵn sàng gửi anh hồ sơ pháp lý công ty, hợp '
     'đồng và mấy công trình đã làm để anh kiểm tra trước. Bên em làm ăn đàng hoàng, '
     'có thương hiệu chứ không làm vớ vẩn được đâu anh.',
     'đặt cọc, trốn đi, thương hiệu, văn phòng, uy tín'),

    ('hopdong', 'kho', 'nghi_ngo',
     'Anh thấy người ta bảo xây nhà trọn gói hợp đồng không rõ ràng?',
     'Khách nghi ngờ hợp đồng trọn gói sơ sài.',
     'Dạ đúng rồi anh, nhiều bên hợp đồng họ làm không rõ ràng thật. Nhưng anh cứ tham '
     'khảo hợp đồng và phụ lục bên em, em làm rất chi tiết, cẩn thận.',
     'Dạ ví dụ như cái cửa, bên em ghi rõ độ dày bao nhiêu, loại gì, thương hiệu gì, '
     'chủng loại vật tư ghi rất chi tiết. Tất cả vật tư bên em đều minh bạch rõ ràng '
     'chứ không ghi chung chung kiểu chỉ có mỗi tên thương hiệu.',
     'Dạ trước khi ký bên em gửi anh xem kỹ hợp đồng. Chỗ nào chưa rõ mình chỉnh hoặc '
     'em giải thích trước, không để đến lúc thi công mới tranh cãi. Anh hoàn toàn yên '
     'tâm.',
     'hợp đồng, không rõ ràng, phụ lục, chủng loại, minh bạch'),

    ('phatsinh', 'kho', 'lo_rui_ro',
     'Anh thấy họ bảo xây nhà trọn gói hay phát sinh nhiều chi phí lắm?',
     'Khách sợ bị phát sinh chi phí ngoài dự kiến.',
     'Dạ bên em cam kết không phát sinh bất kỳ chi phí nào hết anh ạ, trừ khi anh tăng '
     'diện tích, đổi mẫu nhà hoặc đổi loại móng thì mới tính thêm thôi.',
     'Dạ ví dụ như anh muốn ngăn thêm phòng ngủ, làm nhiều phòng hơn thì cũng không '
     'mất thêm đồng nào, vì bên em đã tính theo mét vuông rồi. Anh chỉ cần lưu ý những '
     'hạng mục nào không có trong hợp đồng là do bên em chưa báo thôi, còn lại không '
     'phát sinh gì hết.',
     'Dạ bên em không bao giờ tự ý làm phát sinh rồi bắt anh trả tiền đâu. Nếu có gì '
     'phát sinh thì phải có lý do, khối lượng, đơn giá rõ ràng và anh duyệt trước thì '
     'bên em mới làm.',
     'phát sinh, chi phí, trọn gói, mét vuông, duyệt trước'),

    ('hopdong', 'trungbinh', 'chuan_bi_ky',
     'Bên em có cam kết gì không?',
     'Khách muốn nghe cam kết của công ty.',
     'Dạ có chứ anh. Bên em cam kết vật tư đúng hợp đồng, làm việc chất lượng và bảo '
     'hành kết cấu 5 năm. Bên em làm là để lấy thương hiệu, lấy uy tín nên cam kết làm '
     'tốt theo đúng thỏa thuận.',
     'Dạ anh cứ nghĩ thế này, bên em làm xong cho anh, anh hài lòng thì còn giới thiệu '
     'thêm khách cho em nữa, nên không có lý do gì bên em làm ẩu. Mà bên em làm không '
     'tốt thì ngay phần móng đã có vấn đề rồi, đâu giấu được anh.',
     'Dạ thậm chí nếu anh thấy bên em làm không đúng hợp đồng thì anh cho dừng luôn '
     'cũng được. Bên em tự tin làm đúng cam kết nên mới dám nói với anh như vậy.',
     'cam kết, vật tư, bảo hành 5 năm, uy tín'),

    ('giaca', 'trungbinh', 'so_gia',
     'Bên em có khuyến mại gì không?',
     'Khách muốn được giảm giá / ưu đãi.',
     'Dạ tùy từng thời điểm bên em sẽ có chương trình hỗ trợ khác nhau anh ạ. Nhưng '
     'bên em ưu tiên báo giá thật, vật tư thật, chứ không nâng giá lên rồi nói khuyến '
     'mại cho kêu.',
     'Dạ nếu đang có chương trình hỗ trợ, bên em ghi rõ trong báo giá cho anh thấy. '
     'Quan trọng nhất vẫn là tổng chi phí cuối cùng với chất lượng thi công, chứ '
     'khuyến mại ảo thì không có ý nghĩa gì anh ạ.',
     'Dạ để em kiểm tra chính sách hiện tại xem công trình anh có được ưu đãi gì '
     'không. Nếu có em đưa thẳng vào báo giá để anh nhìn thấy quyền lợi cụ thể luôn.',
     'khuyến mại, ưu đãi, giảm giá, báo giá'),

    ('hopdong', 'kho', 'phan_doi',
     'Bên em có cho nợ không?',
     'Khách muốn thanh toán chậm / nợ tiền.',
     'Dạ thật lòng thì bên em không cho nợ được anh ạ, vì công ty phải ứng vật tư, '
     'nhân công liên tục. Nhưng em có 2 phương án cho anh lựa chọn để vẫn xoay được '
     'tiền.',
     'Dạ phương án một là sau khi xây xong phần thô, mình gọi ngân hàng về làm thủ tục '
     'vay, lúc này đã hình thành ngôi nhà rồi nên vay rất dễ. Phương án hai là nợ bên '
     'cung cấp vật tư, bên em đi xây nhiều nên đàm phán được, nhưng anh phải đứng ra '
     'khất nợ cùng bên em.',
     'Dạ hai cách này nhiều khách bên em đã áp dụng và làm thành công rồi anh. Mình cứ '
     'thống nhất tiến độ thanh toán ngay từ đầu, anh chủ động tài chính, bên em chủ '
     'động vật tư nhân công thì công trình chạy ổn định.',
     'cho nợ, thanh toán, ngân hàng, nợ vật tư, khất nợ'),

    ('hopdong', 'ratkho', 'lo_rui_ro',
     'Bên em có bỏ dở công trình không?',
     'Khách sợ công ty nhận tiền rồi bỏ dở.',
     'Dạ chắc chắn không anh ạ. Bên em làm việc phải có thương hiệu, lấy uy tín, lấy '
     'cái tâm để xây cho anh căn nhà cho tử tế, sau này còn nhiều khách giới thiệu tìm '
     'đến.',
     'Dạ anh cứ yên tâm, lợi nhuận của bên em thường nằm ở đợt thanh toán cuối cùng '
     'sau khi bàn giao nhà. Cho nên bên em không có lý do gì bỏ dở công trình giữa '
     'chừng, vì bỏ dở thì chính bên em mất phần lợi nhuận đó.',
     'Dạ chỉ cần hai bên làm đúng hợp đồng thì không bao giờ có chuyện bỏ dở. Hoàn '
     'thành công trình cho anh là lợi ích của cả hai bên, bên em còn cần uy tín và '
     'khách giới thiệu thêm nữa.',
     'bỏ dở, công trình, uy tín, lợi nhuận cuối'),

    ('baohanh', 'kho', 'chuan_bi_ky',
     'Bên em cho giữ tiền bảo hành bao nhiêu?',
     'Khách muốn giữ lại tiền bảo hành để yên tâm.',
     'Dạ trong hợp đồng bên em để anh giữ tiền bảo hành là 5 triệu anh ạ. Anh cứ yên '
     'tâm, ví dụ sau này thay bóng đèn, bóng điện gì thì bên em xử lý cho anh.',
     'Dạ còn về kết cấu thì bên em đã làm là chắc chắn rồi, chứ không có chuyện phải '
     'bảo hành kết cấu đâu anh. Số tiền giữ bảo hành này chủ yếu cho anh yên tâm mấy '
     'hạng mục lặt vặt thôi.',
     'Dạ mức giữ bảo hành này khách nào bên em cũng áp dụng như vậy. Vừa để anh yên '
     'tâm, vừa hợp lý để bên em quyết toán công trình. Mình ghi rõ phạm vi bảo hành '
     'trong hợp đồng là anh nắm được hết.',
     'giữ bảo hành, 5 triệu, bóng đèn, kết cấu'),

    ('baohanh', 'kho', 'phan_doi',
     'Bên em cho giữ tiền bảo hành thấp quá?',
     'Khách phản đối vì muốn giữ nhiều tiền bảo hành hơn.',
     'Dạ anh yên tâm đi, bên em có số tổng đài hẳn hoi, sau này có vấn đề gì cần bảo '
     'hành anh cứ điện là bên em có mặt. Anh chỉ cần báo trước một hôm là bên em về '
     'tận nơi xử lý cho anh.',
     'Dạ số tiền giữ bảo hành này thì khách nào bên em cũng cho giữ như nhau thôi anh. '
     'Với cả công trình cũng không có quá nhiều lãi, nên bên em chỉ cho giữ ở mức đó, '
     'đây là quy định chung của công ty.',
     'Dạ cái quan trọng không nằm ở số tiền giữ nhiều hay ít, mà ở chỗ bên em có pháp '
     'nhân, có tổng đài, có trách nhiệm bảo hành đàng hoàng. Anh cần là bên em có mặt, '
     'anh cứ yên tâm.',
     'giữ bảo hành thấp, tổng đài, bảo hành tận nơi, quy định'),

    ('tiendo', 'kho', 'lo_rui_ro',
     'Tiến độ bên em làm như thế nào?',
     'Khách lo chậm tiến độ, thiếu thợ.',
     'Dạ cho em hỏi anh xây nhà có đang gấp để dọn vào nhà mới không ạ? Nếu gấp thì '
     'bên em tăng cường thợ làm nhanh cho anh, còn bình thường thì khoảng 4 đến 5 '
     'tháng là xong nhà.',
     'Dạ nhà lớn hơn thì bên em làm tầm 6, 7 tháng anh ạ. Nhưng bên em xây cũng muốn '
     'bê tông phải đủ cứng mới tháo cốt pha, tường phải khô mới cho sơn, nên làm nhanh '
     'quá thì không đảm bảo kỹ thuật.',
     'Dạ mà bên em cũng không để chậm đâu, vì chậm quá thì bên em tốn nhiều chi phí '
     'quản lý. Cho nên anh cứ yên tâm, bên em sẽ làm đúng tiến độ mà mình mong muốn, '
     'có mốc thi công cụ thể cho anh theo dõi.',
     'tiến độ, gấp, 4-5 tháng, cốt pha, mốc thi công'),

    # ===================== E. THỢ THI CÔNG =====================
    ('tho', 'trungbinh', 'nghi_ngo',
     'Thợ bên em lấy ở đâu?',
     'Khách muốn biết nguồn thợ có ổn định, có kiểm soát.',
     'Dạ thợ bên em thì tất cả các tỉnh thành đều có anh ạ. Bên em làm việc là chọn '
     'lọc, thợ nào tay nghề tốt thì bên em giữ lại làm lâu dài.',
     'Dạ anh yên tâm, thợ bên em đã làm quen với mọi quy trình, tiêu chuẩn kỹ thuật '
     'của công ty rồi, nên làm việc theo một tiêu chuẩn thống nhất, đảm bảo chất lượng '
     'cho gia đình mình.',
     'Dạ bên em còn có đội kỹ thuật quản lý, kiểm tra thợ làm. Thợ thi công nhưng công '
     'ty chịu trách nhiệm cuối cùng với anh, nên không để thợ làm tự do không kiểm '
     'soát được đâu.',
     'thợ, tỉnh thành, tay nghề, quy trình, tiêu chuẩn'),

    ('tho', 'de', 'lo_rui_ro',
     'Thợ có ăn ở tại chỗ không?',
     'Khách quan tâm việc thợ ở lại công trình.',
     'Dạ có anh, thường thường các công trình bên em sẽ đưa thợ, đưa nhân công về dựng '
     'lán trại ăn ở ngay tại chỗ cho thuận tiện công việc.',
     'Dạ thợ ở tại công trình thì vừa trông coi được vật tư, vừa tiện thi công, tiến '
     'độ chạy nhanh hơn anh ạ. Bên em cũng nhắc thợ giữ gìn gọn gàng, không làm phiền '
     'hàng xóm xung quanh.',
     'Dạ tùy mặt bằng nhà anh nữa, nếu chỗ phù hợp thì thợ ở tại công trình. Mục tiêu '
     'là đảm bảo tiến độ nhưng vẫn an toàn, sạch sẽ cho gia đình mình.',
     'thợ, ăn ở, lán trại, công trình'),

    ('tho', 'trungbinh', 'nghi_ngo',
     'Thợ bên em tay nghề có cao không?',
     'Khách nghi ngờ tay nghề thợ.',
     'Dạ anh yên tâm, thợ bên em tuyển chọn rất kỹ lưỡng, làm tốt thì mới cho theo '
     'công trình được. Bên em không nhận thợ ẩu vào làm đâu anh.',
     'Dạ với cả làm đến đâu thì có cả phía chủ nhà và kỹ thuật bên em cùng nhau đồng '
     'hành giám sát đến đó, nên đảm bảo được tiêu chuẩn kỹ thuật, anh không phải lo '
     'thợ làm tự do.',
     'Dạ anh có thể xem công trình thực tế hoặc hình ảnh thi công của bên em để đánh '
     'giá. Bên em làm thương hiệu lâu dài nên đội thợ phải giữ chất lượng ổn định, '
     'không thể làm ẩu rồi bỏ đi được.',
     'thợ, tay nghề, tuyển chọn, giám sát, kỹ thuật'),

    ('tho', 'trungbinh', 'lo_rui_ro',
     'Đi xa thợ em có đi không, công ty có nhận công trình ở xa không?',
     'Khách ở xa, lo công ty không nhận hoặc làm không tới.',
     'Dạ bên em thi công toàn quốc anh ạ, ở đâu bên em cũng có thợ. Thường thường bên '
     'em đưa thợ, đưa nhân công về tận công trình để làm, nên ở xa mấy bên em cũng '
     'nhận được.',
     'Dạ bên em còn có chi nhánh ở nhiều tỉnh thành khác nhau nữa, nên anh ở đâu cũng '
     'yên tâm. Công trình xa thì bên em tổ chức bài bản hơn về thợ, kỹ thuật, vật tư, '
     'chỗ ở cho thợ.',
     'Dạ anh gửi em vị trí, diện tích và nhu cầu xây dựng, bên em kiểm tra rồi báo rõ '
     'phương án thi công cho anh ngay từ đầu. Anh cứ yên tâm, ở xa bên em vẫn làm tới '
     'nơi tới chốn.',
     'công trình xa, thợ đi xa, toàn quốc, chi nhánh'),

    ('tho', 'kho', 'lo_rui_ro',
     'Anh muốn tìm thợ ở gần để sau này bảo hành cho dễ?',
     'Khách muốn thợ gần để dễ bảo hành, ngại làm với công ty xa.',
     'Dạ anh yên tâm đi, thợ bên em thi công khắp các tỉnh, tỉnh nào cũng có đội thi '
     'công, nên việc bảo hành sau này rất thuận tiện chứ không khó như anh lo đâu.',
     'Dạ nhiều tỉnh thành lớn bên em có cả chi nhánh văn phòng và thợ thuyền làm việc '
     'tại chỗ. Cho nên có vấn đề gì cần bảo hành bên em có người ở gần xử lý cho anh '
     'nhanh.',
     'Dạ thợ gần thì có cái tiện thật, nhưng quan trọng hơn là ai chịu trách nhiệm '
     'cuối cùng. Bên em có hợp đồng, có bảo hành, có đội ở các tỉnh nên anh yên tâm '
     'hơn nhiều so với thuê thợ tự do.',
     'thợ gần, bảo hành, chi nhánh, trách nhiệm'),

    ('tho', 'trungbinh', 'lo_rui_ro',
     'Bên em có kỹ thuật xuống giám sát công trình không?',
     'Khách muốn có người giám sát chất lượng.',
     'Dạ có chứ anh. Kỹ thuật bên em thường xuyên ở công trình để giám sát thợ thuyền, '
     'kiểm soát chất lượng vật tư cùng với gia đình mình luôn.',
     'Dạ những mốc quan trọng như đổ móng, cột, dầm, sàn, điện nước, chống thấm thì kỹ '
     'thuật bên em đều phải có mặt kiểm tra. Anh cứ yên tâm là không để thợ làm một '
     'mình không ai giám sát.',
     'Dạ nếu anh cần, bên em thống nhất các mốc nghiệm thu để anh cùng kiểm tra với kỹ '
     'thuật: trước khi đổ bê tông, trước khi tô trát, trước khi chống thấm, trước khi '
     'lát gạch và trước khi bàn giao.',
     'kỹ thuật, giám sát, nghiệm thu, mốc thi công'),

    ('tho', 'trungbinh', 'chuan_bi_ky',
     'Bên khách hàng có được giám sát chéo không?',
     'Khách muốn được quyền giám sát công trình.',
     'Dạ được chứ anh, thoải mái luôn. Thậm chí nhiều khách bên em còn thuê hẳn một '
     'giám sát riêng về để giám sát toàn bộ công trình, bên em rất ủng hộ.',
     'Dạ cũng có nhiều khách có người nhà biết về xây dựng thì cùng nhau đồng hành '
     'giám sát với bên em. Bên em làm minh bạch nên không ngại anh giám sát chút nào.',
     'Dạ chỉ có một lưu ý nhỏ là mọi góp ý kỹ thuật anh trao đổi qua kỹ thuật hoặc '
     'quản lý công trình của bên em, tránh chỉ đạo trực tiếp thợ kẻo rối quy trình. '
     'Còn lại anh cứ giám sát thoải mái cho yên tâm.',
     'giám sát chéo, khách hàng, giám sát riêng, minh bạch'),
]
