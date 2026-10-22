# -*- coding: utf-8 -*-
"""个性化引擎：把"全网热点"翻译成"对你有用"的投资/副业信号。

针对方向：投资 / 理财 / 副业
四类信号：机会 / 风险 / 对标 / 点子
输出：个人关注榜 + 四类信号清单 + 方向调整建议

改方向只需改下面 USER_FOCUS / CAT_RELEVANCE / SECTORS / SIGNAL_KEYWORDS 四处。
"""
from collections import Counter, defaultdict

# ============ 你的方向配置 ============
USER_FOCUS = {
    "label": "投资 / 理财 / 副业",
    "tagline": "从每日热点里找钱袋子的机会、风险与可落地点子",
}

# 类目与你的相关度（0~1）：财经最高，娱乐/体育最低
CAT_RELEVANCE = {
    "财经": 1.00, "科技": 0.92, "时政": 0.86, "国际": 0.82, "汽车": 0.80,
    "军事": 0.72, "健康": 0.70, "社会": 0.62, "生活": 0.56, "教育": 0.42,
    "游戏": 0.38, "娱乐": 0.26, "体育": 0.24, "其他": 0.30,
}

# 关键词 → 赛道/板块（把热点映射到可投资/可切入的领域）
# 关键词越长、命中越多，映射越准
SECTORS = [
    (["AI", "人工智能", "大模型", "芯片", "半导体", "GPU", "算力", "英伟达", "OpenAI",
      "DeepSeek", "机器人", "智能体", "具身智能", "数据中心", "大模型", "算法"], "AI 与算力产业链"),
    (["新能源", "锂电", "电池", "光伏", "储能", "充电桩", "氢能", "固态电池", "风电", "核电"], "新能源产业链"),
    (["新能源车", "汽车", "问界", "比亚迪", "特斯拉", "小米汽车", "智驾", "自动驾驶", "新车", "销量", "续航", "换电"], "智能汽车"),
    (["医疗", "医院", "医生", "创新药", "生物", "疫苗", "医保", "集采", "药价", "药品", "私立医院", "体检", "医美"], "医药医疗"),
    (["军工", "国防", "军事", "导弹", "航母", "武器", "解放军", "军演", "战机"], "军工国防"),
    (["黄金", "金价", "美联储", "降息", "加息", "汇率", "人民币", "美元", "央行", "利率", "比特币", "白银"], "宏观与贵金属"),
    (["房地产", "房价", "楼市", "房贷", "公积金", "限购", "房企", "保交楼", "土地"], "房地产"),
    (["消费", "白酒", "食品", "零售", "奶茶", "咖啡", "国货", "新消费", "双十一", "电商", "品牌", "直播带货"], "大消费"),
    (["游戏", "电竞", "元宇宙", "Steam", "米哈游", "手游", "二次元", "短剧", "微短剧", "IP改编", "IP授权"], "游戏与传媒"),
    (["手机", "手表", "耳机", "穿戴", "折叠屏", "消费电子", "iPad", "平板", "笔记本", "小天才", "iPhone", "折叠", "穿戴设备"], "消费电子"),
    (["出海", "跨境电商", "外贸", "TikTok", "亚马逊", "海外", "出口", "关税", "中欧班列"], "出海与跨境电商"),
    (["低空经济", "卫星", "航天", "无人机", "火箭", "空间站", "商业航天", "卫星互联网"], "低空经济与商业航天"),
    (["养老", "退休", "养老金", "银发", "老龄化", "独居", "适老"], "银发经济"),
    (["旅游", "文旅", "景区", "露营", "民宿", "文旅消费", "酒店", "机票"], "文旅消费"),
    (["一人公司", "副业", "创业", "个人IP", "自媒体", "个体户", "灵活就业", "自由职业", "摆摊", "开店", "数字游民", "知识付费"], "副业与个人创业"),
    (["教育", "培训", "职教", "考研", "留学", "课程"], "教育服务"),
]

# 四类信号的触发词（越长越准）
SIGNAL_KEYWORDS = {
    "机会": ["利好", "增长", "大涨", "涨停", "创新高", "新高", "获批", "放开", "补贴",
             "风口", "需求", "涨价", "扩产", "加码", "试点", "突破", "首次", "纪录",
             "回暖", "复苏", "超预期", "放量", "新赛道", "新职业", "出圈", "爆发",
             "翻倍", "供不应求", "订单", "转机", "提速", "量产"],
    "风险": ["暴跌", "崩盘", "暴雷", "爆雷", "处罚", "罚款", "监管", "约谈", "召回",
             "违规", "造假", "退市", "破产", "倒闭", "裁员", "维权", "禁令", "收紧",
             "债务", "违约", "停牌", "下滑", "亏损", "腰斩", "缩水", "起火", "事故",
             "踩雷", "举报", "起诉", "隐患", "收缩", "过冬", "入冬", "骗局", "风险提示", "被查"],
    "对标": ["上市", "融资", "IPO", "收购", "并购", "营收", "销量", "破纪录", "新高",
             "龙头", "首富", "创始人", "赚钱", "盈利", "业绩", "财报", "交付", "出海",
             "拿下", "破万", "第一", "冠军", "市值", "估值", "融资额"],
    "点子": ["副业", "新职业", "创业", "赛道", "风口", "新玩法", "兼职", "赚钱", "变现",
             "机会", "转型", "红利", "蓝海", "轻创业"],
}

# 每个信号对应的"下一步"引导语（大白话，接到具体话题后面）
SIGNAL_ACTION = {
    "机会": "建议放进观察清单——连续多日仍在榜才是真趋势，单日热度多是情绪，别急着追。",
    "风险": "先别急着抄底或加仓——等情绪宣泄完，再看基本面是否真受损。",
    "对标": "值得拆解它的打法、定价与获客路径，看能否迁移到你自己的副业或内容。",
    "点子": "可用最小成本试水：围绕这个方向做一个内容/产品原型，借热点流量验证真实需求。",
}


# ---------------- 判定函数 ----------------

def _sector_for(text):
    """按命中关键词的长度与数量，返回最匹配的赛道名（或空串）。"""
    best, best_score = "", 0.0
    low = text.lower()
    for kws, name in SECTORS:
        s = 0.0
        for kw in kws:
            if kw.lower() in low:
                s += len(kw) ** 1.2
        if s > best_score:
            best, best_score = name, s
    return best if best_score > 0 else ""


def _signals_for(text):
    """返回命中的信号列表（按强度降序，最多 2 个）。"""
    scored = []
    low = text.lower()
    for name, kws in SIGNAL_KEYWORDS.items():
        s = sum(len(kw) ** 1.2 for kw in kws if kw.lower() in low)
        if s > 0:
            scored.append((s, name))
    scored.sort(key=lambda x: -x[0])
    return [name for _, name in scored[:2]]


def _rel_of(c):
    base = CAT_RELEVANCE.get(c["category"], 0.30)
    text = c["title"] + " " + " ".join(m["title"] for m in c["members"])
    hits = sum(1 for kws, _ in SECTORS if any(k.lower() in text.lower() for k in kws))
    boost = min(0.35, 0.06 * hits)
    return min(1.0, base + boost)


def _reason_for(c, signals, sector):
    t = c["title"]
    loc = f"「{sector}」" if sector else "你的关注方向"
    if signals:
        name = signals[0]
        lead = {
            "机会": f"属于{loc}的增量信号",
            "风险": f"是{loc}的利空/风险信号",
            "对标": f"是{loc}里跑通的案例",
            "点子": f"能转成一个具体行动项",
        }[name]
        return f"{lead}。" + SIGNAL_ACTION[name]
    return f"与{loc}相关，先放进关注清单，观察后续是否发酵出机会或风险。"


# ---------------- 主入口 ----------------

def analyze_focus(clusters):
    """为每个话题补关注度/信号，并生成个人摘要与方向建议。返回 focus 字典。"""
    rows = []
    for c in clusters:
        text = c["title"] + " " + " ".join(m["title"] for m in c["members"])
        rel = _rel_of(c)
        sector = _sector_for(text)
        signals = _signals_for(text)
        # 相关度为主、热度为辅：既不错过冷门但高度相关，也不漏掉高热信号
        focus_score = round(0.65 * rel * 100 + 0.35 * c["score"], 1)
        reason = _reason_for(c, signals, sector)
        c["focus_rel"] = round(rel, 2)
        c["focus_score"] = focus_score
        c["sector"] = sector
        c["focus_signals"] = signals
        c["focus_reason"] = reason
        # 只收录真正相关的：类目相关度达标，或命中了赛道/信号关键词
        if rel >= 0.5 or sector or signals:
            rows.append(c)

    rows.sort(key=lambda x: -x["focus_score"])

    def pick(sig):
        return [c for c in rows if sig in c["focus_signals"]][:8]

    opportunities = pick("机会")
    risks = pick("风险")
    benchmarks = pick("对标")
    ideas = pick("点子")

    # 赛道热度统计（用于方向建议，只统计有信号命中的）
    sector_cnt = Counter(c["sector"] for c in rows if c["sector"] and c["focus_signals"])

    advice = _build_advice(opportunities, risks, benchmarks, ideas, rows)

    return {
        "label": USER_FOCUS["label"],
        "tagline": USER_FOCUS["tagline"],
        "relevant": [{
            "title": c["title"], "score": c["score"], "focus_score": c["focus_score"],
            "category": c["category"], "sector": c["sector"],
            "signals": c["focus_signals"], "reason": c["focus_reason"],
            "platforms": c["platforms"],
        } for c in rows[:15]],
        "opportunities": _to_light(opportunities),
        "risks": _to_light(risks),
        "benchmarks": _to_light(benchmarks),
        "ideas": _to_light(ideas),
        "sector_tally": [{"sector": k, "count": v} for k, v in sector_cnt.most_common(8)],
        "advice": advice,
    }


def _to_light(cs):
    return [{
        "title": c["title"], "score": c["score"], "focus_score": c["focus_score"],
        "category": c["category"], "sector": c["sector"],
        "reason": c["focus_reason"], "platforms": c["platforms"],
    } for c in cs]


def _build_advice(opp, risk, bench, ideas, rows):
    adv = []

    # 1. 机会主线
    if opp:
        opp_sec = Counter(c["sector"] for c in opp if c["sector"])
        top_sector, top_cnt = opp_sec.most_common(1)[0] if opp_sec else ("", 0)
        if top_cnt >= 2:
            matched = [c for c in opp if c["sector"] == top_sector]
            others = [c for c in opp if c["sector"] != top_sector]
            names = "、".join(f"「{c['title']}」" for c in (matched + others)[:3])
            line = f"机会主线：今日与你最相关的机会信号有 {len(opp)} 个，最集中在「{top_sector}」——{names}。"
        else:
            names = "、".join(f"「{c['title']}」" for c in opp[:3])
            line = f"机会主线：今日有 {len(opp)} 个机会信号——{names}。"
        line += "判断是真趋势还是情绪，看两点：一是有没有跨平台共振，二是明后天是否还挂在榜上；单日冲高、次日消失的，别碰。"
        adv.append(line)
    else:
        adv.append("机会主线：今日没有明显的机会信号，宜守不宜攻，把精力放在复盘和储备上。")

    # 2. 风险提示
    if risk:
        names = "、".join(f"「{c['title']}」" for c in risk[:3])
        line = f"风险提示：有 {len(risk)} 条与你相关的风险信号——{names}。"
        line += "若你的持仓或副业踩在这些方向上，先查清楚是情绪面杀跌还是基本面真出问题，再决定去留，别凭一条热搜做交易决策。"
        adv.append(line)
    else:
        adv.append("风险提示：今日没有明显的风险信号，相关方向整体平稳。")

    # 3. 对标借鉴
    if bench:
        c = bench[0]
        sec = f"「{c['sector']}」" if c["sector"] else "个人创业/副业"
        adv.append(f"对标借鉴：{c['title']} 是 {sec} 里值得拆的案例。"
                   f"重点看三点——它解决了什么真实需求、靠什么获客、怎么变现，再对照自己能否复制其中一环。")

    # 4. 落地行动（从点子 + 最强机会各取一条，转成可执行动作）
    actions = []
    for c in ideas[:2]:
        sec = f"「{c['sector']}」" if c["sector"] else "该方向"
        actions.append(f"围绕「{c['title']}」做最小试水：在{sec}输出一期内容或小产品，用当天流量验证有没有真实需求")
    if opp and len(actions) < 3:
        c = opp[0]
        sec = f"「{c['sector']}」" if c["sector"] else "该方向"
        actions.append(f"把「{c['title']}」列入每周观察表，跟踪它是否连续出现——连续出现就是入场信号")
    if actions:
        adv.append("落地行动：" + "；".join(actions) + "。")

    # 5. 方向校准（一句话）
    if rows:
        cat_counter = Counter(c["category"] for c in rows if c["category"] != "其他")
        top_cat = cat_counter.most_common(1)[0][0] if cat_counter else (rows[0]["category"] if rows else "")
        if top_cat:
            adv.append(f"方向校准：今日值得你分配注意力的类目是「{top_cat}」，"
                       f"建议把时间先投在它和相关赛道的研究上，别被娱乐热搜带走节奏。")
    return adv
