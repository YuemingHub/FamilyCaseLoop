# FamilyCaseLoop · 月明家庭教育系统（统一仓库）

> 本仓库是「月明家庭教育系统」的**统一载体**：月明自用调试 + 同行引导前端，共用同一份引擎代码，不再分散在多个仓库。

## 一、定位与两轨统一

最初分过两个仓库（自用版 `parent-reply-mvp` + 同行版 `FamilyCaseLoop`）。现按"统一在这里"的指令合并为单一仓库：

| 目录 | 是什么 | 谁来验收 |
|---|---|---|
| **`engine/`** | 方法论引擎（安全门 / 双维诊断 / 七层透镜 / 路由 / 回复生成 / FM 拦截）。既是**月明本地调试沙盒**（调到"觉得可以用了"），也是**同行引导前端复用的内核** | 月明本人 + 同行试用 |
| **`guide/`**（待建） | 同行版引导前端：把 S0–S8 串成同行可自己走通的界面，直接 `import engine` | 同行试用 + 月明复核 |
| **`docs/`** | 个案全生命周期（S0–S8）↔ 本地工作台资产映射 | — |

- **受众（同行版）**：教育工作者 / 咨询师 / 研究者 / 家庭教育从业者。
- **形态**：一个个案从**开始到服务结束**的整个链路（S0–S8）引导。
- **不重新发明逻辑**：引擎复用 `parent-reply` skill 方法论；引导前端复用 `FamilyEduPortable` 工作台现有资产（工作流文档 / 知识库）。

## 二、仓库结构

```
FamilyCaseLoop/
├── engine/                      # 统一引擎（月明调试沙盒 + 同行共用内核）
│   ├── app/                     # diagnosis / reply_gen / router / safety_gate / web / config / schemas / lens / prompts / api
│   ├── tests/                   # pytest，当前 10 passed
│   ├── verify_d.py              # D 任务诊断词表验收脚本（10 样本）
│   ├── D_calibration_report.md  # D 验收报告（词表规则 + 删降清单 + 样本结果）
│   ├── requirements.txt
│   ├── run.py                   # 本地启动 web 引导 + 引擎
│   └── .env.example             # 复制为 .env 填 LLM key（不进版本库）
├── docs/
│   └── case-lifecycle-mapping.md  # S0–S8 ↔ 本地工作台资产映射
├── guide/                       # （待建）同行引导前端
├── README.md
└── .gitignore
```

## 三、与本地工作台的关系（防重复造）

- 本地工作台 `FamilyEduPortable` **已有完整"个案从开始到服务结束"处理链**，不是从零造。
- 同行版 = 把"现有工作流文档 + 知识库 + 已代码化引擎"包成引导前端，不是新引擎。
- 引擎 S3（风险分级/安全门）/ S5（双维诊断）/ S6（回复生成）/ S7（输出质检）为共用内核，不在引导前端重写。

## 四、当前进度

- ✅ 仓库建立（GitHub: `YuemingHub/FamilyCaseLoop`，已 push `main`）
- ✅ **引擎并入本仓库**（`engine/`），含 D 诊断词表校准：
  - 短语优先 + 弱词降权
  - 高风险语言拆到独立 `risk` 层并区分「孩子 / 家长」主体
  - 有意识暂停（`PAUSE_PHRASES`）阻断「动太少型」
  - 多标签带主/次 + 命中证据 + 置信度 + 是否需复核
  - 兜底从「未就绪型」改为「证据不足」（未就绪不再是识别失败的垃圾桶）
- ✅ 引擎验收：`verify_d.py` 10/10 + `pytest` 10 passed
- ✅ 映射文档（`docs/case-lifecycle-mapping.md`）
- ⏳ **B：搭 `guide/` 引导前端骨架**（复用 `engine` + 工作台资产，把 S0–S8 串成界面）
- ⏳ **C：填真实案例容器缺口**（S8 服务档案落点，待月明落真实个案）

## 五、安全底线（沿用 START.md 红线）

- **不面向家长、不部署外部机器人**。
- 未成年人高危场景（橙/红）严格隔离，必须人工复核，不接原始个案进对外链路。
- 密钥不出本机、不进版本库（见 `.gitignore`）。
- 内容转化（S9，若含）属"自媒体/对外"，按 `31_真实服务闭环主收口规则.md` 第 1 节"不适用"，需隔离、不接原始个案。

## 六、本地运行

```bash
cd engine
pip install -r requirements.txt
cp .env.example .env        # 填 LLM_PROVIDER / API_KEY（可选，无 key 走确定性降级）
python run.py               # 启动 web 引导 + 引擎
python verify_d.py          # 跑诊断词表验收（10 样本）
pytest tests/ -q            # 跑单测
```
