# 每日网络热点采集与归纳工具

抓取国内 6 个主流平台的热榜，做**跨平台去重、聚类、分类、评分**，自动写出一份带结论的日报（HTML + Markdown）。

纯 Python 标准库实现，无需安装任何依赖，单个目录即可迁移。

## 快速开始

```bash
# 首次运行（抓取 + 分析 + 生成报告）
python run.py

# 只看前 8 个话题
python run.py --top 8

# 只抓微博和知乎
python run.py --sources weibo,zhihu

# 断网时用最近一次数据重新归纳
python run.py --offline
```

Windows 下可直接双击 `run.bat`。

## 输出

| 路径 | 说明 |
| --- | --- |
| `reports/latest.html` | 最新日报，单文件自包含，可直接发人/存档 |
| `reports/YYYY-MM-DD.html` | 按日期归档的日报 |
| `reports/YYYY-MM-DD.md` | 同样内容的 Markdown，方便粘进文档/公众号 |
| `reports/index.html` | 历史日报索引 |
| `data/YYYY-MM-DD.json` | 原始抓取数据 + 分析结果，用于复盘与二次加工 |
| `samples/example-report.html` | 一份示例日报，不跑也能看效果（`data/`、`reports/` 为运行时生成，不入库） |

## 数据源

| 平台 | 接口 | 抓到的量 |
| --- | --- | --- |
| 微博 | `weibo.com/ajax/side/hotSearch` | 约 50 条实时热搜 |
| 抖音 | `iesdouyin.com/web/api/v2/hotsearch/billboard` | 50 条热榜 |
| 头条 | `toutiao.com/hot-event/hot-board` | 50 条 |
| 百度 | `top.baidu.com/api/board` | 约 50 条 |
| 知乎 | `api.zhihu.com/topstory/hot-lists/total` | 30 条热榜 |
| B站 | `api.bilibili.com/x/web-interface/search/square` | 30 条热搜 |

均为公开接口，并发抓取，单源失败不影响整体（失败情况会在报告页标注）。

## 归纳是怎么做的

不是简单罗列榜单，中间有四层加工：

**1. 热度统一打分**
各平台热度口径不同（微博是讨论数、抖音是热度值、知乎是"万热度"），直接比没有意义。所以先做**平台内归一**：排名分 + 对数热度分各占一半，再乘平台影响力权重。平台置顶位（政宣固定位）单独降权。

**2. 跨平台话题聚类**
同一件事在不同平台措辞不同——微博叫「台独给周杰伦扣帽子国台办回应」，知乎叫「如何看待国台办回应周杰伦…」。
用中文 2/3-gram + IDF 加权算**包含度相似度**（长标题不会被短标题拖低），再做 leader 聚类。
为防误并设了三道闸：极短标题要求更高相似度、泛标签（如 `nba`）不参与放宽、共享词信息量不足不合并。

**3. 分类与性质打标**
14 个类目（时政/国际/军事/财经/科技/体育/健康/教育/汽车/游戏/娱乐/社会/生活/其他），关键词长度加权，娱乐与体育额外挂了人名/战队名表来识别"只有名字没有实词"的标题。
叠加事件性质标签：官方回应 / 突发事件 / 争议讨论 / 政策新规 / 数据突破 / 商业动态。

**4. 生成结论**
不是模板填空，是从数据里取事实再组织语言：
- 规模与结构（多少条、聚成多少话题、哪些类目占主导）
- 头部三件事（标题、类目、热度、哪几个平台、最好排名）
- 跨平台共振（哪些话题真正穿透了圈层）
- 平台差异（某平台哪类内容比整体高多少个百分点）
- 注意力集中度（前 5 话题占全部关注度的比例）

## 目录结构

```
hotspot/
├── run.py        CLI 入口：调度抓取 → 分析 → 渲染
├── sources.py    6 个平台的抓取与字段归一
├── analyzer.py   打分、聚类、分类、摘要生成
├── report.py     HTML / Markdown / 索引页渲染
├── config.py     平台配置与分类词典（要调分类就改这里）
├── explainer.py  “为什么火”大白话归因引擎
├── run.bat       Windows 一键运行
├── samples/      示例日报（example-report.html）
└── data/ reports/  运行时生成，不入库（见 .gitignore）
```

## 想改点什么

- **调整分类**：改 `config.py` 里的 `CATEGORIES`。关键词越长权重越高（`len(kw)**1.2`），专有名词表（`CELEBS` / `SPORTS_TEAMS` / `BRANDS_CAR`）在文件末尾并入对应类目。
- **加平台**：在 `sources.py` 写一个 `_p_xxx()` 解析函数返回 `{title, url, heat, rank, label}`，注册到 `PARSERS`，再在 `config.py` 的 `PLATFORMS` 里加一行。
- **调聚类松紧**：`analyzer.py` 顶部的 `SIM_MERGE`（默认 0.42）调低更爱合并，调高更保守。
- **每天自动跑**：把 `python run.py` 挂到系统计划任务，或让 WorkBuddy 建一个每日定时任务。

## 已知边界

- 热榜每分钟在变，"日报"是某一时刻的快照，采集时间会写在报告页眉。
- 平台接口无官方承诺，改版会导致某个源失效——`run.py` 会在控制台和报告页标出哪个源没抓到。
- 分类基于关键词，遇到新梗、新人名会落到"其他"，属正常损耗；补词即可。
- 聚类阈值偏保守，宁可漏合并也不硬凑，所以跨平台共振数是偏低估的。
