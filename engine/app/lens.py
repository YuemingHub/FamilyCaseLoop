"""七层理论透镜选择（确定性）。一次最多激活 2 层，取信号命中最多的 1-2 层。"""
from __future__ import annotations
from typing import List
from .prompts import LENS_SIGNALS
from .schemas import LensId

# 层描述（用于分析输出与 LLM 提示）
LENS_DESC: dict[LensId, str] = {
    "L1": "依恋理论：孩子用推开来确认你不会走",
    "L2": "情绪共调节：先稳场再谈事",
    "L3": "家庭系统：看互动循环而非怪某个人",
    "L4": "自我决定论：保护自主感，邀请而非指令",
    "L5": "权威型教养：温暖而有边界",
    "L6": "叙事理论：把问题家庭改写为学习中的家庭",
    "L7": "发展生态：把孩子放回年龄/学校/现实压力去病理化",
}


def select_lens(text: str, top: int = 2) -> List[LensId]:
    scored: List[tuple[int, LensId]] = []
    for lid, words in LENS_SIGNALS.items():
        s = sum(w in text for w in words)
        if s > 0:
            scored.append((s, lid))
    scored.sort(key=lambda x: -x[0])
    picked = [lid for _, lid in scored[:top]]
    return picked or ["L1"]
