# -*- coding: utf-8 -*-
"""归纳总结引擎：热度归一 → 跨平台话题聚类 → 分类打标 → 摘要与洞察生成。"""
import math
import re
from collections import Counter, defaultdict

from config import (CATEGORIES, CATEGORY_PRIORITY, PLATFORMS, PLATFORM_ORDER,
                    STOPWORDS, TAGS, TITLE_PREFIX, TOUTIAO_CAT_MAP)

CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
ASCII_TOKEN = re.compile(r"[a-z][a-z0-9\.\+\-]{1,}")

# 聚类阈值
SIM_MERGE = 0.42          # 常规合并阈值（加权包含度）
SIM_ENTITY = 0.28         # 共享强实体词（如 deepseek/iphone）时的放宽阈值
MIN_SHARED_W = 2.4        # 共享词汇的最小信息量
ENT_MIN_LEN = 4           # 可放宽的实体词最短长度，短词如 nba 太泛，不参与放宽


# ---------------- 标题处理 ----------------

def clean_title(t):
    t = (t or "").replace("\u200b", "").strip()
    for p in TITLE_PREFIX:
        if t.startswith(p):
            t = t[len(p):]
            break
    t = re.sub(r"^[【\[「](.{1,12}?)[】\]」]\s*", r"\1：", t)
    t = re.sub(r"[#*]", "", t)
    t = t.strip(" \"'“”‘’？?。.！!，,、：:；;…~～")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def tokenize(title):
    """返回 (中文 2/3-gram 集合, 英文/数字实体集合)。"""
    low = title.lower()
    grams = set()
    for run in CJK_RUN.findall(low):
        n = len(run)
        for size in (2, 3):
            if n >= size:
                for i in range(n - size + 1):
                    grams.add(run[i:i + size])
    ents = {w for w in ASCII_TOKEN.findall(low) if len(w) >= 3}
    ents |= {f"{a}万" for a in re.findall(r"(\d+\.?\d*)万", low)}
    return grams, ents


def build_idf(docs):
    n = len(docs) or 1
    df = Counter()
    for d in docs:
        for t in d:
            df[t] += 1
    return {t: math.log((n + 1) / (c + 0.5)) for t, c in df.items()}


def weighted_sim(a, b, idf):
    """加权包含度：交集权重 / 较短一侧的权重和，长标题不会被短标题拖低。"""
    if not a or not b:
        return 0.0, 0.0
    inter = a & b
    if not inter:
        return 0.0, 0.0
    wa = sum(idf.get(x, 1.0) for x in a)
    wb = sum(idf.get(x, 1.0) for x in b)
    wi = sum(idf.get(x, 1.0) for x in inter)
    if min(wa, wb) <= 0:
        return 0.0, 0.0
    return wi / min(wa, wb), wi


# ---------------- 打分与分类 ----------------

def score_items(items):
    """为每条热榜计算 0~1 的综合关注度。"""
    by_plat = defaultdict(list)
    for it in items:
        by_plat[it["platform"]].append(it)

    for pid, group in by_plat.items():
        group.sort(key=lambda x: (x.get("rank") or 999))
        n = len(group)
        heats = [g["heat"] for g in group if isinstance(g.get("heat"), (int, float)) and g["heat"] > 0]
        max_heat = max(heats) if heats else None
        for g in group:
            rank = g.get("rank") or (group.index(g) + 1)
            rank_score = 1 - (rank - 1) / max(n - 1, 1)
            if max_heat and isinstance(g.get("heat"), (int, float)) and g["heat"] > 0:
                heat_score = math.log1p(g["heat"]) / math.log1p(max_heat)
            else:
                heat_score = rank_score
            g["rank_score"] = round(rank_score, 4)
            s = 0.5 * rank_score + 0.5 * heat_score
            # 平台置顶位（政宣固定位）不代表真实热度，降权处理
            if g.get("label") == "置顶":
                s *= 0.78
            g["item_score"] = round(s, 4)
    return items


def classify(title, hint=""):
    """关键词加权打分，取最高分类。"""
    best, best_score = "其他", 0.0
    for cat, kws in CATEGORIES:
        s = 0.0
        for kw in kws:
            if kw.lower() in title.lower():
                s += len(kw) ** 1.2
        if s > best_score:
            best, best_score = cat, s
    if best_score == 0 and hint:
        best = TOUTIAO_CAT_MAP.get(hint, "其他")
    return best


def tag_of(title):
    found = []
    for name, kws in TAGS:
        if any(k in title for k in kws):
            found.append(name)
    return found[:2]


# ---------------- 聚类 ----------------

def cluster_items(items):
    """Leader 聚类：按关注度降序，与已有簇代表逐条比较，避免链式误并。"""
    docs = []
    for it in items:
        g, e = tokenize(it["title"])
        docs.append(g | e)
    idf = build_idf(docs)
    for it, d in zip(items, docs):
        it["_tok"] = d

    order = sorted(items, key=lambda x: -x["item_score"])
    clusters = []
    for it in order:
        placed = False
        best_c, best_s = None, 0.0
        for c in clusters:
            rep = c["rep"]
            s, wi = weighted_sim(it["_tok"], rep["_tok"], idf)
            if s < SIM_ENTITY:
                continue
            # 只认长度足够的英文/型号类实体，避免 "nba""巴黎" 这类泛标签误并
            strong = [t for t in (it["_tok"] & rep["_tok"])
                      if len(t) >= ENT_MIN_LEN and ASCII_TOKEN.fullmatch(t)]
            # 极短标题（词元很少）一个共同词就能把相似度顶高，需要更高门槛
            thr = 0.75 if min(len(it["_tok"]), len(rep["_tok"])) <= 4 else SIM_MERGE
            ok = (s >= thr and wi >= MIN_SHARED_W) or (s >= SIM_ENTITY and strong)
            if ok and s > best_s:
                best_c, best_s = c, s
        if best_c:
            best_c["members"].append(it)
            it["sim"] = round(best_s, 3)
        else:
            clusters.append({"rep": it, "members": [it]})

    out = []
    for c in clusters:
        members = c["members"]
        plats = sorted({m["platform"] for m in members},
                       key=lambda p: PLATFORM_ORDER.index(p) if p in PLATFORM_ORDER else 99)
        best = max(m["item_score"] for m in members)
        avg = sum(m["item_score"] for m in members) / len(members)
        plat_w = sum(PLATFORMS[p]["weight"] for p in plats) / len(plats)
        # 共振放大：单平台上限约 90，跨平台越多越接近满分，避免"处处 100 分"
        resonance = 0.90 + 0.06 * (len(plats) - 1)
        score = 100 * (0.62 * best + 0.38 * avg) * plat_w * resonance
        score += min(4.0, 1.2 * (len(members) - 1))
        title = c["rep"]["title"]

        # 分类：按成员关注度投票
        votes = defaultdict(float)
        for m in members:
            votes[classify(m["title"], m.get("category_hint", ""))] += m["item_score"] + 0.1
        cat = max(votes.items(), key=lambda kv: kv[1])[0] if votes else "其他"

        tags = []
        for m in members:
            for t in tag_of(m["title"]):
                if t not in tags:
                    tags.append(t)

        out.append({
            "title": title,
            "score": round(min(score, 99.9), 1),
            "category": cat,
            "tags": tags[:2],
            "platforms": plats,
            "members": [{
                "platform": m["platform"],
                "platform_name": PLATFORMS[m["platform"]]["name"],
                "title": m["title"],
                "rank": m.get("rank"),
                "heat": m.get("heat"),
                "url": m.get("url", ""),
                "label": m.get("label", ""),
            } for m in sorted(members, key=lambda x: PLATFORM_ORDER.index(x["platform"]))],
            "_tokens": set().union(*[m["_tok"] for m in members]),
        })

    out.sort(key=lambda c: -c["score"])
    for it in items:
        it.pop("_tok", None)
    return out


# ---------------- 热词 ----------------

def extract_hotwords(clusters, limit=14):
    cnt = Counter()
    for c in clusters:
        w = 3 if c["score"] >= 70 else 2 if c["score"] >= 45 else 1
        for t in c["_tokens"]:
            if len(t) == 2 and CJK_RUN.fullmatch(t) and t not in STOPWORDS:
                cnt[t] += w
            elif len(t) >= 3 and (ASCII_TOKEN.fullmatch(t) or t.endswith("万")):
                cnt[t] += w
    ranked = sorted(cnt.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    picked = []
    for w, c in ranked:
        if c < 2:
            break
        if any(w in p or p in w for p, _ in picked):
            continue
        picked.append((w, c))
        if len(picked) >= limit:
            break
    return [{"word": w, "count": c} for w, c in picked]


# ---------------- 统计与洞察 ----------------

def build_stats(items, clusters, status):
    cat_cnt = Counter(c["category"] for c in clusters)
    total = len(clusters) or 1
    plats = [p for p in PLATFORM_ORDER if status.get(p, {}).get("ok")]
    cross2 = [c for c in clusters if len(c["platforms"]) >= 2]
    cross3 = [c for c in clusters if len(c["platforms"]) >= 3]

    cat_rows = []
    for cat, n in cat_cnt.most_common():
        cat_rows.append({"category": cat, "count": n, "share": round(n / total * 100, 1)})

    # 各平台分类画像（"其他"不参与，避免出现"某平台以其他类为主"的废话）
    plat_rows = []
    for pid in plats:
        its = [i for i in items if i["platform"] == pid]
        cc = Counter(classify(i["title"], i.get("category_hint", "")) for i in its)
        cc.pop("其他", None)
        top = cc.most_common(3)
        plat_rows.append({
            "id": pid,
            "name": PLATFORMS[pid]["name"],
            "color": PLATFORMS[pid]["color"],
            "desc": PLATFORMS[pid]["desc"],
            "count": len(its),
            "top_cats": [{"category": k, "count": v,
                          "share": round(v / max(len(its), 1) * 100, 1)} for k, v in top],
        })

    tag_cnt = Counter()
    for c in clusters:
        for t in c["tags"]:
            tag_cnt[t] += 1

    return {
        "platforms": plats,
        "platform_count": len(plats),
        "item_count": len(items),
        "cluster_count": len(clusters),
        "cross2_count": len(cross2),
        "cross3_count": len(cross3),
        "categories": cat_rows,
        "platform_rows": plat_rows,
        "tags": [{"tag": k, "count": v} for k, v in tag_cnt.most_common()],
    }


def build_insights(clusters, stats):
    """生成可读洞察句，返回 [(标题, 正文)]。"""
    out = []
    cats = {c["category"]: c for c in stats["categories"]}
    total = stats["cluster_count"] or 1

    # 1. 跨平台共振
    cross = [c for c in clusters if len(c["platforms"]) >= 3][:3]
    if cross:
        parts = []
        for c in cross:
            names = "、".join(PLATFORMS[p]["name"] for p in c["platforms"])
            parts.append(f"「{c['title']}」（{names}，{len(c['platforms'])} 平台）")
        out.append(("跨平台共振", "真正穿透圈层的是：" + "；".join(parts) + "。这类话题不依赖单一平台的算法偏好，具备更强的公共性。"))
    else:
        cross2 = [c for c in clusters if len(c["platforms"]) >= 2][:3]
        if cross2:
            names = "、".join(f"「{c['title']}」" for c in cross2)
            out.append(("跨平台共振", f"今日暂无三平台以上共振话题，双平台重叠集中在 {names}。"))
        else:
            out.append(("跨平台共振", "今日各平台榜单几乎完全分化，没有出现跨平台共振话题，舆论场处于分散状态。"))

    # 2. 平台画像
    overall = {c["category"]: c["share"] for c in stats["categories"]}
    lines = []
    for row in stats["platform_rows"]:
        if not row["top_cats"]:
            continue
        top = row["top_cats"][0]
        base = overall.get(top["category"], 0)
        delta = top["share"] - base
        trend = f"高出整体 {delta:.0f} 个百分点" if delta >= 5 else (
            f"与整体持平" if abs(delta) < 5 else f"低于整体 {abs(delta):.0f} 个百分点")
        lines.append(f"{row['name']}以{top['category']}为主（{top['share']:.0f}%，{trend}）")
    if lines:
        out.append(("平台差异", "；".join(lines) + "。同一事件在不同平台的排序差异，本质是用户结构与推荐逻辑的差异。"))

    # 3. 议题性质
    tg = {t["tag"]: t["count"] for t in stats["tags"]}
    halves = []
    if tg.get("官方回应"):
        halves.append(f"「官方回应/通报」类 {tg['官方回应']} 个")
    if tg.get("突发事件"):
        halves.append(f"「突发事件」{tg['突发事件']} 个")
    if tg.get("争议讨论"):
        halves.append(f"「争议讨论」{tg['争议讨论']} 个")
    if tg.get("政策新规"):
        halves.append(f"「政策新规」{tg['政策新规']} 个")
    if halves:
        out.append(("议题性质", "从性质上看，" + "、".join(halves) + "。"
                    + ("突发与回应类占比偏高，说明今日舆论场以「事件驱动」为主。" if tg.get("突发事件", 0) + tg.get("官方回应", 0) > total * 0.12
                       else "整体以日常议题为主，缺乏强冲突性事件。")))

    # 4. 头部集中度
    top5 = sum(c["score"] for c in clusters[:5]) / max(sum(c["score"] for c in clusters) or 1, 1)
    out.append(("注意力结构", f"前 5 个话题占据全部关注度的 {top5 * 100:.0f}%，"
                + ("注意力高度集中，少数事件形成了压倒性声量。" if top5 > 0.22
                   else "注意力相对分散，没有出现单一议题垄断舆论的情况。")))
    return out


def build_summary(clusters, stats):
    """生成 3~4 段可直接发布的中文综述。"""
    if not clusters:
        return ["本次未采集到有效热榜数据，请检查网络或数据源状态。"]

    plats = stats["platforms"]
    n_plat, n_item, n_clu = len(plats), stats["item_count"], stats["cluster_count"]
    cat_rows = stats["categories"]
    paras = []

    # 第一段：规模 + 结构
    p = (f"本次覆盖 {'、'.join(PLATFORMS[x]['name'] for x in plats)} {n_plat} 个平台，"
         f"共采集 {n_item} 条热榜条目，去重聚合后得到 {n_clu} 个独立话题，"
         f"其中 {stats['cross2_count']} 个话题在 2 个及以上平台同时上榜"
         f"（{stats['cross3_count']} 个达到 3 平台以上）。")
    if cat_rows:
        named = [c for c in cat_rows if c["category"] != "其他"] or cat_rows
        top = named[:3]
        p += f"议题结构上，{top[0]['category']}类以 {top[0]['count']} 个话题、{top[0]['share']}% 的占比居首"
        if len(top) > 1:
            p += "，其后是" + "、".join(f"{t['category']}（{t['share']}%）" for t in top[1:])
        p += "。"
    paras.append(p)

    # 第二段：头部事件
    top3 = clusters[:3]
    seg = []
    for i, c in enumerate(top3, 1):
        names = "、".join(PLATFORMS[x]["name"] for x in c["platforms"])
        best_ranks = sorted(c["members"], key=lambda x: x["rank"] or 999)
        seen_p, picked = set(), []
        for m in best_ranks:
            if m["platform"] in seen_p:
                continue
            seen_p.add(m["platform"])
            picked.append(m)
            if len(picked) == 2:
                break
        ranks = "，".join(f"{PLATFORMS[m['platform']]['name']}第{m['rank']}位" for m in picked)
        where = ranks if len(c["platforms"]) == 1 else f"见于{names}：{ranks}"
        seg.append(f"{'①②③'[i - 1]}「{c['title']}」（{c['category']}，综合热度 {c['score']:.0f}，{where}）")
    paras.append("今日关注度最高的三件事是：" + "；".join(seg) + "。")

    # 第三段：跨平台与性质
    cross = [c for c in clusters if len(c["platforms"]) >= 3]
    tg = {t["tag"]: t["count"] for t in stats["tags"]}
    p3 = ""
    if cross:
        p3 += (f"跨平台共振最明显的是「{cross[0]['title']}」，"
               f"同时出现在 {'、'.join(PLATFORMS[x]['name'] for x in cross[0]['platforms'])} "
               f"{len(cross[0]['platforms'])} 个平台。")
    if tg:
        top_tags = sorted(tg.items(), key=lambda kv: -kv[1])[:2]
        p3 += "事件性质上，" + "、".join(f"「{k}」{v} 个" for k, v in top_tags) + "最为集中。"
    if p3:
        paras.append(p3)

    # 第四段：平台差异（取差异最大的一个）
    overall = {c["category"]: c["share"] for c in cat_rows}
    best_delta, best_txt = 0, ""
    for row in stats["platform_rows"]:
        if not row["top_cats"]:
            continue
        t = row["top_cats"][0]
        d = t["share"] - overall.get(t["category"], 0)
        if d > best_delta:
            best_delta = d
            best_txt = (f"{row['name']}的{t['category']}内容占比达 {t['share']:.0f}%，"
                        f"比整体水平高 {d:.0f} 个百分点")
    if best_txt:
        paras.append(best_txt + "，平台间的榜单差异正是各平台用户结构差异的直接体现。")
    return paras


def analyze(items, status):
    score_items(items)
    clusters = cluster_items(items)
    stats = build_stats(items, clusters, status)
    hotwords = extract_hotwords(clusters)
    insights = build_insights(clusters, stats)
    summary = build_summary(clusters, stats)
    for c in clusters:
        c.pop("_tokens", None)

    # 归因：为什么火（大白话）
    import explainer
    category_analysis = explainer.explain(clusters, stats)

    return {
        "stats": stats,
        "clusters": clusters,
        "hotwords": hotwords,
        "insights": [{"title": t, "text": x} for t, x in insights],
        "summary": summary,
        "category_analysis": category_analysis,
    }
