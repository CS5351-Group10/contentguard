# 满分评分卡 — CS5351 ContentGuard（冻结前最后核对，2026-11-25）

> 快照：`main` = `dc01ad1`（2026-11-25 冻结前核对；本卡保留为冻结前审计证据）。
> 后续状态（2026-11-25）：D5 第 1 行已由 #90 补齐（canonical 5/5）；D6 权重已由 #91 改为均分 1.00；
> §4 由冻结后构建的最终 zip 解决；D8 仍为 partial（`test/live/` 仅 README）。

> 依据：`CS5351-2026-2027-project.pdf` p.5–10（D1–D9、§4 提交格式、§5 目录结构、§6 六道门）。
> 仓库快照：`main` = `dc01ad1`（含 #89）；CI 最近 5 次 push 全绿。
> 判定口径：`met` = 原文要求的关键词都能在仓库里指到；`partial` = 有交付但缺原文点名的一项；`missing` = 没有。
> 复核分工：#D2/#D6 行由 LI Shiyi 复核；其余行 + Top 5 由 LIU Jianwei 复核，分歧当场定。

## 评分卡

| # | 满分要求（原文关键词） | 证据（文件:行 / PR / sha / 测试） | 现状 | 扣分风险 | 怎么补（owner） |
|---|---|---|---|---|---|
| **D1** | machine-readable PRD + consolidated registry，`./docs/req/` 下两个 YAML/JSON；每条含 ID/type/statement/**machine-checkable fit criterion**/priority；MoSCoW 且显式写 tradeoff；NFR = metric+threshold+verification；来自既有系统分析的需求要**链接来源** | `docs/req/requirements.yaml`（31 条，含 `moscow_tradeoff_note`）；`docs/req/req-schema.json`；CI gate 3 每次提交校验（`scripts/validate_requirements.py`，run #627 绿） | **met** | 低 — schema 门真在跑，31 条与 trace matrix 一一对上 | 无需补 |
| **D2** | 11 类 artifact 分文件放 `./docs/architecture/`；ADR 含 **alternatives / rationale / consequences / reopen conditions** + 设计过程；AI 组件须给出**layered context、assembly pipeline、token-budget cap 与 compaction threshold、压缩后关键约束再注入策略** | `architecture-blueprint.md`（scope/drivers/boundaries/advisory↔authoritative/agent workflow/permissions/verification/observability/change policy 全命中）；`adr/001-…md`（alternatives/rationale/consequences/reopen 齐；:65–66 记 **8192 envelope / 6144 input cap / 4608 compaction trigger**，reinjection 有）；`adr/002-…md`；`invariants.md`、`trace-matrix.md`（31/31）、`memory-design.md`、`permission-model.md`、`runtime-policy-catalog.md`、`evaluation-table.md`、`option-ledger.md`、`evaluation-logbook.md`、`risk-list.md`、`interface-contracts.md` | **met** | 低 — 11 类齐全；唯一噪音是 `adr/001-placeholder.md` 重定向占位 | 占位文件可选删（owner: 架构） |
| **D3** | 6 份治理文件：根 `AGENTS.md`（构建目标/阅读顺序/基线/可读·可改·冻结/模块组织/集成契约/验证要求）+ `structural-constraints.md` + `mcp-tool-manifest.md` + `.opencode/permissions.jsonc`（默认全禁、逐条白名单）+ `.opencode/rules.md`（human-only）+ `.agent/rules.md`（含测试独立性、安全关键须 ADR+人工批准、上下文新鲜度） | 六份全部在仓库；`AGENTS.md` 6.2KB 且与 ADR-001 的模块布局一致 | **met** | 低 | 无需补 |
| **D4** | `verification-constraints.md`（每条 fit criterion≥1 测试、每条 invariant≥1 条**违反必失败**的负向测试、测试引用 REQ/INV、零回归）；**三层验证** structural/regression/behavioral 写清；每 PR 一份 review-memo；debt-register；bug-diary | `docs/code-governance/verification-constraints.md`（三层 + faithfulness/relevance/zero-safety-escape + negative test 全命中）；`docs/review-memo.md` **RM-001…RM-040**；`docs/bug-diary.md` **BUG-001…005**；`docs/debt-register.md` TD-1…TD-9 | **met** | 低 | 无需补 |
| **D5** | 五份**带标注**的原始 transcript，合起来覆盖六段流水线：requirements classification → architecture candidate evaluation → plan approval → build → verification compliance → architecture revision；人工干预须标 **interrupt/redirect/approve/reject + 理由** | 20 个文件在 `transcripts/`；canonical 已有 **4/5**：`61022208-LIU-Jianwei.md`（12 markers：approve2/redirect6/reject4）、`60368210-HUANG-Hongwei.md`（5 markers，含 interrupt/redirect/approve/reject 全四类）、`60105888-DA-Buna.md`（5）、`60938585-LI-Shiyi.md`（1） | **partial** | **高** — 第 1 行 `60914643-HAN-Mei.md`（requirements classification）**不存在**，`transcripts/README.md` 自己标 ⬜；缺这一段 = 六段流水线少一段 | 补 Mei 的 canonical 文件（owner: HAN Mei + PM 签署），命名 `transcripts/60914643-HAN-Mei.md`，内联 4 类 marker 至少 2 类，然后改 `transcripts/README.md` 第 1 行 |
| **D6** | 单 md 报告；**≤10,000 词**（图表不计）；**>15 页**（12pt 单倍行距）；含全员姓名学号 + **relative contribution 表**（方法自洽）；每人 **300–500 词**自省；覆盖 requirement volatility / defect trends / ambiguity resolution / artifact co-evolution / human oversight | `Report.md` = **8,606 词**（<10k ✓）、**§1–§7 齐**、自省 5 人 **338/319/372/378/350 词**（全在 300–500 内）、§2 有 phases×成员×Weight 表；但表内出现 `not reported` / `unclaimed` / `pending` 单元格，HAN Mei 权重 **0.19** | **partial** | **中** — 词数/页数/小节都够，但贡献表留着"未上报/未认领/待定"，看起来像没做完；0.19 的权重容易被质疑方法一致性 | PM 在表下补一条口径说明（哪些阶段未上报、按什么规则折算），或把已知阶段补齐（owner: PM，11/25 前） |
| **D7** | GitHub 仓库：src/tests + **CI/CD with implemented blocking gates** + **branch protection** + **meaningful commit history**；README 说明 gate 设计 | `ci.yml`：Gate1(:76)、Gate2a–2e(:36,:39,:43,:50,:62)、Gate3(:68)、Gate4 **`--strict`**(:88–92)、Gate5(:72)、Gate6(:95)；分支保护实测：required check `blocking-gates`、strict、1 approval、**code owner review ON**、enforce admins、禁 force push、linear history；`README.md` 922 词含 gate 设计与四项 README 必备内容 | **met** | 低 — 六门齐且真拦；保护设置完整可截图 | 建议截 4 张图（保护设置 / 六门绿 / 一次被拦的红 / CODEOWNERS 生效）放 Report（owner: 治理与 CI） |
| **D8** | `src/` 与 `test/` 全量代码与用例；模块名 = 架构元素；**布局区分 deterministic offline 与需 API 的 live 测试** | `src/contentguard/{analysis,api,audit,escalation,policy}` 与 ADR-001 一一对应；`test/offline/` **35 个测试文件**；`test/live/` 仅 README | **partial** | **中低** — 目录分离做到了，但 live 侧 **0 个测试**，原文说的是"live tests that require API access"，空目录严格讲不成立 | 至少放一个 `test/live/test_analysis_live.py`（无 key 时 `pytest.skip`），或 README 里写明"live 证据由 S5 会话承担 + 为何"（owner: 测试/架构，11/25 前 30 分钟能补） |
| **D9** | 根目录单个静态 `./Prompt.md`：先出**执行计划**（traceability/interface contract/scope boundaries/testing strategy/steps）→ **停等人工批准** → 再写码 → 自验证，各阶段设人工门 | `Prompt.md` 2,794 字符，关键词全命中（execution plan / approval / stop / traceability / interface / scope / test） | **met** | 低 | 无需补 |
| **§4** | zip 按 §5 目录结构装四类交付物；**README 四项**（purpose+architecture / 文件组织 / offline+live+full suite 怎么跑 / 真实 GitHub 仓库链接）；**不放 API KEY**；**demo 视频 10 分钟单独入口上传、不进 zip** | README 四项全查过（`README.md` 922 词）；`docs/release-checklist.md` 有构建方法（#89）；**zip 尚未生成**（仓库及上级目录均无 `.zip`）；视频未录；SEC-005 密钥扫描证据仍 `TBD (S4)` | **missing** | **高** — 今天 23:59 截止；这是唯一"晚一分钟就零分"的项 | 按 `docs/release-checklist.md` 构建 zip → 逐项对照 §5 目录树 → 跑一次密钥扫描并留记录 → 视频单独录 10 分钟（owner: PM；治理与 CI 出扫描证据） |
| **§5** | 指定目录树：根 6 个 md（README/AGENTS/architecture-blueprint/Prompt/Report）+ `docs/{req,architecture,code-governance}` + `.opencode/` + `.agent/` + `.github/workflows/ci.yml` + `prompts/` + `src/` + `test/{offline,live}` + `transcripts/`；`docs/ai-use-log.yaml`、`review-memo.md`、`debt-register.md`、`bug-diary.md` 在位 | 全部命中；额外文件（`docs/policy/`、`docs/evidence/`、`docs/release-checklist.md`、`handoffs/`）不违反结构 | **met** | 低 — 打 zip 时注意只装交付物，别把 `.mypy_cache/` `.pytest_cache/` `.ruff_cache/` 打进去 | 构建脚本里排除缓存与 `.git`（owner: PM） |
| **§6** | 六道门全部在 CI **真拦**：①test approval ②static analysis（lint/type/dependency + 安全路径 contract/security/API-surface/permission）③schema ④semantic eval（prompt/model 变更重放固定题库，不达标拦）⑤regression ⑥AI-use log | Gate1 现解析被引 issue 并比对时间戳（#61）；Gate2a/2b/2c(dependency `check_dependencies.py`)/2d(safety-path `check_safety_paths.py`)/2e(structural `check_structural.py`)；Gate3；Gate4 `--strict` + `test/eval/replay/{bad,good}_prompt.jsonl`（#57）；Gate5；Gate6；`docs/debt-register.md` TD-1/2/4 已关闭或标注 | **met** | 低 — 六门可逐条指到脚本与测试；gate 4 有 bad-prompt 必红的负向证据 | 无需补 |
| **§6 分支保护** | 保护要求 CI 通过；安全关键路径的改动须**人工审查 + 对应架构决策** | 实测：required check `blocking-gates`（strict）、1 个批准、**Require review from Code Owners 已开**、enforce admins、禁直推；`.github/CODEOWNERS` 对 `src/contentguard/policy/**` 指定两名 owner（避免自批死锁） | **met** | 低 | 无需补 |

## 冻结前必须修的 Top 5（按"会不会直接扣分"排序）

1. **D5 第 1 行 canonical transcript 缺失（最高）**
   `transcripts/60914643-HAN-Mei.md` 不存在，requirements-classification 这一段流水线没有证词。
   → 出文件 + 改 `transcripts/README.md` 第 1 行状态。**owner: HAN Mei + PM 签署。今天必须出，这是评分项不是文档项。**

2. **Canvas zip 还没构建（最高，且是唯一硬时限）**
   23:59 前必须按 §5 目录树打 zip；顺手跑密钥扫描留证据（REQ-SEC-005 目前 `TBD`）。
   → `docs/release-checklist.md` 有方法；**owner: PM，治理与 CI 出扫描记录。**

3. **D6 贡献表里留着 `not reported` / `unclaimed` / `pending`（中高）**
   词数页数都合规，但一张半空的表 + 0.19 的权重会被直接问"方法自洽吗"。
   → PM 在表下加一段口径说明（未上报阶段按什么规则处理），或补齐已知阶段。**owner: PM。**

4. **`test/live/` 只有 README（中低）**
   目录分离有了，但没有一个 live 测试，原文"separates … live tests that require API access"严格讲不成立。
   → 放一个无 key 时 `skip` 的 `test/live/test_analysis_live.py`，或在 README 写明 deferral 理由。**owner: 测试 + 架构，成本 30 分钟。**

5. **交付物与引用的一致性收尾（低，但翻车成本低到不值得不修）**
   - `adr/001-placeholder.md` 重定向占位，容易让人以为有两个 ADR-001；
   - Report §6 引用 transcript 文件名，若第 1 项补了文件，引用要同步；
   - 打 zip 时排除 `.mypy_cache/` `.pytest_cache/` `.ruff_cache/`。
   → 一次性过一遍。**owner: 治理与 CI + PM。**

## 复核记录

- 本卡所有"met"项均指到了具体文件/行号或实测的仓库设置，不是印象判断。
- D5 第 1 行、§4 zip 两项**未复核通过**，需 Li（D2/D6）与 Liu（其余 + Top 5）当场确认。
