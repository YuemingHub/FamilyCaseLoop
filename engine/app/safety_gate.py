"""安全门与失败模式硬拦截（确定性层，无需 LLM 即可运行与单测）。

优先级：安全门 > 交还月明 > 常规。
安全门内部：自伤行为/显性暴力/失联/家长自危 始终升门；隐性消亡信号在「反向否认」存在时降级（不升门）。
"""
from __future__ import annotations
import re
from typing import List, Optional, Tuple

# —— 自伤行为（始终升安全门，最高优先级）——
# 实际自伤动作或方法，不等同于意念，必须立即升门
SELF_HARM_ACTIONS = [
    "伤害自己", "割腕", "割手", "割自己", "吞药", "吃药过量", "过量服药",
    "喝洗衣液", "喝消毒液", "喝洁厕灵", "喝农药", "喝漂白剂", "喝洗洁精",
    "撞墙", "撞头", "咬自己", "烫自己", "烧自己", "掐自己",
    "结束生命", "了结自己",
]

# —— 服药过量正则（吃N片/吃了XX N片）——
PILL_OVERDOSE_RE = re.compile(r"吃.{0,10}\d+片")

# —— 自伤行为正则（伤害了自己/伤害着自己/自我伤害等变体）——
SELF_HARM_RE = re.compile(r"伤害.{0,3}自己|自我伤害|自残|自伤")

# —— 有害液体吞食正则（喝/吞/吃 + 有害液体名）——
_HARMFUL_LIQUIDS = ["洗衣液", "消毒液", "洁厕灵", "农药", "漂白剂", "洗洁精",
                    "安眠药", "百草枯"]
_HARMFUL_INGEST_RE = re.compile(r"(喝|吞|吃).{0,6}(" + "|".join(_HARMFUL_LIQUIDS) + ")")
# 反向：有害液体名 + (喝/吞/吃) 也可
_HARMFUL_INGEST_RE2 = re.compile(r"(" + "|".join(_HARMFUL_LIQUIDS) + r").{0,6}(喝|吞|吃)")

# —— 显性风险（始终升安全门）——
VIOLENCE_HARD = ["拿刀", "跳楼", "殴打", "家暴", "伤人", "失联", "离家出走",
                 "夜不归宿", "联系不上", "幻觉", "精神异常", "失控"]

# —— 家长自危（升安全门，优先于交还月明）。仅放明确自害行为；
#  "活着没意思/真想消失/不想活了"等属消亡信号，走下方 DEATH_WORDS + 反向否认覆盖路径（skill line 203）——
PARENT_SELF_HARM = ["一走了之", "开进江里", "开江里"]

# —— 消亡/隐性求救词（升安全门，除非反向否认）——
DEATH_WORDS = ["不想活", "活不下去", "想死", "自杀", "自伤", "自残", "轻生",
               "不在了", "没我也好", "拖累所有人", "拖累", "受罪无意义",
               "睡死过去", "闭眼不开", "不醒来", "尸体", "死人", "没气",
               "像具尸体", "活着没意思", "活着没劲", "受罪",
               # 自杀意念表述（家瑞案触发补充）
               "离开世界", "想离开", "不想存在", "活着的意义", "活着没有方向",
               "没有活着的", "找不到意义", "解脱", "想消失", "消失算了"]

# —— 反向否认（优先，不升安全门，按发呆/耗竭接住）——
DENIAL_WORDS = ["不想死", "没想死", "就是懒得动", "只是无聊", "只是发呆",
                "不想死就是", "就是累"]

# —— 高 stakes 灰区交还月明（硬）——
HANDOFF_HARD = ["离婚", "分居", "退费", "换机构", "解约", "起诉", "不续了",
                "暂时到此为止", "专业判断", "帮我拿个主意", "听听你的判断"]

# —— 高 stakes 灰区（软：需结合「下定/办手续」才交还）——
HANDOFF_SOFT = ["退学", "休学", "复学", "学籍", "搬家转学"]

# —— 学派名词暴露（FM6）——
THEORY_TERMS = ["依恋理论", "自我决定论", "SDT", "自主感", "胜任感", "关系感",
                "家庭系统", "互动循环", "叙事理论", "权威型", "发展生态",
                "共调节", "鲍文", "布朗芬布伦纳", "依恋", "共调节"]

# —— 指令式（FM3）——
IMPERATIVE = ["你应该", "你必须", "你去做", "你要学会", "你就是太"]

# —— 非消亡表述（不升门，耗竭隐喻）——
NON_DEATH = ["行尸走肉", "没灵魂", "空壳", "累死了", "累瘫"]


def _has_denial(text: str) -> bool:
    return any(w in text for w in DENIAL_WORDS)


def scan_safety(text: str) -> Tuple[Optional[str], List[str]]:
    """返回 (风险等级, 原因列表)。风险等级为 '安全门' 或 None。"""
    # 1. 自伤行为（最高优先级，实际动作不等同意念）
    harm_hit = [w for w in SELF_HARM_ACTIONS if w in text]
    if harm_hit:
        return "安全门", [f"自伤行为:{w}" for w in harm_hit]
    if SELF_HARM_RE.search(text):
        return "安全门", ["自伤行为:伤害自己(正则匹配)"]
    if PILL_OVERDOSE_RE.search(text):
        return "安全门", ["自伤行为:服药过量(吃N片)"]
    if _HARMFUL_INGEST_RE.search(text) or _HARMFUL_INGEST_RE2.search(text):
        return "安全门", ["自伤行为:吞食有害液体"]
    # 2. 显性暴力/失联/精神异常
    if any(w in text for w in VIOLENCE_HARD):
        return "安全门", ["显性风险信号(暴力/失联/精神异常)"]
    if any(w in text for w in PARENT_SELF_HARM):
        return "安全门", ["家长自危线索(优先于交还)"]
    # 3. 消亡信号（带反向否认则降级）
    if "消失" in text and not any(m in text for m in ["消失一天", "躲清静"]):
        if not _has_denial(text):
            return "安全门", ["消亡信号:消失(无反向否认)"]
    death_hit = [w for w in DEATH_WORDS if w in text]
    if death_hit:
        if _has_denial(text):
            # 反向否认优先，不升门（按发呆/耗竭接住，由诊断层处理）
            return None, []
        return "安全门", [f"消亡信号:{w}" for w in death_hit]
    return None, []


def scan_handoff(text: str) -> Tuple[bool, List[str]]:
    """高 stakes 灰区 → 交还月明。返回 (是否交还, 原因)。"""
    hard = [w for w in HANDOFF_HARD if w in text]
    if hard:
        return True, [f"硬灰区:{w}" for w in hard]
    soft = [w for w in HANDOFF_SOFT if w in text]
    if soft:
        # 软灰区需结合"下定/办手续/交给定夺"才交还
        decided = ("办手续" in text) or ("办" in text and "手续" in text) or any(
            w in text for w in ["下定", "定夺", "交给你", "你帮我定", "决定办", "这周就办"])
        if decided:
            return True, [f"软灰区已决:{w}" for w in soft]
        return False, [f"软灰区疑似(犹豫期):{s}" for s in soft]
    return False, []


def scan_theory_exposure(text: str) -> List[str]:
    return [w for w in THEORY_TERMS if w in text]


def _has_numbered_list(text: str) -> bool:
    import re
    return bool(re.search(r"(一、|二、|三、|第一|第二|第三|\d+\.\s|\d+、|步骤一|步骤二|步骤三)", text))


def scan_fm(reply: str, inertia: str = "") -> List[str]:
    """失败模式扫描（FM1-9 中可确定化部分）。"""
    v: List[str] = []
    if any(w in reply for w in IMPERATIVE):
        v.append("FM3指令式动作")
    if "只要你" in reply and ("就" in reply):
        v.append("FM9承诺结果")
    exp = scan_theory_exposure(reply)
    if exp:
        v.append("FM6理论露名词:" + ",".join(exp))
    if inertia == "动太多型" and _has_numbered_list(reply):
        v.append("FM7粒度超量/禁清单:动太多型出现步骤清单")
    if inertia == "动太少型" and any(w in reply for w in ["别做", "不要做", "禁止"]):
        v.append("FM4禁清单错配:动太少型出现禁令列表")
    return v


def safety_reply_template() -> str:
    return ("这已经不是普通亲子沟通问题了，先不要急着讲道理，也不要隔着门继续刺激他。"
            "现在第一件事是确保安全：尽量让一个稳定的成年人陪你一起在场，保持距离但不要让他独处在高风险环境里；"
            "如果有自伤工具、跳楼风险或联系不上，请立刻联系当地急救/警方/医院精神心理急诊。"
            "等安全先稳住，我们再谈后面的沟通。")


def handoff_reply_template() -> str:
    return ("这件事我不敢替月明老师替你拍板。它牵扯到你们家一个挺关键的岔路口，"
            "需要月明老师本人结合你们整个情况来判断才稳。你先别急着做决定，"
            "我先把你的情况转给月明老师，她会亲自回你。")
