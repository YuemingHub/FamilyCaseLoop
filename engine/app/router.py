"""MingOS 两级委员会路由。

L1 姿态委员会：按承载力状态 + 激活透镜，决定"接住强度 / 是否稳场 / 边界 / 陪伴"策略。
L2 内容委员会：按行为惯性，决定"动作粒度 / 动作数量 / 是否禁步骤清单 / 邀请式"。

两级输出合并为 RouteDecision，供 reply_gen 约束生成。
"""
from __future__ import annotations
from .schemas import CapacityState, InertiaType, LensId, RouteDecision


def l1_posture_committee(capacity: CapacityState, lens: list[LensId]) -> str:
    """姿态委员会：决定回复强度与姿态。"""
    if capacity in ("崩溃", "耗竭"):
        return "高接住强度：先稳场、少讲道理，只给极小动作或不给动作"
    if capacity == "发呆/停住":
        return "只给允许停下的空间，零建议，纯情绪容器"
    if capacity == "维持":
        return "接住 + 给一个可启动的小动作"
    if capacity == "恢复":
        return "接住 + 小动作 + 轻提醒，避免用力过猛"
    if capacity == "成长":
        return "接住 + 可略解释一点系统逻辑，仍不露名词"
    return "接住 + 小动作"


def l2_content_committee(inertia: InertiaType) -> RouteDecision:
    """内容委员会：决定动作粒度（不变量：邀请式、说完就走）。"""
    base = RouteDecision(invite_style=True)
    if inertia == "动太多型":
        base.action_count = 1
        base.no_step_list = True
        base.content_plan = "只给 1 个动作 + 撤离指令，禁止步骤清单（她需要被叫停）"
    elif inertia == "动太少型":
        base.action_count = 3
        base.no_step_list = False
        base.content_plan = "具体三步（时机+台词+后续）+ 回访机制"
    elif inertia == "已松动型":
        base.action_count = 0
        base.no_step_list = True
        base.content_plan = "不加新动作，镜像孩子变化 + 轻接她的担忧"
    elif inertia == "证据不足":
        base.action_count = 0
        base.no_step_list = True
        base.content_plan = "证据不足：零建议，请家长补充信息后再判（需人工复核）"
    else:  # 未就绪型
        base.action_count = 0
        base.no_step_list = True
        base.content_plan = "零建议，纯情绪容器，只做命名和包容"
    return base


def route(capacity: CapacityState, inertia: InertiaType, lens: list[LensId]) -> RouteDecision:
    posture = l1_posture_committee(capacity, lens)
    decision = l2_content_committee(inertia)
    decision.posture = posture
    decision.lens = lens
    return decision
