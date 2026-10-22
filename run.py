# -*- coding: utf-8 -*-
"""每日网络热点采集与归纳工具 —— CLI 入口。

用法:
    python run.py                 # 抓取全平台，生成当日报告
    python run.py --top 15        # 只详列前 15 个话题
    python run.py --sources weibo,zhihu
    python run.py --offline       # 不联网，用最近一次采集数据重新渲染
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyzer  # noqa: E402
import report  # noqa: E402
import sources  # noqa: E402
from config import PLATFORMS, PLATFORM_ORDER  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
REPORT_DIR = os.path.join(ROOT, "reports")


def ensure_dirs():
    for d in (DATA_DIR, REPORT_DIR):
        os.makedirs(d, exist_ok=True)


def save_json(payload, day):
    ensure_dirs()
    path = os.path.join(DATA_DIR, f"{day}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return path


def latest_data():
    if not os.path.isdir(DATA_DIR):
        return None
    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".json"))
    if not files:
        return None
    path = os.path.join(DATA_DIR, files[-1])
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def previous_data(day):
    """取上一份（非当天）采集数据，用于对比。"""
    if not os.path.isdir(DATA_DIR):
        return None
    files = sorted(f for f in os.listdir(DATA_DIR)
                   if f.endswith(".json") and f[:-5] < day)
    if not files:
        return None
    with open(os.path.join(DATA_DIR, files[-1]), encoding="utf-8") as f:
        return json.load(f), files[-1][:-5]


def run(args):
    ensure_dirs()
    now = datetime.now()
    day = now.strftime("%Y-%m-%d")

    if args.offline:
        got = latest_data()
        if not got:
            print("✗ 没有可用的历史采集数据，先联网跑一次吧。")
            return 1
        payload, path = got
        print(f"· 离线模式，复用 {os.path.basename(path)} 并重新归纳")
        payload.update(analyzer.analyze(payload["items"], payload.get("status", {})))
    else:
        pids = [p.strip() for p in args.sources.split(",") if p.strip()] if args.sources else PLATFORM_ORDER
        bad = [p for p in pids if p not in PLATFORMS]
        if bad:
            print(f"✗ 未知数据源: {', '.join(bad)}；可选: {', '.join(PLATFORM_ORDER)}")
            return 1
        print(f"· 开始采集 {len(pids)} 个平台热榜 …")
        items, status = sources.fetch_all(pids)
        for pid in pids:
            s = status.get(pid, {})
            flag = "✓" if s.get("ok") else "✗"
            extra = f"{s.get('count', 0)} 条" if s.get("ok") else (s.get("error") or "失败")
            print(f"  {flag} {PLATFORMS[pid]['name']:<4} {extra}")
        if not items:
            print("✗ 全部数据源采集失败，检查网络后重试。")
            return 1

        result = analyzer.analyze(items, status)
        payload = {
            "date": day,
            "collected_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "items": items,
            **result,
        }
        path = save_json(payload, day)
        print(f"· 原始数据已归档 {os.path.relpath(path, ROOT)}")

    prev = previous_data(payload.get("date", day))
    prev_payload = prev[0] if prev else None
    html_path = report.render(payload, REPORT_DIR, top=args.top, prev=prev_payload)
    latest = os.path.join(REPORT_DIR, "latest.html")
    shutil.copyfile(html_path, latest)
    md_path = report.render_markdown(payload, REPORT_DIR, top=args.top)
    index_path = report.render_index(DATA_DIR, REPORT_DIR)

    st = payload["stats"]
    print("\n" + "─" * 58)
    print(f"  {payload['date']} 网络热点日报")
    print("─" * 58)
    print(f"  平台 {st['platform_count']} 个 · 条目 {st['item_count']} 条 · "
          f"话题 {st['cluster_count']} 个 · 跨平台 {st['cross2_count']} 个")
    for p in payload["summary"]:
        print("\n  " + p)
    print("\n  Top 5 话题")
    for i, c in enumerate(payload["clusters"][:5], 1):
        names = "/".join(PLATFORMS[x]["name"] for x in c["platforms"])
        print(f"  {i}. [{c['score']:>5.1f}] {c['title'][:34]}  ({c['category']} · {names})")

    fc = payload.get("focus")
    if fc:
        print("\n  ── 对你有什么用（投资/理财/副业） ──")
        for p in fc.get("advice", []):
            print("  · " + p)
        opp = fc.get("opportunities", [])
        risk = fc.get("risks", [])
        if opp:
            print("  ▸ 机会：" + "；".join(c["title"][:20] for c in opp[:3]))
        if risk:
            print("  ▸ 风险：" + "；".join(c["title"][:20] for c in risk[:3]))
    print("\n  报告: " + os.path.relpath(html_path, ROOT))
    print("  摘要: " + os.path.relpath(md_path, ROOT))
    return 0


def main():
    ap = argparse.ArgumentParser(description="每日网络热点采集与归纳")
    ap.add_argument("--top", type=int, default=12, help="报告中详列的话题数")
    ap.add_argument("--sources", default="", help="指定平台，逗号分隔，如 weibo,zhihu")
    ap.add_argument("--offline", action="store_true", help="不联网，复用最近一次采集数据")
    return run(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
