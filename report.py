# -*- coding: utf-8 -*-
"""报告渲染：单文件 HTML 日报 + Markdown 摘要。"""
import html
import os

from config import PLATFORMS, PLATFORM_ORDER

CAT_COLORS = {
    "时政": "#b4342a", "国际": "#8a5a2b", "军事": "#6b5b3e", "财经": "#c2551f",
    "科技": "#1f6fb2", "体育": "#1f8a5b", "健康": "#2b8a7a", "教育": "#4a6fa5",
    "汽车": "#3f5f8f", "游戏": "#7a4fa3", "娱乐": "#c03a6b", "社会": "#4b5563",
    "生活": "#8a7b3e", "其他": "#8b929c",
}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f3f5f7; --card:#fff; --ink:#17212b; --sub:#6b7684; --line:#e4e9ef;
  --hot:#e04a35; --blue:#2563eb; --radius:14px;
}
html{-webkit-text-size-adjust:100%}
body{
  background:var(--bg); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB",
    "Microsoft YaHei",sans-serif;
  font-size:15px; line-height:1.72; padding:40px 20px 60px;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1080px;margin:0 auto}
a{color:inherit;text-decoration:none}

/* ---------- header ---------- */
header{padding:0 4px 26px;border-bottom:2px solid var(--ink);margin-bottom:30px}
.eyebrow{font-size:11px;letter-spacing:.22em;color:var(--hot);font-weight:700;margin-bottom:10px}
h1{font-size:40px;line-height:1.15;letter-spacing:-.02em;font-weight:800}
.h1-sub{font-size:40px;font-weight:300;letter-spacing:-.02em;color:var(--sub)}
.meta{margin-top:14px;font-size:13px;color:var(--sub);display:flex;flex-wrap:wrap;gap:6px 16px}
.meta b{color:var(--ink);font-weight:600}

/* ---------- section ---------- */
section{margin-bottom:38px}
h2{font-size:13px;letter-spacing:.14em;font-weight:700;color:var(--sub);
   text-transform:uppercase;margin-bottom:14px;display:flex;align-items:center;gap:10px}
h2::after{content:"";flex:1;height:1px;background:var(--line)}
h2 .idx{color:var(--hot);font-variant-numeric:tabular-nums}

/* ---------- summary ---------- */
.summary{background:var(--card);border-radius:var(--radius);padding:26px 30px 24px;
  box-shadow:0 1px 2px rgba(20,30,45,.05),0 8px 24px -18px rgba(20,30,45,.35);
  border-left:3px solid var(--hot)}
.summary .lead{font-size:17px;line-height:1.85;margin-bottom:12px}
.summary .lead:last-child{margin-bottom:0}
.summary p{color:#25313d}

/* ---------- kpi ---------- */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:14px}
.kpi{background:var(--card);border-radius:var(--radius);padding:18px 18px 16px;
  box-shadow:0 1px 2px rgba(20,30,45,.05)}
.kpi .n{font-size:30px;font-weight:800;line-height:1.1;font-variant-numeric:tabular-nums;
  letter-spacing:-.02em}
.kpi .n small{font-size:13px;font-weight:600;color:var(--sub);margin-left:2px}
.kpi .l{font-size:12px;color:var(--sub);margin-top:4px}

/* ---------- category bars ---------- */
.cat-wrap{background:var(--card);border-radius:var(--radius);padding:22px 24px;
  box-shadow:0 1px 2px rgba(20,30,45,.05)}
.cat{display:grid;grid-template-columns:64px 1fr 74px;align-items:center;gap:12px;
  margin-bottom:9px;font-size:13px}
.cat:last-child{margin-bottom:0}
.cat .name{font-weight:600;white-space:nowrap}
.cat .track{height:9px;background:#eef1f5;border-radius:5px;overflow:hidden}
.cat .fill{height:100%;border-radius:5px}
.cat .val{text-align:right;color:var(--sub);font-variant-numeric:tabular-nums;font-size:12px}

/* ---------- cluster cards ---------- */
.clusters{display:flex;flex-direction:column;gap:10px}
.cl{background:var(--card);border-radius:var(--radius);padding:18px 22px 16px;
  box-shadow:0 1px 2px rgba(20,30,45,.05);position:relative;overflow:hidden;
  border-top:1px solid transparent}
.cl:hover{border-top-color:var(--line)}
.cl-head{display:flex;gap:14px;align-items:flex-start}
.rank{font-size:13px;font-weight:800;color:#c3cbd4;font-variant-numeric:tabular-nums;
  min-width:26px;padding-top:3px}
.rank.top{color:var(--hot)}
.cl-main{flex:1;min-width:0}
.cl-title{font-size:16.5px;font-weight:700;line-height:1.45;letter-spacing:-.01em}
.cl-title a:hover{color:var(--hot)}
.cl-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px;align-items:center}
.chip{font-size:11.5px;padding:2px 8px;border-radius:20px;background:#f1f4f8;
  color:#4a5563;white-space:nowrap;line-height:1.7}
.chip.cat{color:#fff;font-weight:600}
.chip.tag{background:#fdf1ee;color:#b4402c}
.chip.new{background:#eaf1fd;color:#2563eb}
.chip.cont{background:#f1f4f8;color:#7b8794}
.plat{display:inline-flex;align-items:center;gap:4px;font-size:11.5px;color:#4a5563;
  background:#f1f4f8;padding:2px 8px 2px 6px;border-radius:20px}
.dot{width:6px;height:6px;border-radius:50%;flex:none}
.score{min-width:64px;text-align:right;font-variant-numeric:tabular-nums}
.score b{font-size:19px;font-weight:800;letter-spacing:-.02em}
.score span{display:block;font-size:10.5px;color:var(--sub);letter-spacing:.04em}
.bar{height:3px;background:#eef1f5;border-radius:2px;margin-top:12px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--hot);border-radius:2px}
.members{margin-top:10px;display:flex;flex-direction:column;gap:3px}
.member{font-size:12.5px;color:var(--sub);display:flex;gap:8px;align-items:baseline}
.member .p{flex:none;width:44px;color:#8b929c}
.member .t{color:#3d4a58;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.member .r{flex:none;color:#a9b2bd;font-variant-numeric:tabular-nums}
.why{margin-top:12px;font-size:13px;color:#4a5563;line-height:1.75;background:#fafbfc;
  border:1px solid #f0f3f7;border-radius:10px;padding:10px 13px}
.why b{color:#b4402c;font-weight:700;margin-right:6px}

/* ---------- words ---------- */
.words{display:flex;flex-wrap:wrap;gap:8px;background:var(--card);border-radius:var(--radius);
  padding:20px 22px;box-shadow:0 1px 2px rgba(20,30,45,.05)}
.word{border-radius:8px;padding:5px 11px;background:#f1f4f8;color:#33404e;
  font-size:13px;display:inline-flex;align-items:baseline;gap:5px}
.word i{font-style:normal;font-size:10.5px;color:#9aa4b0}
.word.big{background:#fdece8;color:#a83a26;font-weight:700;font-size:15px}
.word.mid{background:#f6f0ea;color:#7a5327;font-weight:600}

/* ---------- platform cards ---------- */
.plats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.pcard{background:var(--card);border-radius:var(--radius);padding:18px 20px;
  box-shadow:0 1px 2px rgba(20,30,45,.05)}
.pcard .ph{display:flex;align-items:center;gap:8px;margin-bottom:4px}
.pcard .pn{font-weight:700;font-size:15px}
.pcard .pc{font-size:11.5px;color:#a9b2bd;margin-left:auto;font-variant-numeric:tabular-nums}
.pcard .pd{font-size:12px;color:var(--sub);line-height:1.6;margin-bottom:12px;min-height:38px}
.mini{display:flex;align-items:center;gap:8px;font-size:11.5px;margin-bottom:6px}
.mini .mn{width:34px;color:#4a5563;flex:none}
.mini .mt{flex:1;height:6px;background:#eef1f5;border-radius:3px;overflow:hidden}
.mini .mt i{display:block;height:100%;border-radius:3px}
.mini .mv{width:32px;text-align:right;color:#9aa4b0;font-variant-numeric:tabular-nums}

/* ---------- insights ---------- */
.insights{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.ins{background:var(--card);border-radius:var(--radius);padding:18px 20px;
  box-shadow:0 1px 2px rgba(20,30,45,.05)}
.ins h3{font-size:12px;letter-spacing:.08em;color:var(--hot);margin-bottom:7px;font-weight:700}
.ins p{font-size:13.5px;color:#3d4a58;line-height:1.75}

/* ---------- category why ---------- */
.catwhy{display:flex;flex-direction:column;gap:8px}
.cwhy{background:var(--card);border-radius:var(--radius);padding:15px 18px;
  box-shadow:0 1px 2px rgba(20,30,45,.05);display:flex;gap:16px;align-items:flex-start}
.cwhy .cn{flex:none;font-weight:700;font-size:14px;min-width:56px;padding-top:1px}
.cwhy .cn i{font-style:normal;display:block;font-weight:600;color:#9aa4b0;font-size:11px}
.cwhy .ct{flex:1;font-size:13.5px;color:#3d4a58;line-height:1.75}
.cwhy .ct .sp{display:block;margin-top:4px;color:#9aa4b0;font-size:12px}
.cwhy .ct .sp::before{content:"代表：";opacity:.7}

/* ---------- tabs & tables ---------- */
.tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.tab{border:1px solid var(--line);background:var(--card);color:#54606e;font-size:13px;
  padding:7px 15px;border-radius:20px;cursor:pointer;font-family:inherit;
  transition:all .15s;display:inline-flex;align-items:center;gap:6px}
.tab:hover{border-color:#c9d2dc}
.tab.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.tab .c{font-size:10.5px;opacity:.6;font-variant-numeric:tabular-nums}
.panel{display:none;background:var(--card);border-radius:var(--radius);overflow:hidden;
  box-shadow:0 1px 2px rgba(20,30,45,.05)}
.panel.on{display:block}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:left;font-size:11px;letter-spacing:.1em;color:#9aa4b0;font-weight:700;
  padding:12px 16px 8px;border-bottom:1px solid var(--line);text-transform:uppercase}
td{padding:9px 16px;border-bottom:1px solid #f1f4f8;vertical-align:baseline}
tr:last-child td{border-bottom:none}
td.rk{color:#b8c1cc;font-variant-numeric:tabular-nums;width:38px;font-size:12px}
td.tt a:hover{color:var(--hot)}
td.ht{text-align:right;color:#8b929c;font-variant-numeric:tabular-nums;width:86px;font-size:12px}
td.tg{width:52px;text-align:right}
.lab{font-size:10.5px;padding:1px 6px;border-radius:4px;background:#fdece8;color:#b4402c;
  font-weight:600;white-space:nowrap}
.lab.n{background:#eaf1fd;color:#2563eb}
.lab.g{background:#eef3ee;color:#4a6b52}

/* ---------- focus (对你有什么用) ---------- */
.focus-sec{background:linear-gradient(180deg,#fffdf4,#fff);border:1px solid #f0e6c8;
  border-radius:var(--radius);padding:22px 24px 20px;box-shadow:0 1px 2px rgba(20,30,45,.05)}
.focus-tagline{font-size:12.5px;color:#a8822f;margin:-6px 0 16px;font-weight:600}
.advice{background:#fbf7ea;border:1px solid #f0e6c8;border-left:3px solid #c9a227;
  border-radius:10px;padding:15px 18px;margin-bottom:16px}
.advice p{font-size:13.5px;color:#4a4028;line-height:1.82;margin-bottom:8px}
.advice p:last-child{margin-bottom:0}
.signal-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:18px}
.sig-card{border-radius:12px;padding:14px 16px;border:1px solid #eee}
.sig-card h3{font-size:13px;font-weight:700;margin-bottom:8px;display:flex;align-items:center;gap:8px}
.sig-card h3 i{font-style:normal;font-size:11px;background:#fff;border-radius:20px;
  padding:0 8px;font-weight:700;font-variant-numeric:tabular-nums}
.sig-card .si{font-size:12.5px;color:#3d4a58;line-height:1.5;margin-bottom:9px}
.sig-card .si:last-child{margin-bottom:0}
.sig-card .si .st{font-weight:700}
.sig-card .si .sc{display:block;font-size:11.5px;color:#9aa4b0;margin-top:2px}
.sig-card .si .sec{font-size:11px;color:#9a7416;background:rgba(255,255,255,.7);
  padding:1px 7px;border-radius:20px;font-weight:600}
.sig-card .empty{font-size:12px;color:#a9b2bd}
.sig-card.opp{background:#fdf1ee;border-color:#f6d8d2}
.sig-card.opp h3{color:#b4402c}
.sig-card.risk{background:#eef6f0;border-color:#d3e6da}
.sig-card.risk h3{color:#2f7d55}
.sig-card.bench{background:#eef3fd;border-color:#d6e2f7}
.sig-card.bench h3{color:#2563eb}
.sig-card.idea{background:#fbf6ea;border-color:#efe0bd}
.sig-card.idea h3{color:#9a7416}
.fr-title{font-size:12px;letter-spacing:.08em;color:#a8822f;font-weight:700;margin:0 0 8px}
.focus-rank{display:flex;flex-direction:column;gap:5px}
.fr{display:flex;gap:10px;align-items:center;font-size:13px;padding:7px 10px;border-radius:8px}
.fr:hover{background:#faf6ec}
.fr .n{flex:none;width:22px;color:#c9a227;font-weight:800;font-variant-numeric:tabular-nums}
.fr .t{flex:1;font-weight:600;color:#33404e;min-width:0;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.fr .sig{flex:none;font-size:11px;color:#b4402c}
.fr .sec{flex:none;font-size:11px;color:#9a7416;background:#fbf6ea;padding:1px 7px;border-radius:20px}
.fr .fs{flex:none;color:#a9b2bd;font-variant-numeric:tabular-nums;font-size:12px}
.fr .fs b{color:#8a6d1a;font-weight:700}

/* ---------- footer ---------- */
footer{margin-top:46px;padding-top:22px;border-top:1px solid var(--line);
  font-size:12px;color:#9aa4b0;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}
footer b{color:#6b7684;font-weight:600}

@media(max-width:860px){
  body{padding:24px 14px 40px}
  h1,.h1-sub{font-size:30px}
  .kpis{grid-template-columns:repeat(2,1fr)}
  .plats{grid-template-columns:1fr}
  .insights{grid-template-columns:1fr}
  .signal-grid{grid-template-columns:1fr}
  .summary{padding:20px 22px}
}
@media print{
  body{background:#fff;padding:0}
  .cl,.kpi,.cat-wrap,.summary,.pcard,.ins,.panel,.words{box-shadow:none;border:1px solid var(--line)}
  .tabs{display:none}.panel{display:block!important;page-break-inside:avoid}
}
"""

TAB_JS = """
document.querySelectorAll('.tab').forEach(function(t){
  t.addEventListener('click',function(){
    var k=t.dataset.k;
    document.querySelectorAll('.tab').forEach(function(x){x.classList.toggle('on',x===t)});
    document.querySelectorAll('.panel').forEach(function(p){
      p.classList.toggle('on',p.dataset.k===k)});
  });
});
"""


def esc(s):
    return html.escape(str(s or ""), quote=True)


def fmt_heat(h):
    if h is None:
        return "—"
    try:
        h = float(h)
    except (TypeError, ValueError):
        return "—"
    if h >= 1e8:
        return f"{h / 1e8:.2f}亿"
    if h >= 1e4:
        return f"{h / 1e4:.1f}万"
    return f"{int(h)}"


def cat_color(c):
    return CAT_COLORS.get(c, CAT_COLORS["其他"])


def _label_class(label):
    if label in ("爆", "沸", "热"):
        return "lab"
    if label in ("新", "荐"):
        return "lab g"
    return "lab n"


def render(payload, out_dir, top=12, prev=None):
    st = payload["stats"]
    clusters = payload["clusters"]
    day = payload["date"]
    plats = st["platforms"]
    total = st["cluster_count"] or 1

    # --- 分类分布 ---
    cat_html = []
    max_cnt = max((c["count"] for c in st["categories"]), default=1)
    for c in st["categories"][:10]:
        w = c["count"] / max_cnt * 100
        cat_html.append(
            f'<div class="cat"><div class="name">{esc(c["category"])}</div>'
            f'<div class="track"><i class="fill" style="width:{w:.1f}%;'
            f'background:{cat_color(c["category"])}"></i></div>'
            f'<div class="val">{c["count"]} · {c["share"]}%</div></div>')

    # --- 核心话题卡片 ---
    prev_titles = set()
    if prev:
        for pc in prev.get("clusters", []):
            for pm in pc.get("members", []):
                prev_titles.add(str(pm.get("title", "")).strip())

    cl_html = []
    for i, c in enumerate(clusters[:top], 1):
        badges = "".join(
            f'<span class="plat"><i class="dot" style="background:{PLATFORMS[p]["color"]}"></i>'
            f'{PLATFORMS[p]["name"]}</span>' for p in c["platforms"])
        tags = "".join(f'<span class="chip tag">{esc(t)}</span>' for t in c["tags"])
        trend = ""
        if prev_titles:
            hit = any(str(m["title"]).strip() in prev_titles for m in c["members"])
            trend = ('<span class="chip cont">延续昨日</span>' if hit
                     else '<span class="chip new">今日新晋</span>')
        members = ""
        if len(c["members"]) > 1:
            rows = []
            for m in c["members"][:4]:
                rows.append(
                    f'<div class="member"><span class="p">{esc(m["platform_name"])}</span>'
                    f'<span class="t">{esc(m["title"])}</span>'
                    f'<span class="r">#{m["rank"]}</span></div>')
            members = f'<div class="members">{"".join(rows)}</div>'
        link = c["members"][0]["url"] if c["members"] else ""
        title = esc(c["title"])
        if link:
            title = f'<a href="{esc(link)}" target="_blank" rel="noopener">{title}</a>'
        rk_cls = "rank top" if i <= 3 else "rank"
        cl_html.append(f"""
      <article class="cl">
        <div class="cl-head">
          <div class="{rk_cls}">{i:02d}</div>
          <div class="cl-main">
            <div class="cl-title">{title}</div>
            <div class="cl-meta">
              <span class="chip cat" style="background:{cat_color(c['category'])}">{esc(c['category'])}</span>
              {trend}{badges}{tags}
            </div>
            {members}
            {f'<div class="why"><b>为什么火</b>{esc(c["reason"])}</div>' if c.get("reason") else ""}
            <div class="bar"><i style="width:{c['score']:.1f}%"></i></div>
          </div>
          <div class="score"><b>{c['score']:.0f}</b><span>热度</span></div>
        </div>
      </article>""")

    # --- 热词 ---
    words = []
    if payload.get("hotwords"):
        mx = max(w["count"] for w in payload["hotwords"])
        for w in payload["hotwords"]:
            r = w["count"] / mx
            cls = "word big" if r > 0.82 else ("word mid" if r > 0.55 else "word")
            words.append(f'<span class="{cls}">{esc(w["word"])}<i>{w["count"]}</i></span>')

    # --- 平台卡片 ---
    pcard = []
    for row in st["platform_rows"]:
        minis = "".join(
            f'<div class="mini"><span class="mn">{esc(t["category"])}</span>'
            f'<span class="mt"><i style="width:{t["share"]:.0f}%;background:{cat_color(t["category"])}"></i></span>'
            f'<span class="mv">{t["share"]:.0f}%</span></div>' for t in row["top_cats"])
        pcard.append(f"""
      <div class="pcard">
        <div class="ph"><i class="dot" style="background:{row['color']};width:8px;height:8px"></i>
          <span class="pn">{esc(row['name'])}</span>
          <span class="pc">{row['count']} 条</span></div>
        <div class="pd">{esc(row['desc'])}</div>
        {minis}
      </div>""")

    # --- 洞察 ---
    ins = "".join(f'<div class="ins"><h3>{esc(x["title"])}</h3><p>{esc(x["text"])}</p></div>'
                  for x in payload.get("insights", []))

    # --- 类目归因（为什么火） ---
    catwhy = ""
    ca = payload.get("category_analysis", [])
    if ca:
        rows = []
        for a in ca:
            if a["share"] < 3:
                continue
            sp = f'<span class="sp">{esc(a["sample"])}</span>' if a["sample"] else ""
            rows.append(
                f'<div class="cwhy"><div class="cn">{esc(a["category"])}'
                f'<i>{a["count"]} 个 · {a["share"]}%</i></div>'
                f'<div class="ct">{esc(a["reason"])}{sp}</div></div>')
        catwhy = f'<section><h2><span class="idx">06</span> 为什么火 · 大白话解读</h2>'
        catwhy += f'<div class="catwhy">{"".join(rows)}</div></section>'

    # --- 对你有什么用（个性化：投资/副业视角） ---
    focus_html = ""
    fc = payload.get("focus")
    if fc:
        advice = "".join(f'<p>{esc(p)}</p>' for p in fc.get("advice", []))

        def sig_card(cls, title, items):
            if not items:
                return (f'<div class="sig-card {cls}"><h3>{title}<i>0</i></h3>'
                        f'<div class="empty">今日暂无</div></div>')
            body = ""
            for it in items:
                sec = f'<span class="sec">{esc(it["sector"])}</span>' if it.get("sector") else ""
                body += (f'<div class="si"><span class="st">{esc(it["title"])}</span> {sec}'
                         f'<span class="sc">{esc(it["reason"])}</span></div>')
            return f'<div class="sig-card {cls}"><h3>{title}<i>{len(items)}</i></h3>{body}</div>'

        opp_c = sig_card("opp", "机会信号", fc.get("opportunities", []))
        risk_c = sig_card("risk", "风险预警", fc.get("risks", []))
        bench_c = sig_card("bench", "对标案例", fc.get("benchmarks", []))
        idea_c = sig_card("idea", "可落地点子", fc.get("ideas", []))

        rank_rows = []
        for i, it in enumerate(fc.get("relevant", []), 1):
            sig = "、".join(it.get("signals", []))
            sec = f'<span class="sec">{esc(it["sector"])}</span>' if it.get("sector") else ""
            sigs = f'<span class="sig">{esc(sig)}</span>' if sig else ""
            rank_rows.append(
                f'<div class="fr"><span class="n">{i:02d}</span>'
                f'<span class="t">{esc(it["title"])}</span>{sec}{sigs}'
                f'<span class="fs">相关度 <b>{it["focus_score"]:.0f}</b></span></div>')

        focus_html = f'''
  <section class="focus-sec">
    <h2><span class="idx">07</span> 对你有什么用 · {esc(fc["label"])}</h2>
    <div class="focus-tagline">{esc(fc.get("tagline", ""))}</div>
    <div class="advice">{advice}</div>
    <div class="signal-grid">{opp_c}{risk_c}{bench_c}{idea_c}</div>
    <div class="fr-title">个人关注榜 · 按相关度排序</div>
    <div class="focus-rank">{''.join(rank_rows)}</div>
  </section>'''

    # --- 全量榜单 tabs ---
    tabs, panels = [], []
    for idx, pid in enumerate(plats):
        its = sorted([i for i in payload["items"] if i["platform"] == pid], key=lambda x: x["rank"])
        on = " on" if idx == 0 else ""
        tabs.append(f'<button class="tab{on}" data-k="{pid}">{PLATFORMS[pid]["name"]}'
                    f'<span class="c">{len(its)}</span></button>')
        rows = []
        for it in its[:30]:
            lab = (f'<span class="{_label_class(it["label"])}">{esc(it["label"])}</span>'
                   if it.get("label") else "")
            url = it.get("url") or "https://www.baidu.com/s?wd=" + html.escape(it["title"])
            rows.append(
                f'<tr><td class="rk">{it["rank"]}</td>'
                f'<td class="tt"><a href="{esc(url)}" target="_blank" rel="noopener">'
                f'{esc(it["title"])}</a></td>'
                f'<td class="ht">{fmt_heat(it.get("heat"))}</td>'
                f'<td class="tg">{lab}</td></tr>')
        more = (f'<div style="padding:10px 16px;font-size:11.5px;color:#a9b2bd">'
                f'共 {len(its)} 条，此处显示前 30 条</div>') if len(its) > 30 else ""
        panels.append(f'<div class="panel{on}" data-k="{pid}">'
                      f'<table><thead><tr><th>#</th><th>标题</th><th style="text-align:right">热度</th>'
                      f'<th></th></tr></thead><tbody>{"".join(rows)}</tbody></table>{more}</div>')

    summary = "".join(f'<p class="lead">{esc(p)}</p>' for p in payload.get("summary", []))

    # 失败源提示
    failed = [PLATFORMS[p]["name"] for p in PLATFORM_ORDER
              if payload.get("status", {}).get(p, {}).get("ok") is False]
    fail_note = (f'<span style="color:#b4402c">未采集成功：{"、".join(failed)}</span>'
                 if failed else "")

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(day)} 网络热点日报</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="eyebrow">DAILY HOTSPOT DIGEST</div>
    <h1>{esc(day)} <span class="h1-sub">网络热点日报</span></h1>
    <div class="meta">
      <span>采集于 <b>{esc(payload.get('collected_at', ''))}</b></span>
      <span>覆盖 <b>{st['platform_count']}</b> 个平台</span>
      <span>聚合 <b>{st['cluster_count']}</b> 个话题</span>
      {fail_note}
    </div>
  </header>

  <section>
    <div class="summary">{summary}</div>
    <div class="kpis">
      <div class="kpi"><div class="n">{st['item_count']}</div><div class="l">热榜条目</div></div>
      <div class="kpi"><div class="n">{st['cluster_count']}</div><div class="l">去重话题</div></div>
      <div class="kpi"><div class="n">{st['cross2_count']}<small>个</small></div><div class="l">跨平台共振</div></div>
      <div class="kpi"><div class="n">{st['cross3_count']}<small>个</small></div><div class="l">三平台以上</div></div>
    </div>
  </section>

  <section>
    <h2><span class="idx">01</span> 议题结构</h2>
    <div class="cat-wrap">{''.join(cat_html)}</div>
  </section>

  <section>
    <h2><span class="idx">02</span> 核心话题 Top {min(top, len(clusters))}</h2>
    <div class="clusters">{''.join(cl_html)}</div>
  </section>

  <section>
    <h2><span class="idx">03</span> 高频热词</h2>
    <div class="words">{''.join(words)}</div>
  </section>

  <section>
    <h2><span class="idx">04</span> 平台视角</h2>
    <div class="plats">{''.join(pcard)}</div>
  </section>

  <section>
    <h2><span class="idx">05</span> 观察与判断</h2>
    <div class="insights">{ins}</div>
  </section>

  {catwhy}

  {focus_html}

  <section>
    <h2><span class="idx">08</span> 全量榜单</h2>
    <div class="tabs">{''.join(tabs)}</div>
    {''.join(panels)}
  </section>

  <footer>
    <span>数据来源：{'、'.join(PLATFORMS[p]['name'] for p in plats)} 公开热榜接口</span>
    <span>生成时间 <b>{esc(payload.get('collected_at', ''))}</b> · WorkBuddy 热点工具</span>
  </footer>
</div>
<script>{TAB_JS}</script>
</body>
</html>"""

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{day}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path


def render_index(data_dir, out_dir):
    """生成历史日报索引页。"""
    import json
    rows = []
    if os.path.isdir(data_dir):
        for fn in sorted((f for f in os.listdir(data_dir) if f.endswith(".json")), reverse=True):
            try:
                with open(os.path.join(data_dir, fn), encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            st = d.get("stats", {})
            top = (d.get("clusters") or [{}])[0]
            cats = "、".join(c["category"] for c in (st.get("categories") or [])[:3])
            rows.append(
                f'<a class="row" href="{esc(fn[:-5])}.html">'
                f'<div class="d">{esc(fn[:-5])}</div>'
                f'<div class="c">'
                f'<div class="t">{esc(top.get("title", ""))}</div>'
                f'<div class="m">{st.get("item_count", 0)} 条 · {st.get("cluster_count", 0)} 话题 · '
                f'跨平台 {st.get("cross2_count", 0)} 个 · 主类目 {esc(cats)}</div>'
                f'</div><div class="arrow">→</div></a>')
    if not rows:
        rows.append('<div style="padding:30px;color:#8b929c">暂无历史日报，先跑一次采集。</div>')

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>网络热点日报 · 历史</title>
<style>{CSS}
.idx-row{{display:flex;flex-direction:column;gap:10px}}
.row{{display:flex;gap:18px;align-items:center;background:var(--card);border-radius:var(--radius);
  padding:18px 22px;box-shadow:0 1px 2px rgba(20,30,45,.05);transition:transform .15s}}
.row:hover{{transform:translateX(3px)}}
.row .d{{font-size:15px;font-weight:800;font-variant-numeric:tabular-nums;flex:none;width:112px;
  color:var(--ink)}}
.row .c{{flex:1;min-width:0}}
.row .t{{font-size:15px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.row .m{{font-size:12px;color:var(--sub);margin-top:3px}}
.row .arrow{{color:#c3cbd4;font-size:18px}}
</style></head><body><div class="wrap">
<header><div class="eyebrow">DAILY HOTSPOT DIGEST</div>
<h1>网络热点日报 <span class="h1-sub">历史归档</span></h1>
<div class="meta"><span>共 <b>{len(rows)}</b> 期</span></div></header>
<section><div class="idx-row">{''.join(rows)}</div></section>
<footer><span>点击任意一期查看当日完整报告</span><span>WorkBuddy 热点工具</span></footer>
</div></body></html>"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path


def render_markdown(payload, out_dir, top=12):
    st = payload["stats"]
    clusters = payload["clusters"]
    day = payload["date"]
    L = [f"# {day} 网络热点日报", "",
         f"> 采集时间 {payload.get('collected_at', '')} ｜ 覆盖 {st['platform_count']} 个平台 ｜ "
         f"{st['item_count']} 条热榜 ｜ 聚合 {st['cluster_count']} 个话题", ""]

    L.append("## 一、今日综述")
    L.append("")
    for p in payload.get("summary", []):
        L.append(p)
        L.append("")

    L.append("## 二、议题结构")
    L.append("")
    L.append("| 类别 | 话题数 | 占比 |")
    L.append("| --- | ---: | ---: |")
    for c in st["categories"]:
        L.append(f"| {c['category']} | {c['count']} | {c['share']}% |")
    L.append("")

    L.append(f"## 三、核心话题 Top {min(top, len(clusters))}")
    L.append("")
    for i, c in enumerate(clusters[:top], 1):
        plats = "、".join(f"{PLATFORMS[p]['name']}第{[m for m in c['members'] if m['platform'] == p][0]['rank']}位"
                          for p in c["platforms"])
        L.append(f"**{i}. {c['title']}**")
        L.append("")
        L.append(f"- 综合热度：**{c['score']:.0f}** ｜ 类别：{c['category']}"
                 + (f" ｜ 性质：{'、'.join(c['tags'])}" if c["tags"] else ""))
        L.append(f"- 平台分布：{plats}")
        if c.get("reason"):
            L.append(f"- 为什么火：{c['reason']}")
        if len(c["members"]) > 1:
            for m in c["members"]:
                L.append(f"  - {m['platform_name']} #{m['rank']}：{m['title']}")
        L.append("")

    L.append("## 四、为什么火（类目归因）")
    L.append("")
    if payload.get("category_analysis"):
        for a in payload["category_analysis"]:
            if a["share"] < 3:
                continue
            L.append(f"- **{a['category']}**（{a['count']} 个 · {a['share']}%）：{a['reason']}"
                     + (f" 代表：{a['sample']}" if a["sample"] else ""))
    L.append("")

    L.append("## 五、平台观察")
    L.append("")
    for row in st["platform_rows"]:
        cats = "、".join(f"{t['category']}{t['share']:.0f}%" for t in row["top_cats"])
        L.append(f"- **{row['name']}**（{row['count']} 条）：{cats} — {row['desc']}")
    L.append("")

    if payload.get("insights"):
        L.append("## 六、观察与判断")
        L.append("")
        for x in payload["insights"]:
            L.append(f"- **{x['title']}**：{x['text']}")
        L.append("")

    if payload.get("hotwords"):
        L.append("## 七、高频热词")
        L.append("")
        L.append("　".join(f"{w['word']}({w['count']})" for w in payload["hotwords"]))
        L.append("")

    fc = payload.get("focus")
    if fc:
        L.append(f"## 八、对你有什么用（{fc.get('label', '个人视角')}）")
        L.append("")
        for p in fc.get("advice", []):
            L.append(f"- {p}")
        L.append("")
        for title, key in [("机会信号", "opportunities"), ("风险预警", "risks"),
                           ("对标案例", "benchmarks"), ("可落地点子", "ideas")]:
            items = fc.get(key, [])
            L.append(f"**{title}**（{len(items)}）")
            if items:
                for it in items:
                    sec = f"｜{it['sector']}" if it.get("sector") else ""
                    L.append(f"- {it['title']}{sec}：{it['reason']}")
            else:
                L.append("- 今日暂无")
            L.append("")
        if fc.get("relevant"):
            L.append("**个人关注榜**（按相关度排序）")
            L.append("")
            for i, it in enumerate(fc["relevant"], 1):
                sig = ("｜" + "、".join(it["signals"])) if it.get("signals") else ""
                sec = f"｜{it['sector']}" if it.get("sector") else ""
                L.append(f"{i}. {it['title']}{sec}{sig}（相关度 {it['focus_score']:.0f}）")
            L.append("")

    L.append("## 九、全量榜单")
    L.append("")
    for pid in st["platforms"]:
        its = sorted([i for i in payload["items"] if i["platform"] == pid], key=lambda x: x["rank"])
        L.append(f"### {PLATFORMS[pid]['name']}（{len(its)} 条）")
        L.append("")
        L.append("| # | 标题 | 热度 |")
        L.append("| ---: | --- | ---: |")
        for it in its[:20]:
            t = str(it["title"]).replace("|", "\\|")
            L.append(f"| {it['rank']} | [{t}]({it.get('url', '')}) | {fmt_heat(it.get('heat'))} |")
        L.append("")

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{day}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return path
