# BCI 论文追踪器 — OpenClaw + ChatGPT 5.4 场景实现计划

## 0. 目标与设计原则

把现有的"定时搜论文"任务改造成一个可被 OpenClaw 定时或手动触发的场景：OpenClaw 负责调度、文件读写、命令执行与结果回报；ChatGPT 5.4 作为该场景的主模型，只承担需要判断力的筛选与摘要写作。

整个任务拆成两层：

1. **确定性代码层**（一个 Python CLI 包 `bci-tracker`）：负责所有机械、可复现、可单测的工作——算日期、调各来源 API、解析 JSON/XML、归一化成统一 schema、跨源去重、附加确定性信号（期刊层级）、写中间产物。**这一层不做任何质量判断**，只负责"把最近一周所有命中的论文如实收集起来"。
2. **OpenClaw 场景/方法论层**（一个场景 `bci-weekly-paper-tracker`，配套一个可复用技能或知识文件 `bci-paper-curation`）：由 OpenClaw 触发，并让 ChatGPT 5.4 阅读候选池后应用筛选方法论，负责从候选池里挑 4–6 篇、写两句话总结、写入选理由、处理"论文不够"的情况。

### 数据流

```
[OpenClaw 场景触发]  →  [bci-tracker fetch]  →  bci_candidates_{date}.json   (确定性：全部命中 + 信号，无判断)
        ↓
[OpenClaw agent + ChatGPT 5.4 + bci-paper-curation]  →  selection_{date}.json   (判断 + 文字)
        ↓
[bci-tracker render]  →  bci_papers_raw_{date}.md   (确定性：校验 + 套模板渲染)
        ↓
[OpenClaw 回报/投递]  →  简要状态、失败源、最终文件路径
```

### 关键安全属性（必须实现）

`selection_{date}.json` 里每篇论文**只携带三个字段**：`id`、`two_sentence_summary`、`selection_reason`。所有硬信息（标题 / 作者 / 机构 / venue / 日期 / DOI / 链接）由 `render` 步骤**按 `id` 从 `bci_candidates_{date}.json` 里取出**后填入模板，渲染器**忽略** selection 里出现的任何其它元数据。

后果：模型即使想伪造链接或机构也注入不进去；它唯一能自由书写的只有"两句话总结"和"入选理由"两段文字，而方法论文件会约束这两段必须基于摘要、不得出现摘要里没有的数字。若 selection 里的某个 `id` 在候选池中找不到，`render` 直接报错退出。这把"请不要编造"从一句口头约束变成了结构性保证。

---

## 1. 仓库结构

```
bci-tracker/
├── pyproject.toml              # 依赖：requests, lxml, python-dateutil, pyyaml；可选 rapidfuzz
├── README.md
├── config.yaml                 # 全部可调参数（见 §6）
├── openclaw/
│   ├── scenarios/
│   │   └── bci-weekly-paper-tracker.md
│   │       # OpenClaw 场景入口：触发条件、执行步骤、回报格式、模型建议
│   └── skills/
│       └── bci-paper-curation/
│           └── SKILL.md
│               # ChatGPT 5.4 使用的方法论：筛选、总结、入选理由、论文不足处理
├── src/bci_tracker/
│   ├── __init__.py
│   ├── cli.py                  # 入口：fetch / render / dry-run
│   ├── config.py               # 读取 + 校验 config.yaml
│   ├── schema.py               # Candidate dataclass + 序列化
│   ├── dates.py                # START/END 计算（tz=Asia/Shanghai）+ 窗口 padding
│   ├── http.py                 # session、重试、限流、超时、UA
│   ├── sources/
│   │   ├── base.py             # Source 接口：fetch(start, end, cfg) -> list[Candidate]
│   │   ├── pubmed.py
│   │   ├── biorxiv.py
│   │   ├── medrxiv.py
│   │   ├── arxiv.py
│   │   └── semantic_scholar.py # 可选
│   ├── enrich.py               # 尽力补全缺失机构（如打开 arXiv abs 页），标注来源
│   ├── dedup.py                # 按 DOI / 归一化标题合并，正式版优先
│   ├── scoring.py              # 按白名单给 venue_tier（仅确定性信号）
│   ├── pool.py                 # 编排 sources → dedup → score → 写 bci_candidates.json
│   └── render.py               # 读 selection + bci_candidates → 校验 → 套模板渲染 .md
└── tests/
    ├── fixtures/               # 冻结的真实 API 响应样本
    ├── test_dates.py
    ├── test_pubmed_parse.py
    ├── test_biorxiv_parse.py
    ├── test_arxiv_parse.py
    ├── test_dedup.py
    ├── test_scoring.py
    └── test_render_validate.py # 重点：selection 里有伪造 id/元数据时必须被拒
```

> 开发期把 OpenClaw 场景文件与技能文件放在仓库 `openclaw/` 下。部署时把 `openclaw/scenarios/bci-weekly-paper-tracker.md` 和 `openclaw/skills/bci-paper-curation/` 安装到你的 OpenClaw 实例能发现的位置；具体目录名按当前 OpenClaw 配置处理，不在代码层硬编码。

---

## 2. 数据契约

### 2.1 Candidate（候选池中每条记录）

```python
# schema.py
@dataclass
class Candidate:
    id: str                      # 规范 id：优先 DOI，其次 arXiv id，再次 "source:localid"
    source: str                  # pubmed | biorxiv | medrxiv | arxiv | semantic_scholar
    title: str
    authors: list[str]           # ["Last, F. M.", ...]，按原始顺序
    affiliations: list[str]      # 可能为空或不全
    corresponding_institution: str | None   # bioRxiv/medRxiv 直接给
    venue: str                   # 期刊全名，或 "preprint:arXiv" / "preprint:bioRxiv" 等
    venue_tier: int | None       # 1/2/3，由 scoring 按白名单确定；预印本默认 None 或 3
    doi: str | None              # arXiv-only 可能为 None
    url: str                     # https://doi.org/... 或 arXiv abs 链接
    published_date: str          # YYYY-MM-DD（落在本地周窗内）
    abstract: str
    matched_keywords: list[str]
    raw: dict                    # 原始 API 记录，便于追溯/调试
```

`bci_candidates_{date}.json` 顶层结构：

```json
{
  "date": "2026-06-05",
  "window": {"start": "2026-05-29", "end": "2026-06-05", "tz": "Asia/Shanghai"},
  "sources": {
    "pubmed":   {"status": "ok",     "hit": 12, "kept": 9},
    "biorxiv":  {"status": "ok",     "hit": 4,  "kept": 3},
    "medrxiv":  {"status": "ok",     "hit": 2,  "kept": 2},
    "arxiv":    {"status": "ok",     "hit": 7,  "kept": 6},
    "semantic_scholar": {"status": "skipped", "reason": "rate_limited"}
  },
  "candidates": [ /* Candidate[] 去重后 */ ]
}
```

### 2.2 selection（OpenClaw 场景中由 ChatGPT 5.4 产出，唯一允许 LLM 写的东西）

```json
{
  "date": "2026-06-05",
  "selected": [
    {
      "id": "10.1088/1741-2552/xxxxx",
      "two_sentence_summary": "第一句讲做了什么/方法；第二句讲关键结果或意义。",
      "selection_reason": "一句话，落在质量/相关性/代表性上。"
    }
  ],
  "not_enough": false,
  "notes": ""
}
```

`render` 只信任 `selected[].id` 去池子里取硬信息；其余字段一律从候选池回填。

---

## 3. 代码层 — 各模块职责

- **dates.py**：以 Asia/Shanghai 计算 `END=今天`、`START=END-7天`。注意各 API 用 UTC 日期，存在 ±1 天边界风险——拉取时把 API 日期窗 **左右各 pad 1 天**，落库前再用每篇论文的日期**精确过滤**回本地周窗。提供 `to_local_date()` 工具。
- **http.py**：单一 `requests.Session`；指数退避重试（连接错误 / 5xx / 429）；全局限流器（按 `config.http.rate_limit_per_sec`，PubMed 必须 ≤3/s）；统一超时与 UA。
- **sources/base.py**：定义 `Source.fetch(start, end, cfg) -> list[Candidate]`，每个源各自负责"调用 + 解析 + 归一化 + 本地过滤"，失败时抛出可被 pool 捕获并记入 `sources[*].status` 的异常。
- **enrich.py**：尽力补全缺失的 `affiliations`（主要面向 arXiv：打开 abs 页解析作者单位）。补不到就保持空，并在 `raw` 里标 `enrich: "failed"`。**纯尽力而为，不得阻塞主流程。**
- **dedup.py**：先按 `doi` 合并；无 DOI 时用归一化标题（小写、去标点、压空格；可用 `rapidfuzz` 设较保守阈值，并要求日期相近）合并，避免误并。合并时**正式发表版优先**作为规范记录，预印本信息保留在 `raw.also_seen_as`。
- **scoring.py**：按 `config.journal_tiers` 把 venue 映射到 `venue_tier`（**纯确定性**，不做"好不好"的主观判断；那是 OpenClaw 场景/方法论层的事）。预印本给 None 或 3。
- **pool.py**：编排所有启用的源 → 汇总 → dedup → score → 写 `bci_candidates_{date}.json` 及 `sources` 状态块。
- **render.py**：
  1. 读 `selection_{date}.json` 与 `bci_candidates_{date}.json`；
  2. 对每个 `selected[].id` 在候选池查找，**找不到即报错退出**；
  3. 用候选池里的硬信息 + selection 的两段文字，按 §5.5 的固定模板渲染最终 `.md`；
  4. 校验：`selected` 数量在 `[total_min, total_max]` 内；每源入选不超过 `per_source_cap`（违反则报错，提示 OpenClaw 重跑筛选步骤）；
  5. 若 `not_enough=true` 或 `selected` 为空，按模板写"未发现足够高质量论文"的文末说明。

---

## 4. 已验证的 API 参考（直接照此实现，不要再猜参数）

### PubMed（NCBI E-utilities） base: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
- 搜索取 PMID：
  `esearch.fcgi?db=pubmed&datetype=pdat&reldate=7&retmode=json&retmax=50&term=<urlencoded>&tool=bci_tracker&email=<你的邮箱>`
  → 读 `esearchresult.idlist`。`reldate=7` + `datetype=pdat` = 发表日落在过去 7 天内。
- 取详情：
  `efetch.fcgi?db=pubmed&id=<逗号分隔PMID>&retmode=xml&tool=bci_tracker&email=<邮箱>`
  → MEDLINE XML，逐篇提取：`ArticleTitle`；`Abstract/AbstractText`（可能多段带 Label，需拼接）；`AuthorList/Author`（`LastName`+`ForeName`，每作者 `AffiliationInfo/Affiliation`）；`Journal/Title`（期刊全名）+ `JournalIssue/PubDate`；`ArticleIdList/ArticleId[@IdType="doi"]`（或 `ELocationID[@EIdType="doi"]`）。
- 限流：无 API key 时 ≤3 次/秒（间隔 ≥0.34s）；`efetch` 单次可传 ~200 个 id。

### bioRxiv / medRxiv（CSHL API） base: `https://api.biorxiv.org`
- `details/<server>/<START>/<END>/<cursor>/json`，`server` = `biorxiv` 或 `medrxiv`。
- bioRxiv 追加 `?category=neuroscience`（空格换下划线、可小写）；**medRxiv 无合适单一类目 → 不加 category，全量拉后本地过滤**。
- `cursor` 取 0、100、200… 翻页直到 `collection` 为空（每页 100）；`messages[].count`/total 可读总量。
- 字段：`doi`、`title`、`authors`（"Last, F.M." 分号连接）、`author_corresponding`、`author_corresponding_institution`、`date`、`category`、`abstract`、`published`（未进期刊为 "NA"，否则为正式版信息）。
- **该 API 不支持关键词检索** → 拉窗口后在 `title`+`abstract` 上用 `local_filter_terms` 过滤。
- 兜底：加 `category` 后结果为 0 或异常时，去掉 category 全量拉取再本地过滤。

### arXiv API base: `http://export.arxiv.org/api/query`
- `?search_query=<urlencoded>&sortBy=submittedDate&sortOrder=descending&start=0&max_results=50`
- 返回 Atom XML，逐条提取：`title`、`summary`（摘要）、`author/name`（含可选 `arxiv:affiliation`，**常为空**）、`published`、`updated`、`id`（abs 链接）、`link[@title="pdf"]`、`category@term`。
- **无 reldate** → 用 `<published>`（或 `<updated>`）在 `[START,END]` 内本地过滤。作者单位通常缺失 → 走 `enrich.py` 尽力补；补不到则机构留空。

### Semantic Scholar（可选） 
`https://api.semanticscholar.org/graph/v1/paper/search?query=<...>&fields=title,authors,abstract,venue,publicationDate,externalIds,url&limit=30`
→ 用 `publicationDate` 本地过滤近一周；有限流，遇 429 退避并将该源标为 `skipped`。

---

## 5. OpenClaw 场景与方法论层

这一层包含两个文件：

- `openclaw/scenarios/bci-weekly-paper-tracker.md`：OpenClaw 的场景入口，描述触发方式、执行步骤、模型建议、回报格式和失败处理。
- `openclaw/skills/bci-paper-curation/SKILL.md`：给 ChatGPT 5.4 使用的筛选方法论，只负责判断与文字，不负责抓取或最终渲染。

若你的 OpenClaw 版本只支持单文件场景，就把 `SKILL.md` 的方法论正文合并进场景文件的 `curation_rules` 或等价段落；核心约束不变：模型只产出 `id`、`two_sentence_summary`、`selection_reason`。

### 5.1 场景文件 — `bci-weekly-paper-tracker`

场景文件建议写成 OpenClaw 可读的 runbook。字段名可以按实际 OpenClaw 版本调整，但语义保持一致：

```markdown
---
name: bci-weekly-paper-tracker
description: 每周或手动执行 BCI/EEG 论文追踪，抓取候选池、调用 ChatGPT 5.4 做筛选、渲染最终 Markdown。
model: chatgpt-5.4              # OpenClaw provider 中配置的模型别名
tools:
  - shell
  - filesystem
schedule: manual_or_weekly      # 具体 cron / 定时写法按 OpenClaw 实例配置
---

你是 OpenClaw 中的 BCI 论文追踪代理。按顺序执行：
1. 在项目根目录运行 `bci-tracker fetch`，生成 `bci_candidates_{date}.json`。
2. 读取候选池，应用 `bci-paper-curation` 方法论，只生成 `selection_{date}.json`。
3. 运行 `bci-tracker render`，由渲染器校验并生成最终 Markdown。
4. 只回报执行摘要：候选数、入选数、失败源、是否论文不足、最终文件路径。

不要在聊天窗口里直接展开最终论文摘要；最终内容以 Markdown 文件为准。
若任一步失败，保留中间文件，报告失败命令、失败源和可重试建议。
```

### 5.2 方法论文件 frontmatter

`openclaw/skills/bci-paper-curation/SKILL.md` 建议包含 YAML frontmatter，方便 OpenClaw 或其它本地代理按描述主动选用：

```yaml
---
name: bci-paper-curation
description: >
  从 bci-tracker 生成的候选论文池（bci_candidates_{date}.json）中筛选并撰写每周 BCI/EEG
  论文追踪摘要。每当 OpenClaw 场景需要为脑机接口/神经接口论文做质量筛选、
  挑选代表性论文、写两句话总结与入选理由，或处理"本周高质量论文不足"的情形时，
  都使用本方法论。本方法论由 ChatGPT 5.4 执行，只做判断与文字，不负责抓取或最终渲染。
---
```

### 5.3 输入输出契约（写进方法论正文）
- 输入：一个 `bci_candidates_{date}.json` 路径（由 `bci-tracker fetch` 产出），schema 见本计划 §2.1。
- 产出：一个 `selection_{date}.json`，schema 见 §2.2。**只写 `id` + 两段文字**，硬信息由渲染器回填。
- 工具边界：ChatGPT 5.4 可以读取候选池并写 selection 文件；不要让模型手写最终 Markdown，也不要让模型补写 DOI、机构、作者、链接等硬信息。

### 5.4 筛选方法论（正文核心）
按重要性排序的筛选标准：
1. **venue 质量**：同行评审期刊 > 预印本；优先 `venue_tier` 高者（白名单：Nature Neuroscience、Nature Biomedical Engineering、Brain 等为一级；Journal of Neural Engineering、IEEE TNSRE、IEEE TBME、NeuroImage 等为二级；预印本为三级）。
2. **真·相关性**：必须确实属于 BCI/神经接口/神经解码，而非只是顺带提了一句 EEG 的无关研究（例如把 EEG 仅作旁支测量的非 BCI 临床研究，相关性低）。临床向的癫痫样波检测、ICU 连续脑电监护、睡眠分期等属于强相关。
3. **代表性与信息密度**：优先方法/结论有看点的论文；在子方向上**分散**（motor imagery、SSVEP/P300、解码方法、临床 EEG、脑电基础模型等），避免选 5 篇几乎同质的文章。
4. **同研究去重偏好**：同一研究若正式版与预印本都在，选正式版。
5. **配额**：每源 ≤2 篇，合计 4–6 篇（与 config 一致）。

两句话总结规则：第 1 句=做了什么/方法，第 2 句=关键结果或意义；**严格基于 `abstract`**，不得写出摘要里没有的数字或结论。
入选理由：一句话，落在上面的质量/相关性/代表性维度。
缺失字段：若候选池里某硬信息为空，不要臆测；交给渲染器，模板会显示"（原数据未提供）"。
**不足处理**：若真正相关且达标的候选 < 4 篇，置 `not_enough=true` 并在 `notes` 说明，**不要为凑数硬塞**。

### 5.5 最终 Markdown 模板（render.py 用，方法论正文也附一份以对齐预期）

```markdown
# BCI论文追踪原始摘要
业务日期：{date}
时区：Asia/Shanghai
时间范围：最近一周（{start} 至 {end}）
检索来源：PubMed / bioRxiv / medRxiv / arXiv（+ 可选 Semantic Scholar）
采集方式：API 优先，浏览器兜底

## 入选论文{n}
- 标题：{title}
- 作者：{authors}
- 所属机构/工作室/实验室：{affiliation_or_placeholder}
- 来源平台：{source} / {venue}
- 发布时间：{published_date}
- 关键词：{matched_keywords}
- 链接（含DOI）：{url}{doi_suffix}
- 两句话总结：{two_sentence_summary}
- 入选理由：{selection_reason}

（重复 N 篇）

---
检索说明：
- 各来源命中/入选：PubMed {hit}/{kept}；bioRxiv …；medRxiv …；arXiv …
- 浏览器兜底条目：{若有则列出，否则"无"}

# 若不足：
- 最近一周内未发现足够高质量且适合纳入摘要的相关论文。
```

### 5.6 场景要带 2–3 个测试用例
给 OpenClaw 场景写几条真实风格的测试输入（例如"执行本周 BCI 论文追踪"、"对 bci_candidates_2026-06-05.json 做本周筛选并产出 selection.json"），用样例候选池跑一遍，人工 + 简单断言评估（如：selected 数量合规、每源不超配额、not_enough 逻辑正确、总结里不含摘要外数字、最终 Markdown 的硬信息全部来自候选池）。

---

## 6. config.yaml 规格

```yaml
timezone: Asia/Shanghai
window_days: 7

sources:
  pubmed: true
  biorxiv: true
  medrxiv: true
  arxiv: true
  semantic_scholar: false       # 默认关，限流时再开

keywords:
  pubmed_term: >
    ("brain-computer interface"[tiab] OR "brain-machine interface"[tiab]
     OR "motor imagery"[tiab] OR "EEG decoding"[tiab] OR "neural interface"[tiab])
  arxiv_search_query: >
    (cat:eess.SP OR cat:cs.HC OR cat:q-bio.NC OR cat:cs.LG)
    AND (abs:"brain-computer interface" OR abs:"motor imagery" OR abs:EEG)
  local_filter_terms:           # 用于 biorxiv/medrxiv/arxiv/ss 的本地过滤
    - brain-computer interface
    - brain-machine interface
    - BCI
    - EEG
    - motor imagery
    - neural decoding
    - SSVEP
    - P300

biorxiv:
  category: neuroscience        # medrxiv 留空 → 不加 category

journal_tiers:                  # 归一化期刊名 → 层级
  tier1: ["Nature Neuroscience", "Nature Biomedical Engineering", "Brain"]
  tier2: ["Journal of Neural Engineering", "IEEE Transactions on Neural Systems and Rehabilitation Engineering",
          "IEEE Transactions on Biomedical Engineering", "NeuroImage"]
  # 其余期刊 tier3；预印本 None

selection:
  per_source_cap: 2
  total_min: 4
  total_max: 6

ncbi:
  tool: bci_tracker
  email: "<你的邮箱>"

http:
  rate_limit_per_sec: 3
  timeout_seconds: 30
  max_retries: 3
  user_agent: "bci-tracker/0.1 (mailto:<你的邮箱>)"

output:
  dir: "/Users/zuqiu/Documents/openclaw/bci"
  candidates_filename: "bci_candidates_{date}.json"
  final_filename: "bci_papers_raw_{date}.md"
```

---

## 7. 测试计划

- **冻结 fixtures**：先对每个源各跑一次真实请求，把响应（脱敏后）存到 `tests/fixtures/`（`pubmed_esearch.json`、`pubmed_efetch.xml`、`biorxiv.json`、`arxiv.atom` 等）。之后所有解析测试都离线跑。
- **解析单测**：每个源用 fixture 断言字段正确提取（标题/作者/机构/DOI/日期/摘要）。
- **dedup 单测**：同 DOI 合并；预印本+正式版 → 正式版为规范记录；无 DOI 的近似标题在保守阈值下正确合并、且不误并不同研究。
- **scoring 单测**：白名单期刊 → 正确 tier；未知期刊 → tier3；预印本 → None。
- **dates 单测**：窗口数学、tz、±1 天 padding 后精确过滤的边界行为。
- **render/validate 单测（重点）**：
  - selection 里出现池中不存在的 `id` → 报错退出；
  - 合法 selection → 渲染正确，且**硬信息全部来自候选池**（即便 selection 里塞了错误元数据也被忽略）；
  - 数量越界 / 超配额 → 报错。
- **dry-run**：`bci-tracker fetch --dry-run` 只打印各源命中数，不写文件。

---

## 8. 边界与防护

- **某源挂掉**：重试后仍失败则跳过该源，在 `sources[*].status` 记 `failed` + 原因，最终 Markdown 文末如实反映，**不让整体任务失败**。
- **限流**：PubMed 严格 ≤3/s；Semantic Scholar 遇 429 退避并标 `skipped`。
- **时区 ±1 天**：见 §3 dates.py，拉宽窗 + 精确过滤。
- **bioRxiv category 大小写/无果**：去 category 全量拉取兜底。
- **arXiv 机构缺失**：enrich 尽力补，补不到留空 + 模板占位。
- **dedup 误并**：标题匹配用保守阈值并要求日期相近。
- **反编造**：由 §0 的 render 校验从结构上保证；OpenClaw 方法论层再加摘要约束。

---

## 9. OpenClaw 场景 prompt

代码、场景与方法论文件就位后，OpenClaw 里的触发 prompt 可以保持很短：

```
执行 BCI 论文追踪场景（模型：ChatGPT 5.4）：
1) 在项目根目录运行 `bci-tracker fetch`（按 config.yaml），产出 bci_candidates_{date}.json。
2) 读取该候选池，应用 bci-paper-curation 方法论，产出对应的 selection_{date}.json。
   selection 顶层只能包含 date、selected、not_enough、notes；selected[] 每项只能包含
   id、two_sentence_summary、selection_reason。
3) 运行 `bci-tracker render`，校验并渲染最终文件到
   /Users/zuqiu/Documents/openclaw/bci/bci_papers_raw_{date}.md。
4) 简要回报：各源命中/保留/入选数、是否有源失败、是否触发"论文不足"、最终文件路径。
不要把结果直接发到聊天窗口；完成后关闭临时打开的浏览器页签或外部资源。
```

---

## 10. 实现路线图（建议顺序）

- **M0 脚手架**：仓库、pyproject、config 读取+校验、Candidate schema、dates、http。
- **M1 PubMed 源**（价值最高，先做）：esearch+efetch、XML 解析、fixture、单测。
- **M2 bioRxiv + medRxiv 源**：窗口拉取 + cursor 翻页 + 本地关键词过滤 + 单测。
- **M3 arXiv 源 + enrich**：Atom 解析 + 客户端日期过滤 + 机构兜底 + 单测。
- **M4 Semantic Scholar（可选）**。
- **M5 dedup + scoring + pool**：产出 bci_candidates.json；实现 `--dry-run`。
- **M6 render + 校验（安全关键）**：模板渲染 + 反编造校验 + 单测。
- **M7 撰写 OpenClaw 场景 + 方法论文件并测试**：补齐 `openclaw/scenarios/bci-weekly-paper-tracker.md` 与 `openclaw/skills/bci-paper-curation/SKILL.md`，用 2–3 个测试用例跑通一次真实的端到端。
- **M8 收尾**：OpenClaw 场景 prompt、README、接入定时调度。

> 每个里程碑都先写测试/fixture 再实现；M6 的校验测试是整个反编造保证的落点，务必覆盖。
