"""话术生成：MingOS 编排主链路 + LLM 生成 / 确定性离线降级。

链路：安全门 → 灰区交还 → 双维诊断 → 七层透镜 → 两级委员会路由 → 生成 → FM 硬拦截。
LLM 可用（配了 DEEPSEEK_API_KEY）走月明 system prompt；无 key 走签名动作库模板降级。
"""
from __future__ import annotations
from typing import Optional
from .config import (settings, effective_api_key, effective_provider, effective_base_url,
                   effective_model, effective_llm_enabled)
from .schemas import ReplyRequest, ReplyResult, Diagnosis, RouteDecision, LensId, RiskLevel
from .safety_gate import (scan_safety, scan_handoff, scan_fm, scan_theory_exposure,
                          safety_reply_template, handoff_reply_template)
from .diagnosis import diagnose_heuristic
from .lens import select_lens, LENS_DESC
from .router import route
from .prompts import (YUEMING_SYSTEM_PROMPT, SIGNATURE_ACTIONS, INERTIA_ACTION)

# —— 确定性降级短语库（不露学派名词，画面化）——
_CAPACITY_OPEN = {
    "崩溃": "你现在最累的，可能不只是孩子这件事，是你一边担心他掉下去，一边发现自己说什么都进不去了。",
    "耗竭": "你能撑到现在，已经用掉了太多力气。先别急着找办法，你现在需要的不是再学一招。",
    "维持": "看得出你还想为这个家做点什么，这份心孩子其实感受得到。",
    "恢复": "你开始能往后退一步看这件事了，这本身就不容易。",
    "成长": "你在认真想这件事背后的系统，这份清醒很难得。",
    "发呆/停住": "你现在什么都不想做，也行。先允许自己停一下，不用马上好起来。",
}
_LENS_RENAME = {
    "L1": "他关门不是不要你，是里面自己都喘不过气；你守在门外没追进去，本身就在告诉他这世上有一个地方他碎了也回得来。",
    "L2": "你一看到他就炸，不是你脾气差，是你们俩的情绪频率撞一起了。先把自己调到不追着他的频率，他才有空间慢慢降下来。",
    "L3": "你看见的是孩子在闹，我看见的是这个家在转一个圈——你越催他越躲，这个圈不是他一个人的事。",
    "L4": "给他一个他能自己说了算的小事，不是奖励，是让他记住在这家里他的选择是算数的。",
    "L5": "接住他不等于顺着他。你可以是那个让他知道'我懂你难受，但该有的边界还在'的人。",
    "L6": "不是你家完了，是这阵子你们都在学一件特别难的事——怎么在彼此都累的时候还找得到对方。",
    "L7": "他不是比别人差，他是这个年纪、这个升学压力、这个手机时代里一个还没找到支点的孩子。",
}
_ACTION_PHRASE = {
    "存在即价值": "今天先不争对错，只找一个不带审判的时刻，说一句'妈在呢'。说完就停，不追问。",
    "空间静止_停3秒": "下次情绪要炸的时候，先物理静止 3 秒再开口，就这一个小动作。",
    "抑制控制训练": "今天可以试一次：给他东西时故意晚几秒再递，练一练'等一等'。",
    "轻动作_说完就走": "今晚挑一件最小的、他能自己定的小事交给他定，你只说一句就走，不等他回应。",
    "洗脸倒水喘息": "现在去洗把脸、倒杯水，把自己从那个循环里摘出来 3 分钟。",
    "记观察不评判": "心里记一句'他其实挺在乎的'，下次轻接就够了，不用多说。",
}


def _build_user_prompt(text: str, diag: Diagnosis, lens: list[LensId], rdec: RouteDecision) -> str:
    lens_txt = "、".join(LENS_DESC.get(l, l) for l in lens)
    ev_lines = "\n".join(f"  · {k}：{', '.join(v)}" for k, v in (diag.evidence or {}).items())
    return (
        f"家长原话：\n「{text}」\n\n"
        f"已完成的诊断（必须遵守）：\n"
        f"- 承载力状态：{diag.capacity}\n"
        f"- 行为惯性：{diag.inertia}（标签：{','.join(diag.tags) or '无'}）\n"
        f"- 主标签：{diag.primary or '—'}；次标签：{', '.join(diag.secondary) or '无'}\n"
        f"- 置信度：{diag.confidence_score}；需复核：{diag.needs_review}\n"
        f"- 命中证据：\n{ev_lines or '  ·（无）'}\n"
        f"- 激活透镜（只化进话术，不露名词）：{lens_txt}\n"
        f"- 姿态策略：{rdec.posture}\n"
        f"- 内容策略：{rdec.content_plan}\n"
        f"- 动作数量：{rdec.action_count}；禁步骤清单：{rdec.no_step_list}；邀请式：{rdec.invite_style}\n\n"
        f"请生成可直接发给家长的回复（五句结构），严格遵守上述粒度与安全门/失败模式规则。"
        f"只输出回复正文，不加标题、不加括号标注、不暴露任何理论名词。"
    )


def _generate_llm(text: str, diag: Diagnosis, lens: list[LensId], rdec: RouteDecision) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=effective_api_key() or "x", base_url=effective_base_url())
    user = _build_user_prompt(text, diag, lens, rdec)
    resp = client.chat.completions.create(
        model=effective_model(),
        messages=[{"role": "system", "content": YUEMING_SYSTEM_PROMPT},
                  {"role": "user", "content": user}],
        temperature=0.7,
        timeout=20,
    )
    return resp.choices[0].message.content.strip()


def _deterministic_reply(text: str, diag: Diagnosis, lens: list[LensId], rdec: RouteDecision) -> str:
    parts: list[str] = [_CAPACITY_OPEN.get(diag.capacity, _CAPACITY_OPEN["维持"])]
    # 重新命名句：取激活透镜第一层
    if lens:
        parts.append(_LENS_RENAME.get(lens[0], ""))
    action_key = INERTIA_ACTION.get(diag.inertia, "轻动作_说完就走")
    action_txt = _ACTION_PHRASE.get(action_key, _ACTION_PHRASE["轻动作_说完就走"])
    if rdec.action_count == 0:
        # 已松动/未就绪/证据不足：不塞新动作
        if diag.inertia == "已松动型":
            parts.append("他其实已经有了细微的变化，你看见了吗？先别急着加新的，把这份担心轻轻接住就够了。")
        elif diag.inertia == "证据不足":
            parts.append("现在信息还不太够，我不敢乱给建议。你再多说两句——比如最近家里发生了什么、你最担心的是哪一点？")
        # 未就绪 不加句
    else:
        if diag.inertia == "动太少型":
            # 具体三步（流动句，非编号清单）
            parts.append("今晚可以试试：先找个他没在防御的时刻；就说一句'我不是来吵的，是有点担心我们现在说不上话'；"
                         "说完停一停，过两天再看看他的反应。")
        else:
            # 动太多 / 默认：1 动作 + 撤离
            parts.append("给你一个小动作：" + action_txt)
    # 陪伴句
    parts.append("我就在这儿，你什么时候想说都行。")
    return "\n".join(p for p in parts if p)


def generate(req: ReplyRequest) -> ReplyResult:
    text = req.parent_message
    result = ReplyResult()

    # —— 第零步：安全门（最高优先级）——
    safety_level, safety_reasons = scan_safety(text)
    if safety_level == "安全门":
        result.safety_triggered = True
        result.risk_level = "安全门"
        result.reply = safety_reply_template()
        result.meta = "；".join(safety_reasons)
        result.source = "deterministic"
        return result

    # —— 第零点五步：高 stakes 灰区交还月明 ——
    handoff, handoff_reasons = scan_handoff(text)
    if handoff:
        result.handoff_to_yueming = True
        result.risk_level = "交还月明"
        result.reply = handoff_reply_template()
        result.meta = "；".join(handoff_reasons)
        result.source = "deterministic"
        # 交还路径下仍做诊断供月明参考，但不生成常规回复
        diag = diagnose_heuristic(text)
        lens = select_lens(text)
        result.diagnosis = diag
        result.lens = lens
        return result

    # —— 常规链路 ——
    diag = diagnose_heuristic(text)
    lens = select_lens(text)
    rdec = route(diag.capacity, diag.inertia, lens)
    result.diagnosis = diag
    result.lens = lens
    result.route = rdec
    result.risk_level = "常规"

    if effective_llm_enabled():
        try:
            reply = _generate_llm(text, diag, lens, rdec)
            result.source = "llm"
        except Exception as e:  # 网络/密钥失败 → 降级
            reply = _deterministic_reply(text, diag, lens, rdec)
            result.source = "deterministic(fallback)"
            result.meta = f"LLM 调用失败已降级: {type(e).__name__}"
    else:
        reply = _deterministic_reply(text, diag, lens, rdec)
        result.source = "deterministic"

    # —— 失败模式硬拦截（对输出）——
    fm = scan_fm(reply, diag.inertia)
    result.fm_violations = fm
    result.reply = reply

    if req.mode == "analyze":
        result.analysis = {
            "diagnosis": diag.model_dump(),
            "lens": lens,
            "lens_desc": {l: LENS_DESC.get(l, "") for l in lens},
            "route": rdec.model_dump(),
            "safety": {"level": "常规", "reasons": []},
            "fm_violations": fm,
            "risk": diag.risk,
            "needs_review": diag.needs_review,
        }
    return result
