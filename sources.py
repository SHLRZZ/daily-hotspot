# -*- coding: utf-8 -*-
"""各平台热榜抓取与归一化。

统一输出条目结构：
{
  "platform": "weibo", "title": "...", "url": "...",
  "heat": 1152749 | None, "rank": 1, "label": "热|沸|爆|新|置顶|"
}
"""
import gzip
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from config import BASE_CHROME, PLATFORM_ORDER

TIMEOUT = 12

_HDR = {
    "User-Agent": BASE_CHROME,
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _request(url, referer=None, timeout=TIMEOUT):
    headers = dict(_HDR)
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8", "ignore"))


def _clean(t):
    if not t:
        return ""
    t = re.sub(r"\s+", " ", str(t)).strip()
    return t


# ---------------- 各平台解析器 ----------------

def _p_weibo():
    d = _request("https://weibo.com/ajax/side/hotSearch", referer="https://weibo.com/")
    out = []
    for i, it in enumerate(d.get("data", {}).get("realtime", []), 1):
        if it.get("is_ad"):
            continue
        title = _clean(it.get("note") or it.get("word"))
        if not title:
            continue
        out.append({
            "title": title,
            "url": "https://s.weibo.com/weibo?q=%23" + urllib.parse.quote(title) + "%23",
            "heat": it.get("num"),
            "rank": it.get("realpos") or i,
            "label": _clean(it.get("label_name")),
        })
    return out


def _p_baidu():
    d = _request("https://top.baidu.com/api/board?platform=wise&tab=realtime",
                 referer="https://top.baidu.com/board?tab=realtime")
    items = d.get("data", {}).get("cards", [{}])[0].get("content", [{}])[0].get("content", [])
    out = []
    for i, it in enumerate(items, 1):
        title = _clean(it.get("word"))
        if not title:
            continue
        out.append({
            "title": title,
            "url": it.get("url") or "https://www.baidu.com/s?wd=" + urllib.parse.quote(title),
            "heat": it.get("hotScore"),
            "rank": i,
            "label": "置顶" if it.get("isTop") else _clean(it.get("hotTag")),
        })
    return out


def _p_douyin():
    d = _request("https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/",
                 referer="https://www.douyin.com/")
    label_map = {1: "新", 3: "热", 5: "新", 8: "爆", 9: "荐"}
    out = []
    for i, it in enumerate(d.get("word_list") or [], 1):
        title = _clean(it.get("word"))
        if not title:
            continue
        out.append({
            "title": title,
            "url": "https://www.douyin.com/search/" + urllib.parse.quote(title),
            "heat": it.get("hot_value"),
            "rank": i,
            "label": label_map.get(it.get("label"), ""),
        })
    return out


def _parse_zhihu_heat(text):
    """'1333 万热度' -> 13330000"""
    if not text:
        return None
    m = re.search(r"([\d.]+)\s*(万|亿)?", str(text))
    if not m:
        return None
    v = float(m.group(1))
    if m.group(2) == "万":
        v *= 1e4
    elif m.group(2) == "亿":
        v *= 1e8
    return int(v)


def _p_zhihu():
    d = _request("https://api.zhihu.com/topstory/hot-lists/total?limit=50",
                 referer="https://www.zhihu.com/hot")
    out = []
    for i, it in enumerate(d.get("data") or [], 1):
        tgt = it.get("target") or {}
        title = _clean(tgt.get("title"))
        if not title:
            continue
        qid = tgt.get("id")
        out.append({
            "title": title,
            "url": f"https://www.zhihu.com/question/{qid}" if qid else "https://www.zhihu.com/hot",
            "heat": _parse_zhihu_heat(it.get("detail_text")),
            "rank": i,
            "label": "热" if i <= 3 else "",
            "excerpt": _clean(tgt.get("excerpt"))[:120],
            "answers": tgt.get("answer_count"),
        })
    return out


def _p_toutiao():
    d = _request("https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
                 referer="https://www.toutiao.com/")
    out = []
    for i, it in enumerate(d.get("data") or [], 1):
        title = _clean(it.get("Title"))
        if not title:
            continue
        cats = it.get("InterestCategory") or []
        out.append({
            "title": title,
            "url": it.get("Url") or "",
            "heat": it.get("HotValue"),
            "rank": i,
            "label": _clean(it.get("Label")),
            "category_hint": cats[0] if cats else "",
        })
    return out


def _p_bilibili():
    d = _request("https://api.bilibili.com/x/web-interface/search/square?limit=30",
                 referer="https://www.bilibili.com/")
    lst = ((d.get("data") or {}).get("trending") or {}).get("list") or []
    out = []
    for i, it in enumerate(lst, 1):
        title = _clean(it.get("show_name") or it.get("keyword"))
        if not title:
            continue
        out.append({
            "title": title,
            "url": "https://search.bilibili.com/all?keyword=" + urllib.parse.quote(title),
            "heat": it.get("heat_score"),
            "rank": i,
            "label": "",
        })
    return out


PARSERS = {
    "weibo": _p_weibo,
    "baidu": _p_baidu,
    "douyin": _p_douyin,
    "zhihu": _p_zhihu,
    "toutiao": _p_toutiao,
    "bilibili": _p_bilibili,
}


def fetch_one(pid, retries=1):
    """抓取单个平台，返回 (pid, items, error)。"""
    last_err = ""
    for _ in range(retries + 1):
        try:
            items = PARSERS[pid]()
            if items:
                for it in items:
                    it["platform"] = pid
                    it.setdefault("label", "")
                return pid, items, ""
            last_err = "接口返回空列表"
        except Exception as exc:  # noqa: BLE001
            last_err = f"{type(exc).__name__}: {exc}"
    return pid, [], last_err


def fetch_all(sources=None, workers=6):
    """并发抓取全部平台。

    返回 (items, status)，status[pid] = {"ok": bool, "count": n, "error": str}
    """
    pids = sources or PLATFORM_ORDER
    items, status = [], {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for pid, got, err in pool.map(fetch_one, pids):
            status[pid] = {"ok": bool(got), "count": len(got), "error": err}
            items.extend(got)
    return items, status
