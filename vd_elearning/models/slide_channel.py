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

    # Cau hinh bai thi.
    vd_pass_percent = fields.Integer(string='Ty le dat (%)', default=80)
    vd_max_attempts = fields.Integer(string='So lan thi lai toi da', default=3,
                                     help='0 = khong gioi han')
    # Thoi gian lam bai (phut). 0 = tu dong 1 phut/cau (20 cau = 20 phut).
    vd_exam_minutes = fields.Integer(string='Thoi gian thi (phut)', default=0,
                                     help='0 = tu dong 1 phut moi cau')

    # ------------------------------------------------------------------
    def _vd_is_admin(self):
        return (self.env.user.has_group('base.group_system')
                or self.env.user.has_group('vd_crm_lead.vd_crm_group_admin'))

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
        zone_recs = {
            'sales': self.search([('vd_role_zone', '=', 'sales')], order='vd_seq, id'),
            'leader': self.search([('vd_role_zone', '=', 'leader')], order='vd_seq, id'),
        }

        # ----- Tien do hoc cua tung NV de gan avatar vao dung "cua ai" -----
        SCP = self.env['slide.channel.partner'].sudo()
        all_chan_ids = (zone_recs['sales'] | zone_recs['leader']).ids
        progress = {}  # partner_id -> {channel_id: member_status}
        if all_chan_ids and internal:
            for p in SCP.search([('partner_id', 'in', internal.partner_id.ids),
                                 ('channel_id', 'in', all_chan_ids)]):
                progress.setdefault(p.partner_id.id, {})[p.channel_id.id] = p.member_status

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
            """Khoa hoc NV dang dung ('cua ai' hien tai)."""
            if not recs:
                return False
            ids = recs.ids
            mine = progress.get(user.partner_id.id, {})
            if not mine:
                return ids[0]                       # chua hoc gi -> dung o cua dau
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
            } for c in recs]

        PathModel = self.env['vd.learning.path']

        def zone_paths(zk):
            paths = PathModel.search([('zone', '=', zk)], order='sequence, id')
            return [{
                'id': p.id,
                'name': p.name or '',
                'courses': course_list(p.course_ids.sorted(lambda c: (c.vd_seq, c.id))),
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
        ch = self.browse(channel_id)
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
        ch = self.browse(channel_id)
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
        return {'total': total, 'score': correct_count, 'percent': percent,
                'pass_percent': pass_percent, 'passed': percent >= pass_percent,
                'results': results}

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
    def vd_save_order(self, zone, ordered_ids):
        """Luu lai thu tu lo trinh sau khi admin keo-tha. Chi admin."""
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc sap xep lo trinh khoa hoc.')
        seq = 10
        for cid in ordered_ids:
            self.browse(cid).write({'vd_seq': seq, 'vd_role_zone': zone})
            seq += 10
        return True
