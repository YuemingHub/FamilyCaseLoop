"""确定性逻辑单测（无需 LLM / 网络）。"""
from app.reply_gen import generate
from app.safety_gate import scan_safety, scan_handoff, scan_fm, scan_theory_exposure
from app.schemas import ReplyRequest
from app.diagnosis import diagnose_heuristic


def test_safety_death():
    lvl, reasons = scan_safety("他说不想活了，还把自己关在房间里")
    assert lvl == "安全门"


def test_safety_denial_override():
    lvl, _ = scan_safety("活着没意思，但也不想死，就是懒得动")
    assert lvl is None


def test_safety_violence_hard():
    lvl, _ = scan_safety("他拿刀了，我快拦不住")
    assert lvl == "安全门"


def test_handoff_hard():
    ok, _ = scan_handoff("我想办退费手续不续了")
    assert ok is True


def test_handoff_soft_hesitant():
    ok, _ = scan_handoff("我在犹豫要不要给他办休学")
    assert ok is False  # 犹豫期，不交还


def test_theory_exposure():
    exp = scan_theory_exposure("根据依恋理论和自我决定论，孩子需要安全感")
    assert "依恋" in exp


def test_fm_step_list_on_manyi():
    v = scan_fm("第一，你去做作业；第二，你别玩手机", "动太多型")
    assert any("FM7" in x for x in v)


def test_reply_safety_shortcuts():
    r = generate(ReplyRequest(parent_message="他说不想活了"))
    assert r.safety_triggered and r.risk_level == "安全门"


def test_reply_handoff():
    r = generate(ReplyRequest(parent_message="我想给孩子办退学手续"))
    assert r.handoff_to_yueming and r.risk_level == "交还月明"


def test_reply_deterministic_no_theory_leak():
    r = generate(ReplyRequest(parent_message="孩子天天玩手机，我一说他就吼我，我快崩溃了"))
    assert r.reply
    assert r.risk_level == "常规"
    assert scan_theory_exposure(r.reply) == []
    assert r.fm_violations == []


# —— 否定句弱词误命中修复（甲鱼案"没强逼"问题）——
def test_diagnosis_negation_excludes_weak_word():
    # "天天"提供强度，若无否定检测"逼"会命中→动太多型(0.55)；修复后应被排除
    d = diagnose_heuristic("我们天天也没强逼他")
    assert d.inertia != "动太多型"
    assert "否定句排除" in (d.note or "")


def test_diagnosis_no_false_negation_suppress():
    # 正向控制：天天催他 + 忍不住提醒 → 仍判动太多型（"催"未被否定）
    d = diagnose_heuristic("我天天催他写作业，忍不住提醒")
    assert d.inertia == "动太多型"


def test_diagnosis_flip_resets_negation():
    # 转折：一开始没催，但后来又天天催了 → 第二处"催"非否定，应计分→动太多型
    d = diagnose_heuristic("一开始我没催他，但后来又天天催了")
    assert d.inertia == "动太多型"


# —— S3 安全门自伤/自杀意念补全（家瑞案触发）——
def test_safety_self_harm_action():
    """自伤行为关键词必须升门"""
    lvl, reasons = scan_safety("孩子伤害了自己")
    assert lvl == "安全门"
    lvl, reasons = scan_safety("孩子割腕了")
    assert lvl == "安全门"


def test_safety_pill_overdose():
    """服药过量正则（吃N片）必须升门"""
    lvl, reasons = scan_safety("孩子吃了布洛芬12片")
    assert lvl == "安全门"
    lvl, reasons = scan_safety("她吃了8片安眠药")
    assert lvl == "安全门"


def test_safety_harmful_liquid():
    """吞食有害液体必须升门"""
    lvl, reasons = scan_safety("孩子喝了洗衣液")
    assert lvl == "安全门"
    lvl, reasons = scan_safety("她吞了消毒液")
    assert lvl == "安全门"


def test_safety_suicidal_ideation_expanded():
    """扩充的自杀意念表述必须升门"""
    lvl, _ = scan_safety("孩子说想离开世界")
    assert lvl == "安全门"
    lvl, _ = scan_safety("不知道活着的意义在哪里")
    assert lvl == "安全门"
    lvl, _ = scan_safety("孩子说活着没有方向")
    assert lvl == "安全门"


def test_safety_jiarui_case_full_text():
    """家瑞案真实脱敏文本复跑：必须从'常规'升为'安全门'"""
    text = ("为了逃避考试，吃了布洛芬12片，还喝洗衣液伤害自己来不上学。"
            "去医院处理后回家，彻底不上学了，觉得活着没有方向，想离开世界。")
    lvl, reasons = scan_safety(text)
    assert lvl == "安全门"
    assert len(reasons) >= 2  # 至少命中2个自伤/意念信号


def test_safety_no_false_positive_normal_medication():
    """正常吃药不误触发（无数字+片组合）"""
    lvl, _ = scan_safety("孩子每天按时吃药，医生开的")
    assert lvl is None
