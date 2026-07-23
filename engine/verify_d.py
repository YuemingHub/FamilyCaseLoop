"""D 校准验收：原 4 样本 + 6 边界样本。

直接调用 diagnose_heuristic（不经过安全门短路），重点验证：
- 惯性命中是否符合预期（尤其动太多/动太少不再误判未就绪）
- 主体识别（孩子/家长风险）
- 有意识暂停 / 共同协商 / 仅局部松动 等边界是否被正确处理
- 兜底是否仍为「证据不足」而非「未就绪型」
"""
from app.diagnosis import diagnose_heuristic

# (样本, 期望惯性, 期望要点)
SAMPLES = [
    # —— 原 4 样本 ——
    ("我天天跟他讲道理，还给他列了计划，催着他做，结果他更烦了", "动太多型", "动太多命中"),
    ("我不敢说他，怕他烦，我们就这么耗着，我也不问他", "动太少型", "动太少命中"),
    ("这两天他好像平静了一点，愿意跟我说话了，还会笑了", "已松动型", "已松动命中"),
    ("我快崩溃了，每天跟他吵，我就是气，说不清", "未就绪型", "崩溃+未就绪（说不清不再单独触发未就绪）"),

    # —— 新增 6 边界样本 ——
    ("我今天先没有问他，想让他缓一缓，晚上再看看。", "证据不足", "有意识暂停，不判动太少"),
    ("我以前每天催他、给他列计划，这几天已经停下来了。", "证据不足", "曾动太多，当前已调整，不判当前动太多"),
    ("他今天出来吃了一顿饭，但一提上学还是很抗拒。", "已松动型", "局部松动，置信度降，非整体恢复"),
    ("我现在说不清楚具体原因，但我的情绪还算稳定。", "证据不足", "说不清楚但情绪稳定，不判未就绪"),
    ("孩子说他不想活了，我现在完全不知道怎么办。", "未就绪型", "孩子风险(主体=孩子)+家长未就绪"),
    ("我给他列了一个计划，是我们两个人商量以后，他自己决定照着试一周。", "证据不足", "共同协商制定，不判动太多"),
]


def fmt_evidence(ev: dict) -> str:
    if not ev:
        return "（无）"
    return "；".join(f"{k}=[{','.join(v)}]" for k, v in ev.items())


def main():
    print("=" * 78)
    print("D 校准验收报告 · diagnose_heuristic（10 样本）")
    print("=" * 78)
    ok = 0
    for i, (text, exp_inertia, exp_note) in enumerate(SAMPLES, 1):
        d = diagnose_heuristic(text)
        passed = (d.inertia == exp_inertia)
        ok += 1 if passed else 0
        print(f"\n样本{i}  [{'PASS' if passed else 'FAIL'}]  期望惯性={exp_inertia} | 实际={d.inertia}")
        print(f"  原话：{text}")
        print(f"  主标签：{d.primary} ｜ 次标签：{','.join(d.secondary) or '无'}")
        print(f"  承载力：{d.capacity} ｜ 情绪标签：{','.join(d.tags) or '无'}")
        print(f"  置信度：{d.confidence_score} ｜ 需复核：{d.needs_review}")
        print(f"  命中证据：{fmt_evidence(d.evidence)}")
        if d.risk:
            print(f"  风险层：主体={d.risk['subject']} 证据={d.risk['evidence']}")
        print(f"  备注：{d.note or '—'}")
        print(f"  期望要点：{exp_note}")
    print("\n" + "=" * 78)
    print(f"结果：{ok}/{len(SAMPLES)} 样本惯性判定符合预期")
    # 兜底逻辑检查
    trash = diagnose_heuristic("今天天气不错。")
    print(f"兜底检查：中性文本 → inertia={trash.inertia}（应为'证据不足'，不再是'未就绪型'）")
    print("=" * 78)


if __name__ == "__main__":
    main()
