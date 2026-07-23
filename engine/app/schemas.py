"""请求/响应数据模型。"""
from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

CapacityState = Literal["崩溃", "耗竭", "维持", "恢复", "成长", "发呆/停住"]
InertiaType = Literal["动太多型", "动太少型", "已松动型", "未就绪型", "证据不足"]
RiskLevel = Literal["安全门", "交还月明", "常规"]
LensId = Literal["L1", "L2", "L3", "L4", "L5", "L6", "L7"]


class ReplyRequest(BaseModel):
    parent_message: str = Field(..., min_length=1, description="家长第一人称原话")
    context: Optional[str] = Field(None, description="可选：家庭级历史上下文（多轮/既往风险）")
    mode: Literal["reply", "analyze", "multi"] = "reply"


class Diagnosis(BaseModel):
    capacity: CapacityState = "维持"
    inertia: InertiaType = "证据不足"   # 默认改为"证据不足"：识别不足时不再自动丢进未就绪型
    tags: List[str] = Field(default_factory=list)
    confidence: str = "heuristic"
    note: str = ""
    # —— D 校准新增（短语/权重/主体/风险层）——
    primary: str = ""                       # 主标签（如 "动太多型" / "崩溃+未就绪型"）
    secondary: List[str] = Field(default_factory=list)   # 次标签（承载力/情绪/风险）
    evidence: dict = Field(default_factory=dict)         # {维度: [命中短语]}
    confidence_score: float = 0.0           # 整体置信度 0-1
    needs_review: bool = False              # 是否需人工复核
    risk: Optional[dict] = None             # 独立安全风险层：{"level","subject","evidence"}


class RouteDecision(BaseModel):
    posture: str = ""          # L1 姿态委员会输出
    content_plan: str = ""     # L2 内容委员会输出
    action_count: int = 1
    invite_style: bool = True
    no_step_list: bool = False
    lens: List[LensId] = Field(default_factory=list)


class ReplyResult(BaseModel):
    reply: str = ""
    diagnosis: Diagnosis = Field(default_factory=Diagnosis)
    lens: List[LensId] = Field(default_factory=list)
    risk_level: RiskLevel = "常规"
    safety_triggered: bool = False
    handoff_to_yueming: bool = False
    route: RouteDecision = Field(default_factory=RouteDecision)
    fm_violations: List[str] = Field(default_factory=list)
    source: str = "deterministic"   # deterministic | llm
    meta: str = ""
    analysis: Optional[dict] = None
