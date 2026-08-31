# -*- coding: utf-8 -*-
"""
晴太のらぢお ― ポッドキャストRSS（住所録）を組み立てる

episodes.json（過去51回）と、新チャンネルのRSS（#52以降）を合体させて
feed.xml を書き出します。

使い方:
    python3 generate_feed.py                 # 過去51回だけで作る
    python3 generate_feed.py --new-rss URL   # 新チャンネルのRSSも合体させる
"""
from __future__ import annotations
import argparse, json, re, sys, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ============ ここだけ書き換えれば設定は終わりです ============
BASE_URL   = "https://seitasaegusa-dot.github.io/seita_no_radio"
TITLE      = "晴太のらぢお｜Kodo Heartbeat Radio"
AUTHOR     = "KODO"
OWNER_MAIL = "seita.saegusa@kodo-group.com"                     # ← Apple の本人確認に使われます
LANGUAGE   = "ja"
CATEGORIES = [("Music", "Music Commentary"), ("Arts", "Performing Arts")]
DESCRIPTION = """太鼓芸能集団「鼓童」の三枝晴太が、太鼓のことだけを話す番組です。

プロの打ち手が普段どう考えているのか。稽古場で何が起きているのか。
全国の太鼓打ちが、なぜあそこまで打ち込むのか。

太鼓を打っている人、これから始めたい人、
そして「あの音は何なのか」が気になった人へ。毎週木曜20時に更新します。

鼓童の番組「Kodo Heartbeat Radio」から生まれた、太鼓の話だけの番組です。
本編（メンバーインタビュー・公演の裏側）は Kodo Heartbeat Radio でどうぞ。

出演：三枝晴太（鼓童）
お便り・出演希望は Instagram @seita_no_radio まで"""
# ==============================================================

CDN_AUDIO = "https://cdncf.stand.fm/audios/{}"
CDN_IMAGE = "https://cdncf.stand.fm/cdn-cgi/image/fit=cover,width=1400,height=1400/coverImages/{}"
ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
NS = {"itunes": ITUNES, "content": "http://purl.org/rss/1.0/modules/content/"}


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cdata(s: str) -> str:
    return "<![CDATA[" + (s or "").replace("]]>", "]]&gt;") + "]]>"


def load_past() -> list[dict]:
    rows = json.loads((HERE / "episodes.json").read_text(encoding="utf-8"))
    out = []
    for r in rows:
        out.append({
            "ep": r["ep"], "title": r["t"], "desc": r["d"], "pub": r["pub"],
            "dur": r["dur"], "audio": CDN_AUDIO.format(r["au"]),
            "image": CDN_IMAGE.format(r["im"]),
            "guid": "seita-radio-" + str(r["ep"]),
            "type": "audio/x-m4a",
        })
    return out


def load_new(url: str) -> list[dict]:
    """新チャンネルのRSSから #52 以降を拾う。"""
    req = urllib.request.Request(url, headers={"User-Agent": "seita-radio-feed/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        ch = ET.fromstring(r.read()).find("channel")
    out = []
    for it in ch.findall("item"):
        t = (it.findtext("title") or "").strip()
        m = re.search(r"#\s*(\d+)", t)
        if not m:
            continue
        ep = int(m.group(1))
        if ep <= 51:
            continue
        enc = it.find("enclosure")
        if enc is None:
            continue
        img = it.find("itunes:image", NS)
        out.append({
            "ep": ep, "title": t,
            "desc": it.findtext("description") or "",
            "pub": (it.findtext("pubDate") or "").strip(),
            "dur": (it.findtext("itunes:duration", default="", namespaces=NS) or "").strip(),
            "audio": enc.get("url"), "type": enc.get("type") or "audio/x-m4a",
            "image": (img.get("href") if img is not None else ""),
            "guid": "seita-radio-" + str(ep),
        })
    return out


def build(items: list[dict]) -> str:
    items = sorted(items, key=lambda x: x["ep"], reverse=True)   # 新しい順
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    L = []
    A = L.append
    A('<?xml version="1.0" encoding="UTF-8"?>')
    A('<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" '
      'xmlns:content="http://purl.org/rss/1.0/modules/content/" '
      'xmlns:atom="http://www.w3.org/2005/Atom">')
    A('<channel>')
    A(f'<title>{esc(TITLE)}</title>')
    A(f'<link>{esc(BASE_URL)}/</link>')
    A(f'<atom:link href="{esc(BASE_URL)}/feed.xml" rel="self" type="application/rss+xml"/>')
    A(f'<language>{LANGUAGE}</language>')
    A(f'<lastBuildDate>{now}</lastBuildDate>')
    A(f'<description>{cdata(DESCRIPTION)}</description>')
    A(f'<itunes:summary>{cdata(DESCRIPTION)}</itunes:summary>')
    A(f'<itunes:author>{esc(AUTHOR)}</itunes:author>')
    A('<itunes:owner>')
    A(f'  <itunes:name>{esc(AUTHOR)}</itunes:name>')
    A(f'  <itunes:email>{esc(OWNER_MAIL)}</itunes:email>')
    A('</itunes:owner>')
    A(f'<itunes:image href="{esc(BASE_URL)}/cover.jpg"/>')
    A('<itunes:explicit>false</itunes:explicit>')
    A('<itunes:type>episodic</itunes:type>')
    for main, sub in CATEGORIES:
        A(f'<itunes:category text="{esc(main)}"><itunes:category text="{esc(sub)}"/></itunes:category>')
    A(f'<copyright>{esc(AUTHOR)}</copyright>')

    for it in items:
        A('<item>')
        A(f'  <title>{esc(it["title"])}</title>')
        A(f'  <description>{cdata(it["desc"])}</description>')
        A(f'  <content:encoded>{cdata(it["desc"])}</content:encoded>')
        A(f'  <pubDate>{esc(it["pub"])}</pubDate>')
        A(f'  <guid isPermaLink="false">{esc(it["guid"])}</guid>')
        A(f'  <enclosure url="{esc(it["audio"])}" type="{esc(it["type"])}" length="0"/>')
        if it.get("dur"):
            A(f'  <itunes:duration>{esc(it["dur"])}</itunes:duration>')
        if it.get("image"):
            A(f'  <itunes:image href="{esc(it["image"])}"/>')
        A(f'  <itunes:episode>{it["ep"]}</itunes:episode>')
        A('  <itunes:explicit>false</itunes:explicit>')
        A('</item>')

    A('</channel>')
    A('</rss>')
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--new-rss", default="", help="新チャンネルのRSS（#52以降）")
    a = ap.parse_args()

    items = load_past()
    n_new = 0
    rss = a.new_rss
    if not rss:
        f = HERE / "new_rss.txt"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    rss = line
                    break
    a.new_rss = rss
    if a.new_rss:
        try:
            new = load_new(a.new_rss)
            have = {i["ep"] for i in items}
            new = [x for x in new if x["ep"] not in have]
            items += new
            n_new = len(new)
        except Exception as e:
            print(f"★注意★ 新チャンネルのRSSが読めませんでした: {e}")
            print("　過去51回だけで書き出します（既存のfeed.xmlは壊しません）。")
            sys.exit(1)

    xml = build(items)
    (HERE / "feed.xml").write_text(xml, encoding="utf-8")
    print(f"feed.xml を書き出しました  全{len(items)}回（うち新規{n_new}回）")
    print(f"  最新: #{max(i['ep'] for i in items)}   最古: #{min(i['ep'] for i in items)}")
