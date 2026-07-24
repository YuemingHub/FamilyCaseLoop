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
