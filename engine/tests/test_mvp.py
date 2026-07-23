"""确定性逻辑单测（无需 LLM / 网络）。"""
from app.reply_gen import generate
from app.safety_gate import scan_safety, scan_handoff, scan_fm, scan_theory_exposure
from app.schemas import ReplyRequest


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
