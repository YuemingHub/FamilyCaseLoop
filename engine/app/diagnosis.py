"""双维诊断（承载力状态 × 行为惯性）——D 校准版。

设计原则（来自 回复.txt）：
1. 短语优先：尽量用多字短语命中，单字弱词需「强度词/上下文」组合才计分；
2. 主体区分：高风险语言拆到独立 risk 层，并区分「孩子说 / 家长说」；
3. 有意识暂停：PAUSE_PHRASES 命中时，阻断「动太少型」（冻结回避 ≠ 有意识克制）；
4. 多标签：输出主标签/次标签/命中证据/置信度/是否需复核；
5. 兜底不再是未就绪型：识别不足时输出「证据不足」，而非把家长默认判成未就绪。

LLM 可用时由 reply_gen 用同一套维度做结构化回填（confidence='llm'）。
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple

from .schemas import CapacityState, InertiaType, Diagnosis

# —— 强度/上下文标记 ——
INTENSITY = ["反复", "一直", "每天", "忍不住", "必须", "什么都", "次次", "总",
             "老", "天天", "一遍遍", "总想", "越着急", "成天", "动不动"]
# 动太少弱词所需的「害怕/无力」类上下文（单独出现易歧义）
FEARLESS = ["怕", "不敢", "无力", "不知道", "只能", "躲", "不敢"]

# —— 行为惯性：强短语（权重 3）——
INERTIA_STRONG: Dict[InertiaType, List[str]] = {
    "动太多型": [
        "天天跟他说", "天天跟他讲", "反复讲道理", "讲道理", "说了很多遍", "忍不住提醒", "一直催",
        "催着他", "每天盯着", "盯着他完成", "给他列计划", "给他列了计划", "给他安排得很细", "检查他做没做",
        "什么都替他想好", "一遍遍确认", "推着他往前走", "怕他落下", "怕他松懈",
        "越着急越想管", "试了很多办法", "一个方法不行又换一个", "每天围着这件事转",
        "总想马上看到变化", "天天说", "反复说", "监督他", "盯着他",
    ],
    "动太少型": [
        "不敢开口", "不敢提这件事", "一说就怕他烦", "怕他发火", "怕把关系弄得更僵",
        "不知道该不该问", "只能装作没看见", "一直拖着没处理", "就这么一天一天耗着",
        "等他自己好起来", "什么也不敢做", "想管又不敢管", "每次话到嘴边又咽回去",
        "家里没人敢提", "怕刺激他", "我现在只能躲着", "我也不知道还能做什么",
        "不敢说他", "不敢管", "不敢问", "不敢惹", "怕冲突",
    ],
    "已松动型": [
        "比前几天平静了一些", "最近愿意跟我说几句了", "今天主动出来吃饭了", "开始愿意出门了",
        "会主动回应我了", "没有像以前那样马上发火", "我说话时他能听一会儿了",
        "愿意坐下来聊几分钟", "会跟家里人开玩笑了", "最近睡眠稍微规律了一点",
        "愿意让我靠近了", "以前完全不说现在会说一点", "提到这件事时没那么抗拒了",
        "关系没有前段时间那么僵了", "他自己提出想试一试", "虽然变化不大但能感觉到在缓和",
        "愿意跟我说话了", "平静了一点", "会笑了", "出来吃", "开始笑了", "愿意说",
    ],
    "未就绪型": [
        "我现在脑子很乱", "我什么都听不进去", "我现在只想哭", "我已经不知道自己在说什么了",
        "让我先缓一缓", "我现在没办法想下一步", "一想到这件事就控制不住", "我现在特别气",
        "我现在只觉得委屈", "这件事我还没缓过来", "我不知道该从哪里说", "我现在完全理不清",
        "我就是接受不了", "我现在不想分析", "我整个人都是懵的", "我怕自己一开口就失控",
        "就是气", "完全不知道怎么办",
    ],
}

# —— 行为惯性：弱词（权重 1，必须带强度/上下文才计分）——
INERTIA_WEAK: Dict[InertiaType, List[str]] = {
    "动太多型": ["安排", "规划", "检查", "操心", "抓紧", "做了", "提醒", "催", "说教", "逼", "列计划", "列了", "盯着", "监督"],
    "动太少型": ["不问", "随他", "由着他", "等着", "顺自然数", "忍着", "回避", "耗着", "躲"],
}

# —— 有意识暂停（阻断动太少，非冻结回避）——
PAUSE_PHRASES = [
    "先没追问", "先没有问", "先不追", "想让他缓一缓", "先不逼", "让他缓一缓",
    "先观察", "先不追问他", "今天先没", "晚上再看看", "先让他缓", "冷处理",
    "先没说", "先不着急", "等他缓", "我想先不", "先别追", "先没问", "想让他缓",
]

# —— 组合反信号 ——
COLLAB_MARKERS = ["商量", "协商", "一起", "他自己决定", "他决定", "他同意", "他选",
                  "他来定", "共同", "他自己选", "他愿意"]          # 动太多反信号：共同协商
STOP_COUNTER = ["已经停下来", "不催了", "停了", "放下了", "不逼了", "不再催",
                "收手", "停下来了", "不催", "不逼"]                  # 动太多反信号：已调整
RECOVER_COUNTER = ["但一提", "一提就", "一提到", "还是抗拒", "仍然", "依旧",
                   "可是", "但", "只是"]                            # 已松动反信号：仅局部

# —— 承载力：强短语 ——
CAPACITY_STRONG: Dict[CapacityState, List[str]] = {
    "崩溃": ["我真的撑不住了", "我马上就要垮了", "我控制不住自己了", "我已经完全受不了了",
             "我不知道自己还能坚持多久", "快崩溃", "快疯了", "绝望", "撑不住", "崩溃"],
    "耗竭": ["心累", "什么都不想管了", "我已经麻木了", "一点力气都没有", "每天都像在硬撑",
             "连生气的力气都没了", "不想说话", "不想动", "只想躺着", "感觉自己被掏空了",
             "麻木", "无力", "疲惫", "累", "没招", "心死"],
    "维持": ["虽然很累但我还能处理日常", "我现在还能稳住自己", "我知道很难但还能继续",
             "我能听进去也能做一点", "情绪会起来但还能慢慢下来", "想做点什么", "试试", "努力", "办法"],
    "恢复": ["最近比前段时间好一些", "我现在能睡一点了", "情绪没那么容易失控了", "我能慢慢想清楚了",
             "遇到事情时能先停一下", "我现在能听孩子说一点了", "有好转", "能反思", "平静", "能理解", "慢慢"],
    "成长": ["我开始能看见自己的反应了", "我发现自己以前一直在催他", "我现在能分开我的焦虑和孩子的需要",
             "我知道不是马上改变孩子", "我开始能在事情发生时停下来观察", "我愿意调整自己的做法",
             "我能理解孩子为什么会这样了"],
    "发呆/停住": ["什么都不想做", "停一下", "允许停下", "发呆", "不想动", "歇着", "放空", "歇会"],
}
# 承载力优先级（同分时）：崩溃 > 耗竭 > 发呆 > 恢复 > 成长 > 维持
_CAP_PRIORITY = {"崩溃": 0, "耗竭": 1, "发呆/停住": 2, "恢复": 3, "成长": 4, "维持": 5}

# —— 情绪标签：强短语 ——
TAG_STRONG: Dict[str, List[str]] = {
    "焦虑": ["我一想到他的以后就害怕", "我怕他以后养活不了自己", "我担心他以后什么都做不了",
             "我整晚都在想他的未来", "我怕他这辈子就这样了", "我越想越慌", "我控制不住地往坏处想"],
    "防御": ["这也不能全怪我", "我已经做得够多了", "都是学校把他弄成这样的", "老师也有很大责任",
             "他自己一点都不配合", "换成谁遇到这样的孩子都没办法", "不是我不想改变是他根本不给机会"],
    "自责": ["都怪我", "是我把孩子害了", "我是不是毁了他", "我不是一个好妈妈", "我太失败了",
             "我对不起孩子", "我以前做错太多了", "如果不是我他不会变成这样", "我怎么这么没用",
             "我没有保护好他"],
}

# —— 独立高风险层（不进承载力词表；与 safety_gate 升门互补，这里额外做主体区分）——
RISK_PHRASES = ["想死", "不想活", "活够了", "想结束", "消失算了", "活着没意思",
                "我走了大家都轻松", "不想活了", "活着没意思"]
CHILD_MARKERS = ["孩子", "儿子", "女儿", "娃", "姑娘", "小子", "他说", "他跟我说", "他跟"]
PARENT_MARKERS = ["我", "我自己", "作为妈妈", "作为爸爸", "当妈", "当爹"]


# —— 否定句修饰（避免"没强逼/不催/没盯着"被误计为行为惯性证据）——
NEGATION_MARKERS = ("没", "不", "未", "没有", "别", "无", "从未", "从不")
_FLIP_WORDS = ("但是", "可是", "然而", "不过", "但")  # 转折后重置否定语境


def _occurrences(text: str, word: str) -> List[int]:
    """word 在 text 中的所有起始索引（允许重叠，不漏单字弱词）。"""
    out: List[int] = []
    start = 0
    while True:
        i = text.find(word, start)
        if i == -1:
            break
        out.append(i)
        start = i + 1
    return out


def _is_negated(text: str, pos: int, span: int = 6) -> bool:
    """pos 处命中是否被否定词修饰：看其前 span 字窗口内是否有否定标记。

    若窗口含转折词，只取最后一个转折词之后的部分再判否定，
    避免"虽然没催，但后来又催"里第二处被误判为否定。
    """
    win = text[max(0, pos - span):pos]
    last_flip, last_flip_len = -1, 0
    for flip in _FLIP_WORDS:
        fi = win.rfind(flip)
        if fi > last_flip:
            last_flip, last_flip_len = fi, len(flip)
    if last_flip != -1:
        win = win[last_flip + last_flip_len:]
    return any(neg in win for neg in NEGATION_MARKERS)


def _scan_word(text: str, word: str) -> Tuple[bool, List[str]]:
    """扫描 word 所有出现。返回(是否存在非否定出现, 被否定修饰的片段列表)。"""
    has_pos = False
    neg_snips: List[str] = []
    for pos in _occurrences(text, word):
        if _is_negated(text, pos):
            neg_snips.append(text[max(0, pos - 3):pos + len(word) + 1])
        else:
            has_pos = True
    return has_pos, neg_snips


def _strong_hits(text: str, phrases: List[str],
                 neg_collector: Optional[List[str]] = None,
                 filter_negation: bool = True) -> List[str]:
    out: List[str] = []
    for p in phrases:
        if p not in text:
            continue
        if filter_negation:
            has_pos, negs = _scan_word(text, p)
            if has_pos:
                out.append(p)
            if neg_collector is not None and negs:
                neg_collector.extend(negs)
        else:
            out.append(p)
    return out


def _weak_hits(text: str, weak: List[str], need_intensity: bool,
               neg_collector: Optional[List[str]] = None) -> List[str]:
    """弱词需带强度词(动太多) 或 强度/害怕上下文(动太少) 才计分；否定句修饰的弱词不计分。"""
    if not any(w in text for w in weak):
        return []
    has_intensity = any(m in text for m in INTENSITY)
    has_fear = any(m in text for m in FEARLESS)
    ok = has_intensity if need_intensity else (has_intensity or has_fear)
    if not ok:
        return []
    out: List[str] = []
    for w in weak:
        if w not in text:
            continue
        has_pos, negs = _scan_word(text, w)
        if has_pos:
            out.append(w)
        if neg_collector is not None and negs:
            neg_collector.extend(negs)
    return out


def _scan_risk(text: str) -> Optional[dict]:
    for rp in RISK_PHRASES:
        if rp in text:
            idx = text.find(rp)
            window = text[max(0, idx - 14):idx]
            if any(m in window for m in CHILD_MARKERS):
                subject = "孩子"
            elif any(m in window for m in PARENT_MARKERS):
                subject = "家长"
            else:
                subject = "未明(偏孩子)"
            return {"level": "high", "subject": subject, "evidence": [rp]}
    return None


def _conf_from_score(score: int) -> float:
    if score >= 6:
        return 0.9
    if score >= 3:
        return 0.8
    if score >= 1:
        return 0.55
    return 0.3


def diagnose_heuristic(text: str) -> Diagnosis:
    notes: List[str] = []
    evidence: Dict[str, List[str]] = {}

    # —— 风险层（独立）——
    risk = _scan_risk(text)

    # —— 行为惯性评分 ——
    in_scores: Dict[InertiaType, int] = {}
    in_evidence: Dict[InertiaType, List[str]] = {}
    neg_snips: List[str] = []  # 被否定修饰、不计分的命中片段（供人工复核追溯）
    for typ, strong in INERTIA_STRONG.items():
        hits = _strong_hits(text, strong, neg_collector=neg_snips)
        score = len(hits) * 3
        weak = _weak_hits(text, INERTIA_WEAK.get(typ, []),
                          need_intensity=(typ == "动太多型"),
                          neg_collector=neg_snips)
        score += len(weak) * 1

        # 组合反信号
        if typ == "动太多型":
            if any(c in text for c in COLLAB_MARKERS):
                if score > 0:
                    score = 0
                    notes.append("存在共同协商/孩子自主，不判动太多（非单方推动）")
            elif any(c in text for c in STOP_COUNTER):
                if score > 0:
                    score = min(score, 1)
                    notes.append("曾动太多，但当前已调整，仅保留历史证据")
        if typ == "动太少型" and any(p in text for p in PAUSE_PHRASES):
            score = 0
            notes.append("疑似有意识暂停，非冻结回避，不判动太少")

        in_scores[typ] = score
        if hits or weak:
            in_evidence[typ] = hits + [f"(弱){w}" for w in weak]

    if neg_snips:
        notes.append("否定句排除(不作为行为惯性证据)：" + "、".join(dict.fromkeys(neg_snips)))

    top_in = max(in_scores, key=lambda k: in_scores[k])
    if in_scores[top_in] == 0:
        inertia: InertiaType = "证据不足"
        needs_review = True
        notes.append("证据不足/待补充信息（不再默认丢进未就绪型）")
    else:
        inertia = top_in
        needs_review = False
        # 已松动但仅局部
        if inertia == "已松动型" and any(c in text for c in RECOVER_COUNTER):
            needs_review = True
            notes.append("局部松动，非整体恢复，置信度降")
        # 动太多历史反信号 → 不简单判当前仍为动太多
        if inertia == "动太多型" and any(c in text for c in STOP_COUNTER):
            inertia = "证据不足"  # type: ignore
            needs_review = True
            notes.append("曾动太多，当前已调整，无法确认当前状态→证据不足")

    in_conf = _conf_from_score(in_scores[top_in]) if inertia != "证据不足" else 0.25

    # —— 承载力评分 ——
    cap_scores: Dict[CapacityState, int] = {}
    for cap, phrases in CAPACITY_STRONG.items():
        cap_scores[cap] = len(_strong_hits(text, phrases, filter_negation=False))
    # 取命中最多；同分按优先级
    best_cap = max(cap_scores, key=lambda c: (cap_scores[c], -_CAP_PRIORITY[c]))
    capacity = best_cap if cap_scores[best_cap] > 0 else "维持"
    cap_conf = _conf_from_score(cap_scores[best_cap])

    # —— 情绪标签（多标签）——
    tags = [tag for tag, phrases in TAG_STRONG.items() if any(p in text for p in phrases)]

    # —— 冲突裁决：情绪满 + 误判已松动 → 强制未就绪 ——
    if capacity in ("崩溃", "耗竭") and inertia == "已松动型":
        inertia = "未就绪型"  # type: ignore
        notes.append("情绪满却判已松动→误判高危区，强制未就绪")

    # —— 组装主/次标签、证据、置信度 ——
    primary = inertia if inertia != "证据不足" else "证据不足"
    secondary: List[str] = []
    if capacity != "维持":
        secondary.append(capacity)
    secondary += tags
    if risk:
        secondary.append(f"风险:{risk['subject']}")

    if in_evidence:
        evidence["惯性"] = in_evidence.get(inertia if inertia != "证据不足" else top_in, []) or \
                           [v for vs in in_evidence.values() for v in vs]
    if capacity != "维持" and cap_scores[capacity] > 0:
        evidence["承载力"] = _strong_hits(text, CAPACITY_STRONG[capacity], filter_negation=False)
    if tags:
        evidence["标签"] = tags
    if risk:
        evidence["风险"] = risk["evidence"]

    conf_score = round(max(in_conf, cap_conf), 2)

    return Diagnosis(
        capacity=capacity,
        inertia=inertia,
        tags=tags,
        confidence="heuristic",
        note="；".join(notes),
        primary=primary,
        secondary=secondary,
        evidence=evidence,
        confidence_score=conf_score,
        needs_review=needs_review,
        risk=risk,
    )
