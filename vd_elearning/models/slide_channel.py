# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class SlideChannel(models.Model):
    _inherit = 'slide.channel'

    # Khu vuc theo chuc vu — quyet dinh khoa hoc hien o KHU nao tren trang tong quan.
    vd_role_zone = fields.Selection(
        [('sales', 'Nhan vien kinh doanh'),
         ('leader', 'Truong nhom')],
        string='Khu vuc chuc vu', default='sales', index=True,
        help='Khoa hoc nay thuoc khu nao tren trang Tong quan eLearning theo chuc vu.')

    # Thu tu trong lo trinh hoc (admin keo-tha de sap xep).
    vd_seq = fields.Integer(string='Thu tu lo trinh', default=10, index=True)

    # Lo trinh dao tao chua khoa hoc nay.
    vd_path_id = fields.Many2one('vd.learning.path', string='Lộ trình',
                                 index=True, ondelete='set null')

    # Cau hinh bai thi. Mac dinh: dat 100%, thi lai 3 lan (user spec 2026-06-18).
    vd_pass_percent = fields.Integer(string='Ty le dat (%)', default=100)
    vd_max_attempts = fields.Integer(string='So lan thi lai toi da', default=3,
                                     help='0 = khong gioi han')
    # Thoi gian lam bai (phut). 0 = tu dong 1 phut/cau (20 cau = 20 phut).
    vd_exam_minutes = fields.Integer(string='Thoi gian thi (phut)', default=0,
                                     help='0 = tu dong 1 phut moi cau')

    @api.model
    def _vd_apply_course_defaults(self):
        """Ap mac dinh cho TAT CA khoa (moi + dang co): dat 100%, thi lai 3,
        thoi gian = so cau (1 phut/cau) - dien luon vao vd_exam_minutes de hien
        ro so phut. Chay 1 lan duy nhat (guard param) -> khong de len cau hinh
        admin chinh sau nay."""
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('vd_elearning.course_defaults_v1') == '1':
            return True
        for ch in self.sudo().search([]):
            quiz = ch.slide_ids.filtered(lambda x: x.slide_category == 'quiz')[:1]
            n_q = len(quiz.question_ids) if quiz else 0
            ch.write({
                'vd_pass_percent': 100,
                'vd_max_attempts': 3,
                'vd_exam_minutes': n_q,  # 20 cau -> 20 phut (hien ro), 0 neu chua co cau
            })
        ICP.set_param('vd_elearning.course_defaults_v1', '1')
        return True

    # ------------------------------------------------------------------
    def _vd_is_admin(self):
        return (self.env.user.has_group('base.group_system')
                or self.env.user.has_group('vd_crm_lead.vd_crm_group_admin'))

    @staticmethod
    def _vd_course_has_content(c):
        """Khoa co NOI DUNG (slide article) HOAC BAI THI (quiz co cau hoi) chua."""
        slides = c.slide_ids.filtered(lambda s: not s.is_category)
        if slides.filtered(lambda s: s.slide_category != 'quiz'):
            return True
        quiz = slides.filtered(lambda s: s.slide_category == 'quiz')[:1]
        return bool(quiz and quiz.question_ids)

    @api.model
    def _vd_assign_default_paths(self):
        """Gan khoa hoc chua co lo trinh vao 'Lo trinh co ban' cua zone (idempotent)."""
        refs = {'sales': self.env.ref('vd_elearning.path_sales_basic', raise_if_not_found=False),
                'leader': self.env.ref('vd_elearning.path_leader_basic', raise_if_not_found=False)}
        for zk, path in refs.items():
            if not path:
                continue
            orphans = self.sudo().search([('vd_role_zone', '=', zk), ('vd_path_id', '=', False)])
            if orphans:
                orphans.write({'vd_path_id': path.id})
        return True

    @api.model
    def vd_get_overview(self):
        """Du lieu cho trang OWL.
        - 2 khu theo chuc vu (NV kinh doanh / Truong nhom).
        - Moi khu: nhan vien nhom theo phong ban (leader vang len dau) + lo trinh khoa hoc."""
        Users = self.env['res.users']
        internal = Users.search([('share', '=', False), ('active', '=', True)])

        # Map khoa hoc theo zone (theo thu tu lo trinh).
        # sudo: app tu kiem soat quyen theo vai tro/lo trinh, KHONG dung record rule
        # cua website_slides (membership) -> tranh an khoa NV chua la member.
        zone_recs = {
            'sales': self.sudo().search([('vd_role_zone', '=', 'sales')], order='vd_seq, id'),
            'leader': self.sudo().search([('vd_role_zone', '=', 'leader')], order='vd_seq, id'),
        }

        # TU DONG CHAY LO TRINH cho NV DANG XEM (user spec 2026-06-24): mo khoa moi
        # chen vao lo trinh da gan + mo lo trinh ke tiep neu da hoan thanh — TRUOC
        # khi dung `progress` de me/report phan anh ngay membership moi.
        cur = self.env.user
        if cur and not cur.share and cur.vd_crm_role in (
                'employee', 'collaborator', 'team_leader'):
            self._vd_heal_path_membership(cur)
            self._vd_progress_user_paths(cur)

        # ----- Tien do hoc cua tung NV de gan avatar vao dung "cua ai" -----
        SCP = self.env['slide.channel.partner'].sudo()
        all_chan_ids = (zone_recs['sales'] | zone_recs['leader']).ids
        progress = {}  # partner_id -> {channel_id: member_status}
        if all_chan_ids and internal:
            for p in SCP.search([('partner_id', 'in', internal.partner_id.ids),
                                 ('channel_id', 'in', all_chan_ids)]):
                progress.setdefault(p.partner_id.id, {})[p.channel_id.id] = p.member_status

        # ----- Tap khoa DA DAT (passed) BEN VUNG theo NV: vd.exam.result -----
        # Dung cho bang THEO DOI lo trinh (ai hoan thanh / dang hoc / chua hoc).
        # Ben vung: khong mat khi gan lai lo trinh hay xoa membership. Fallback
        # them membership 'completed' cho NV cu chua co ban ghi exam.result.
        passed_by_uid = {}  # user_id -> set(channel_id da dat)
        if all_chan_ids and internal:
            ER = self.env['vd.exam.result'].sudo()
            for r in ER.search([('user_id', 'in', internal.ids),
                                ('channel_id', 'in', all_chan_ids),
                                ('passed', '=', True)]):
                passed_by_uid.setdefault(r.user_id.id, set()).add(r.channel_id.id)
            pid2uid = {u.partner_id.id: u.id for u in internal}
            for pid, chans in progress.items():
                uid = pid2uid.get(pid)
                if not uid:
                    continue
                for cid, st in chans.items():
                    if st == 'completed':
                        passed_by_uid.setdefault(uid, set()).add(cid)

        # NV duoc coi la "da gan" khi co membership o it nhat 1 khoa trong khu.
        sales_ids = set(zone_recs['sales'].ids)
        leader_ids = set(zone_recs['leader'].ids)

        def is_assigned(user, zk):
            mine = progress.get(user.partner_id.id)
            if not mine:
                return False
            ids = sales_ids if zk == 'sales' else leader_ids
            return any(cid in ids for cid in mine)

        def current_course_id(user, recs):
            """Khoa hoc NV dang dung ('cua ai' hien tai).
            CHI xet cac khoa NV THUC SU duoc gan (co membership) - tranh "do" NV
            sang khoa o lo trinh khac (vd. da go gan nhung van hien) chi vi khoa do
            dung sau trong thu tu chung va NV chua hoan thanh no."""
            if not recs:
                return False
            mine = progress.get(user.partner_id.id, {})
            ids = [cid for cid in recs.ids if cid in mine]
            if not ids:
                return False                         # khong con gan khoa nao -> khong hien
            for cid in ids:                          # cua dang hoc dang do
                if mine.get(cid) in ('joined', 'ongoing'):
                    return cid
            for cid in ids:                          # cua tiep theo chua hoan thanh
                if mine.get(cid) != 'completed':
                    return cid
            return ids[-1]                           # da pha dao het

        def zone_employees(roles, recs, zk):
            us = internal.filtered(lambda u: u.vd_crm_role in roles and is_assigned(u, zk))
            us = us.sorted(lambda u: (u.vd_team_label or 'KHAC', u.name or ''))
            return [{'id': u.id, 'name': u.name or '',
                     'course_id': current_course_id(u, recs)} for u in us]

        def course_list(recs):
            return [{
                'id': c.id,
                'name': c.name or '',
                'total_slides': c.total_slides,
                'has_image': bool(c.image_512),
                'published': bool(c.is_published),
                # Co noi dung HOAC bai thi -> icon tim; rong -> icon xam + xoa duoc.
                'has_content': self._vd_course_has_content(c),
            } for c in recs]

        PathModel = self.env['vd.learning.path'].sudo()

        track_role_label = {'collaborator': 'CTV', 'employee': 'NV',
                            'team_leader': 'TN', 'director': 'GĐ', 'admin': 'Admin'}

        def path_tracking(path, zk):
            """TAT CA nhan vien hien tai cua khu: ai HOAN THANH / DANG HOC / CHUA HOC
            lo trinh nay. 'Da dat' = passed_by_uid (ben vung)."""
            courses = path.course_ids.sorted(lambda c: (c.vd_seq, c.id))
            cids = courses.ids
            total = len(cids)
            roles = self._vd_zone_roles(zk)
            us = internal.filtered(lambda u: u.vd_crm_role in roles)
            rows = []
            n_done = n_learn = n_todo = 0
            for u in us:
                mine = passed_by_uid.get(u.id, set())
                c = sum(1 for cid in cids if cid in mine)
                if total and c >= total:
                    status, cur = 'done', ''
                    n_done += 1
                elif c > 0:
                    status = 'learning'
                    cur = next((co.name for co in courses if co.id not in mine), '')
                    n_learn += 1
                else:
                    status, cur = 'todo', (courses[0].name if courses else '')
                    n_todo += 1
                rows.append({'id': u.id, 'name': u.name or '',
                             'team': u.vd_team_label or 'KHAC',
                             'role': track_role_label.get(u.vd_crm_role, ''),
                             'status': status, 'done': c, 'total': total,
                             'current': cur})
            order = {'learning': 0, 'todo': 1, 'done': 2}
            rows.sort(key=lambda r: (order.get(r['status'], 9),
                                     r['team'], r['name']))
            return {'rows': rows, 'total_courses': total, 'n_total': len(rows),
                    'n_done': n_done, 'n_learning': n_learn, 'n_todo': n_todo}

        def zone_paths(zk):
            paths = PathModel.search([('zone', '=', zk)], order='sequence, id')
            return [{
                'id': p.id,
                'name': p.name or '',
                'courses': course_list(p.course_ids.sorted(lambda c: (c.vd_seq, c.id))),
                'tracking': path_tracking(p, zk),
            } for p in paths]

        # ----- Bao cao thanh tich tung NV (tab NHAN VIEN) -----
        role_label = {'collaborator': 'CTV', 'employee': 'Nhân viên',
                      'team_leader': 'Trưởng nhóm', 'director': 'Giám đốc', 'admin': 'Admin'}

        def report_row(user):
            zk = ('leader' if user.vd_crm_role == 'team_leader' else 'sales')
            recs = zone_recs[zk]
            ids = recs.ids
            mine = progress.get(user.partner_id.id, {})
            completed_ids = [cid for cid in ids if mine.get(cid) == 'completed']
            completed = len(completed_ids)
            total = len(ids)
            cur_id = current_course_id(user, recs)
            cur = recs.filtered(lambda c: c.id == cur_id)[:1]
            return {
                'id': user.id, 'name': user.name or '',
                'team': user.vd_team_label or 'KHAC',
                'role': role_label.get(user.vd_crm_role, ''),
                'completed': completed, 'total': total,
                'percent': round(100.0 * completed / total) if total else 0,
                'current': cur.name if cur else '',
                'current_id': cur_id,
                'completed_ids': completed_ids,
                'zone_key': zk,
            }

        report_users = internal.filtered(
            lambda u: u.vd_crm_role in ('employee', 'collaborator', 'team_leader')
            and is_assigned(u, 'leader' if u.vd_crm_role == 'team_leader' else 'sales')
        ).sorted(lambda u: (u.vd_team_label or 'zz', u.name or ''))
        report = [report_row(u) for u in report_users]

        # Thong tin user hien tai — NV/CTV/TN dang nhap se vao thang giao dien cua minh.
        u = self.env.user
        role = u.vd_crm_role
        my_zone = ('sales' if role in ('employee', 'collaborator')
                   else 'leader' if role == 'team_leader' else False)
        if my_zone:
            my_mine = progress.get(u.partner_id.id, {})
            me = {'id': u.id, 'name': u.name or '', 'zone_key': my_zone,
                  'course_id': current_course_id(u, zone_recs[my_zone]),
                  'completed_ids': [cid for cid in zone_recs[my_zone].ids
                                    if my_mine.get(cid) == 'completed']}
        else:
            me = False

        return {
            'is_admin': self._vd_is_admin(),
            'me': me,
            'report': report,
            'zones': [
                {'key': 'sales', 'title': 'NHAN VIEN KINH DOANH',
                 'employees': zone_employees(['employee', 'team_leader', 'collaborator'], zone_recs['sales'], 'sales'),
                 'courses': course_list(zone_recs['sales']),
                 'paths': zone_paths('sales')},
                {'key': 'leader', 'title': 'TRUONG NHOM',
                 'employees': zone_employees(['team_leader'], zone_recs['leader'], 'leader'),
                 'courses': course_list(zone_recs['leader']),
                 'paths': zone_paths('leader')},
            ],
        }

    # ==================================================================
    #  TRINH SOAN KHOA HOC (popup full man hinh): noi dung + cau hoi thi
    # ==================================================================
    @api.model
    def vd_course_load(self, channel_id):
        """Du lieu cho popup khoa hoc: noi dung (slide article) + cau hoi thi (quiz).
        Hoc vien KHONG nhan duoc co is_correct (tranh lo dap an)."""
        # sudo: app kiem soat quyen rieng -> NV chua la member van load duoc khoa.
        ch = self.sudo().browse(channel_id)
        is_admin = self._vd_is_admin()
        contents = []
        for s in ch.slide_ids.filtered(
                lambda x: not x.is_category and x.slide_category != 'quiz'
        ).sorted(lambda x: (x.sequence, x.id)):
            contents.append({'id': s.id, 'name': s.name or '',
                             'body': s.vd_body or s.html_content or ''})
        questions = []
        quiz = ch.slide_ids.filtered(lambda x: x.slide_category == 'quiz')[:1]
        if quiz:
            for q in quiz.question_ids.sorted(lambda x: (x.sequence, x.id)):
                questions.append({
                    'id': q.id, 'text': q.question or '',
                    'answers': [{'id': a.id, 'text': a.text_value or '',
                                 'is_correct': a.is_correct if is_admin else False}
                                for a in q.answer_ids.sorted(lambda x: (x.sequence, x.id))],
                })
        # Thoi gian thi hieu luc: cau hinh > 0 thi dung; =0 -> 1 phut/cau.
        n_q = len(questions)
        exam_minutes = ch.vd_exam_minutes or n_q or 0
        return {'id': ch.id, 'name': ch.name or '', 'is_admin': is_admin,
                'pass_percent': ch.vd_pass_percent or 80,
                'max_attempts': ch.vd_max_attempts or 0,
                'exam_minutes_cfg': ch.vd_exam_minutes or 0,  # raw (0 = auto)
                'exam_minutes': exam_minutes,                 # hieu luc cho timer
                'contents': contents, 'questions': questions}

    @api.model
    def vd_course_config_save(self, channel_id, pass_percent, max_attempts, exam_minutes=0):
        """Luu cau hinh khoa hoc (ty le dat, so lan thi lai, thoi gian thi). Chi admin."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc cau hinh khoa hoc.')
        pp = max(0, min(100, int(pass_percent or 0)))
        ma = max(0, int(max_attempts or 0))
        em = max(0, int(exam_minutes or 0))
        self.browse(channel_id).write({
            'vd_pass_percent': pp, 'vd_max_attempts': ma, 'vd_exam_minutes': em})
        return True

    @api.model
    def vd_course_rename(self, channel_id, name):
        """Doi ten khoa hoc nhanh (nut but tren tieu de). Chi admin."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc doi ten khoa hoc.')
        nm = (name or '').strip()
        if nm:
            self.browse(channel_id).name = nm
        return nm

    @api.model
    def vd_course_grade(self, channel_id, answers_by_q):
        """Cham diem bai thi tren SERVER. answers_by_q = {qid(str): [answer_id,...]}.
        Cau dung khi tap dap an chon == tap dap an dung. Tra ve diem + dap an dung de xem lai."""
        ch = self.sudo().browse(channel_id)
        quiz = ch.slide_ids.filtered(lambda x: x.slide_category == 'quiz')[:1]
        qs = quiz.question_ids.sorted(lambda x: (x.sequence, x.id)) if quiz else self.env['slide.question']
        results = []
        correct_count = 0
        for q in qs:
            correct_ids = set(q.answer_ids.filtered('is_correct').ids)
            chosen = set(int(x) for x in (answers_by_q.get(str(q.id)) or []))
            ok = bool(correct_ids) and chosen == correct_ids
            if ok:
                correct_count += 1
            results.append({'qid': q.id, 'correct': ok,
                            'correct_ids': list(correct_ids)})
        total = len(qs)
        percent = round(100.0 * correct_count / total) if total else 0
        pass_percent = ch.vd_pass_percent or 80
        passed = percent >= pass_percent
        # Ghi nhan ket qua thi cho NV dang nhap moi lan nop (phuc vu bang LICH SU HOC)
        # + danh dau HOAN THANH khi dat (dashboard dung tien do + banner tu tat).
        pid = self.env.user.partner_id.id
        SCP = self.env['slide.channel.partner'].sudo()
        rec = SCP.search([('channel_id', '=', ch.id),
                          ('partner_id', '=', pid)], limit=1)
        vals = {
            'vd_exam_percent': percent,
            'vd_exam_passed': passed or (rec.vd_exam_passed if rec else False),
            'vd_exam_attempts': (rec.vd_exam_attempts if rec else 0) + 1,
            'vd_exam_done_at': fields.Datetime.now(),
        }
        if passed:
            vals['member_status'] = 'completed'
        if rec:
            rec.write(vals)
        else:
            vals.update({'channel_id': ch.id, 'partner_id': pid})
            SCP.create(vals)
        # Lich su BEN VUNG theo NHAN VIEN (khong mat khi gan lai lo trinh / xoa khoa).
        self.env['vd.exam.result'].sudo().vd_record_attempt(
            self.env.user, ch, percent, passed)
        # TU DONG CHAY LO TRINH: dat -> mo khoa moi chen + mo lo trinh ke tiep neu
        # da hoan thanh het lo trinh hien tai (user spec 2026-06-24).
        if passed:
            self._vd_heal_path_membership(self.env.user)
            self._vd_progress_user_paths(self.env.user)
        return {'total': total, 'score': correct_count, 'percent': percent,
                'pass_percent': pass_percent, 'passed': passed,
                'results': results,
                # Dữ liệu giấy chứng nhận (hiện khi ĐẠT) — user spec 2026-06-24.
                'cert': self._vd_cert_payload(self.env.user, ch, percent)}

    @api.model
    def vd_course_save(self, channel_id, name, contents, questions):
        """Luu ten + noi dung + cau hoi thi tu popup. Chi admin."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc sua khoa hoc.')
        ch = self.browse(channel_id)
        if name and (name or '').strip() and name.strip() != ch.name:
            ch.name = name.strip()
        Slide = self.env['slide.slide'].sudo()
        Question = self.env['slide.question'].sudo()

        # ----- NOI DUNG (slide article) -----
        keep = self.env['slide.slide']
        seq = 1
        for c in (contents or []):
            name = (c.get('name') or '').strip() or 'Nội dung'
            body = c.get('body') or ''
            if c.get('id'):
                s = Slide.browse(c['id'])
                s.write({'name': name, 'vd_body': body, 'sequence': seq})
            else:
                s = Slide.create({'channel_id': ch.id, 'name': name,
                                  'slide_category': 'article', 'vd_body': body,
                                  'sequence': seq, 'is_published': True})
            keep |= s
            seq += 1
        existing = ch.slide_ids.filtered(
            lambda x: not x.is_category and x.slide_category != 'quiz')
        (existing - keep).unlink()

        # ----- CAU HOI THI (quiz slide chung) -----
        questions = questions or []
        quiz = ch.slide_ids.filtered(lambda x: x.slide_category == 'quiz')[:1]
        if questions and not quiz:
            quiz = Slide.create({'channel_id': ch.id, 'name': 'Bài thi',
                                 'slide_category': 'quiz', 'sequence': 999,
                                 'is_published': True})
        keep_q = self.env['slide.question']
        qseq = 1
        for q in questions:
            text = (q.get('text') or '').strip()
            if not text:
                continue
            ans = q.get('answers') or []
            corr = [a for a in ans if a.get('is_correct')]
            if len(ans) < 2 or not corr or len(corr) == len(ans):
                raise ValidationError(
                    'Mỗi câu hỏi phải có ít nhất 1 đáp án đúng và 1 đáp án sai.\nCâu: %s' % text)
            cmds = [(0, 0, {'text_value': (a.get('text') or '').strip() or '-',
                            'is_correct': bool(a.get('is_correct')), 'sequence': i + 1})
                    for i, a in enumerate(ans)]
            if q.get('id'):
                qq = Question.browse(q['id'])
                qq.answer_ids.unlink()
                qq.write({'question': text, 'sequence': qseq, 'answer_ids': cmds})
            else:
                qq = Question.create({'slide_id': quiz.id, 'question': text,
                                      'sequence': qseq, 'answer_ids': cmds})
            keep_q |= qq
            qseq += 1
        if quiz:
            (quiz.question_ids - keep_q).unlink()
        return True

    @staticmethod
    def _vd_zone_roles(zk):
        return (['employee', 'collaborator', 'team_leader'] if zk == 'sales'
                else ['team_leader'])

    @api.model
    def vd_path_candidates(self, path_id):
        """Danh sach NV co the gan vao lo trinh + trang thai da gan hay chua."""
        path = self.env['vd.learning.path'].browse(path_id)
        roles = self._vd_zone_roles(path.zone)
        internal = self.env['res.users'].search(
            [('share', '=', False), ('active', '=', True)])
        us = internal.filtered(lambda u: u.vd_crm_role in roles)
        us = us.sorted(lambda u: (u.vd_team_label or 'zz', u.name or ''))
        course_ids = path.course_ids.ids
        assigned = set()
        if course_ids and us:
            SCP = self.env['slide.channel.partner'].sudo()
            for p in SCP.search([('channel_id', 'in', course_ids),
                                 ('partner_id', 'in', us.partner_id.ids)]):
                assigned.add(p.partner_id.id)
        role_label = {'collaborator': 'CTV', 'employee': 'Nhân viên',
                      'team_leader': 'Trưởng nhóm'}
        return [{'id': u.id, 'name': u.name or '',
                 'team': u.vd_team_label or 'KHAC',
                 'role': role_label.get(u.vd_crm_role, ''),
                 'assigned': u.partner_id.id in assigned} for u in us]

    @api.model
    def vd_set_path_members(self, path_id, user_ids):
        """Dong bo NV duoc gan vao lo trinh = membership o moi khoa cua lo trinh.
        Chi gan/go trong pham vi NV du dieu kien (khong dung den NV khac). Chi admin."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc gan nhan vien.')
        path = self.env['vd.learning.path'].browse(path_id)
        courses = path.course_ids
        if not courses:
            return True
        roles = self._vd_zone_roles(path.zone)
        internal = self.env['res.users'].search(
            [('share', '=', False), ('active', '=', True)])
        pool = internal.filtered(lambda u: u.vd_crm_role in roles)
        pool_pids = set(pool.partner_id.ids)
        target_pids = set(self.env['res.users'].browse(user_ids).partner_id.ids) & pool_pids
        SCP = self.env['slide.channel.partner'].sudo()
        for c in courses:
            existing = SCP.search([('channel_id', '=', c.id),
                                   ('partner_id', 'in', list(pool_pids))])
            existing_pids = set(existing.mapped('partner_id').ids)
            to_remove = existing.filtered(lambda r: r.partner_id.id not in target_pids)
            if to_remove:
                to_remove.unlink()
            for pid in (target_pids - existing_pids):
                SCP.create({'channel_id': c.id, 'partner_id': pid,
                            'member_status': 'joined'})
        return True

    @api.model
    def vd_member_position(self, path_id, user_id):
        """Vi tri hoc hien tai cua 1 NV trong lo trinh (de preselect popup Vi tri hoc)."""
        path = self.env['vd.learning.path'].browse(path_id)
        courses = path.course_ids.sorted(lambda c: (c.vd_seq, c.id))
        user = self.env['res.users'].browse(user_id)
        pid = user.partner_id.id
        SCP = self.env['slide.channel.partner'].sudo()
        status = {}
        if courses and pid:
            for p in SCP.search([('channel_id', 'in', courses.ids),
                                 ('partner_id', '=', pid)]):
                status[p.channel_id.id] = p.member_status
        completed_count = sum(1 for c in courses if status.get(c.id) == 'completed')
        current_id = False
        for c in courses:
            if status.get(c.id) != 'completed':
                current_id = c.id
                break
        return {'total': len(courses), 'completed_count': completed_count,
                'current_id': current_id}

    @api.model
    def vd_set_member_position(self, path_id, user_id, current_course_id=False, completed_all=False):
        """Gan 1 NV (thuong la NV cu) vao vi tri cu the trong lo trinh: chon khoa
        DANG hoc -> moi khoa TRUOC do = hoan thanh, khoa do + sau = dang hoc. Chi admin."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc gan vi tri hoc.')
        path = self.env['vd.learning.path'].browse(path_id)
        courses = path.course_ids.sorted(lambda c: (c.vd_seq, c.id))
        if not courses:
            return True
        roles = self._vd_zone_roles(path.zone)
        user = self.env['res.users'].browse(user_id)
        if user.vd_crm_role not in roles:
            raise AccessError('Nhan vien khong thuoc khu dao tao cua lo trinh nay.')
        pid = user.partner_id.id
        course_ids = courses.ids
        # cut = so khoa duoc tinh la HOAN THANH (cac khoa truoc moc dang hoc).
        if completed_all:
            cut = len(course_ids)
        elif current_course_id and current_course_id in course_ids:
            cut = course_ids.index(current_course_id)
        else:
            cut = 0
        SCP = self.env['slide.channel.partner'].sudo()
        for idx, c in enumerate(courses):
            st = 'completed' if idx < cut else 'joined'
            rec = SCP.search([('channel_id', '=', c.id),
                              ('partner_id', '=', pid)], limit=1)
            if rec:
                rec.write({'member_status': st})
            else:
                SCP.create({'channel_id': c.id, 'partner_id': pid,
                            'member_status': st})
        return True

    # ==================================================================
    #  TU DONG CHAY LO TRINH (user spec 2026-06-24)
    #  - Admin chi gan NV o LO TRINH DAU. NV hoc tuan tu trai->phai,
    #    tren->duoi; hoan thanh het 1 lo trinh -> TU MO lo trinh ke tiep.
    #  - Khoa MOI chen vao lo trinh da gan -> NV van co membership (bam hoc duoc).
    # ==================================================================
    def _vd_user_zone(self, user):
        return ('leader'
                if user.has_group('vd_crm_lead.vd_crm_group_team_leader')
                else 'sales')

    # ===== GIẤY CHỨNG NHẬN (user spec 2026-06-24) =====
    _VD_CERT_ROLE = {
        'collaborator': 'CỘNG TÁC VIÊN KINH DOANH',
        'employee': 'NHÂN VIÊN KINH DOANH',
        'team_leader': 'TRƯỞNG NHÓM KINH DOANH',
        'director': 'BAN GIÁM ĐỐC',
        'admin': 'QUẢN TRỊ VIÊN',
    }

    def _vd_cert_payload(self, user, channel=None, percent=None):
        """Thông tin để vẽ giấy chứng nhận: tên NV (bỏ tiền tố team), vai trò,
        công ty, tên khoá, điểm."""
        import re as _re
        full = user.name or ''
        m = _re.match(r'^\s*[A-Za-zÀ-ỹ0-9]+\s*-\s*(.+)$', full)
        emp = (m.group(1) if m else full).strip()
        return {
            'emp_name': emp or full,
            'role_label': self._VD_CERT_ROLE.get(user.vd_crm_role, 'NHÂN VIÊN KINH DOANH'),
            'company_name': 'CÔNG TY CỔ PHẦN VINADUY',
            'course_name': (channel.name if channel else '') or '',
            'percent': int(percent) if percent is not None else 0,
        }

    @api.model
    def vd_my_certificates(self):
        """Danh sách giấy chứng nhận ĐÃ ĐẠT của NV đang đăng nhập (lưu bền vững ở
        vd.exam.result.passed) + thông tin NV để vẽ lại chứng nhận."""
        user = self.env.user
        ER = self.env['vd.exam.result'].sudo()
        recs = ER.search([('user_id', '=', user.id), ('passed', '=', True)])
        base = self._vd_cert_payload(user)
        items = []
        for r in recs:
            items.append({
                'channel_id': r.channel_id.id if r.channel_id else False,
                'course_name': (r.channel_id.name if r.channel_id
                                else r.course_name) or '(khóa đã xóa)',
                'percent': r.best_percent or r.percent or 0,
                'date_ts': ER._to_ts(r.last_done_at),
            })
        items.sort(key=lambda i: -i['date_ts'])
        base['items'] = items
        return base

    def _vd_heal_path_membership(self, user):
        """NV da la member cua 1 lo trinh -> DAM BAO co membership o MOI khoa cua
        lo trinh do (ke ca khoa moi chen vao sau khi gan). Giu nguyen completed.
        => khoa moi chen truoc/giua cac khoa da hoc van BAM HOC DUOC (co membership).
        Idempotent, sudo, nuot loi."""
        try:
            if not user or user.share:
                return
            Path = self.env['vd.learning.path'].sudo()
            paths = Path.search([('zone', '=', self._vd_user_zone(user))])
            SCP = self.env['slide.channel.partner'].sudo()
            pid = user.partner_id.id
            for p in paths:
                cids = p.course_ids.ids
                if not cids:
                    continue
                members = SCP.search([('partner_id', '=', pid),
                                      ('channel_id', 'in', cids)])
                if not members:
                    continue  # KHONG phai member lo trinh nay -> de nguyen (khoa)
                have = set(members.mapped('channel_id').ids)
                for c in p.course_ids:
                    if c.id not in have:
                        SCP.create({'channel_id': c.id, 'partner_id': pid,
                                    'member_status': 'joined'})
        except Exception:
            pass

    def _vd_progress_user_paths(self, user):
        """NV hoan thanh HET 1 lo trinh (moi khoa CO BAI THI deu da DAT) -> TU GAN
        (membership 'joined') toan bo khoa cua lo trinh KE TIEP cung khu. Cascade
        trong 1 lan goi. Idempotent, sudo, nuot loi."""
        try:
            if not user or user.share:
                return
            Path = self.env['vd.learning.path'].sudo()
            paths = Path.search([('zone', '=', self._vd_user_zone(user))],
                                order='sequence, id')
            if len(paths) < 2:
                return
            SCP = self.env['slide.channel.partner'].sudo()
            ER = self.env['vd.exam.result'].sudo()
            pid = user.partner_id.id
            all_ids = []
            for p in paths:
                all_ids += p.course_ids.ids
            if not all_ids:
                return
            status = {}
            for m in SCP.search([('partner_id', '=', pid),
                                 ('channel_id', 'in', all_ids)]):
                status[m.channel_id.id] = m.member_status
            passed = set(ER.search([
                ('user_id', '=', user.id), ('channel_id', 'in', all_ids),
                ('passed', '=', True)]).mapped('channel_id').ids)

            def done(c):
                return status.get(c.id) == 'completed' or c.id in passed

            def has_quiz(c):
                quiz = c.slide_ids.filtered(
                    lambda s: s.slide_category == 'quiz')[:1]
                return bool(quiz and quiz.question_ids)

            def is_member(p):
                return any(c.id in status for c in p.course_ids)

            def path_complete(p):
                # Co it nhat 1 khoa co noi dung + moi khoa CO BAI THI deu da DAT.
                if not any(self._vd_course_has_content(c) for c in p.course_ids):
                    return False
                for c in p.course_ids:
                    if has_quiz(c) and not done(c):
                        return False
                return True

            for i, p in enumerate(paths):
                if i + 1 >= len(paths):
                    break
                if is_member(p) and path_complete(p):
                    nxt = paths[i + 1]
                    for c in nxt.course_ids:
                        if c.id not in status:
                            SCP.create({'channel_id': c.id, 'partner_id': pid,
                                        'member_status': 'joined'})
                            status[c.id] = 'joined'
        except Exception:
            pass

    @api.model
    def vd_save_order(self, zone, ordered_ids):
        """Luu lai thu tu lo trinh sau khi admin keo-tha. Chi admin."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc sap xep lo trinh khoa hoc.')
        seq = 10
        for cid in ordered_ids:
            self.browse(cid).write({'vd_seq': seq, 'vd_role_zone': zone})
            seq += 10
        return True

    _VD_DELETED_KEY = 'vd_elearning.deleted_courses'

    @api.model
    def vd_course_delete(self, channel_id):
        """Xoa khoa hoc VINH VIEN khoi SQL - CHI khi khoa chua co noi dung + chua
        co bai thi. Chi admin. Neu khoa do seed tu courses.xml (co xmlid) -> ghi
        xmlid vao blocklist + _vd_purge_deleted_courses (chay cuoi courses.xml) se
        xoa lai sau moi -u -> KHONG bi tai tao (user spec 2026-06-24)."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc xoa khoa hoc.')
        ch = self.browse(channel_id)
        if not ch.exists():
            return True
        if self._vd_course_has_content(ch):
            raise ValidationError(
                'Chi xoa duoc khoa hoc CHUA co noi dung va CHUA co bai thi.')
        IMD = self.env['ir.model.data'].sudo()
        imd = IMD.search([('model', '=', 'slide.channel'),
                          ('res_id', '=', ch.id)], limit=1)
        if imd:
            ICP = self.env['ir.config_parameter'].sudo()
            blocked = set(filter(None, (ICP.get_param(self._VD_DELETED_KEY) or '').split(',')))
            blocked.add('%s.%s' % (imd.module, imd.name))
            ICP.set_param(self._VD_DELETED_KEY, ','.join(sorted(blocked)))
            imd.unlink()
        ch.unlink()
        return True

    @api.model
    def _vd_purge_deleted_courses(self):
        """Chay cuoi courses.xml moi lan -u: xoa lai cac khoa admin DA xoa (du
        courses.xml vua tai tao). Giu xoa VINH VIEN qua cac lan deploy."""
        ICP = self.env['ir.config_parameter'].sudo()
        blocked = [x for x in (ICP.get_param(self._VD_DELETED_KEY) or '').split(',') if x]
        IMD = self.env['ir.model.data'].sudo()
        for xmlid in blocked:
            rec = self.env.ref(xmlid, raise_if_not_found=False)
            if not rec:
                continue
            imd = IMD.search([('model', '=', 'slide.channel'),
                              ('res_id', '=', rec.id)], limit=1)
            try:
                rec.sudo().unlink()
                if imd:
                    imd.unlink()
            except Exception:
                continue
        return True

    @api.model
    def vd_save_path_order(self, zone, ordered_path_ids):
        """Luu thu tu LO TRINH sau khi admin keo-tha (khoa hoc di theo cung). Chi admin."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc sap xep lo trinh.')
        Path = self.env['vd.learning.path']
        seq = 10
        for pid in ordered_path_ids:
            Path.browse(pid).write({'sequence': seq, 'zone': zone})
            seq += 10
        return True
