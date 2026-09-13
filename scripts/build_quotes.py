#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQS-2.0 Markdown 生成脚本
读取：
  - data/quotes.yaml     （基础版，299 条）
  - data/quotes_v2.yaml  （升级版，优先使用）
输出：
  - content/quotes/{chapter_slug}/{slug}/index.md
逻辑：
  - v2 优先，v2 里没有的用 v0 骨架
"""

import os
import re
import sys
import yaml
from pathlib import Path
from pypinyin import lazy_pinyin

ROOT = Path(__file__).parent.parent
V0_FILE = ROOT / "data" / "quotes.yaml"
V2_FILE = ROOT / "data" / "quotes_v2.yaml"
OUT_DIR = ROOT / "content" / "quotes"

# 13 篇顺序
CHAPTER_ORDER = {
    "chapter-01-shi-ji": 1,
    "chapter-02-zuo-zhan": 2,
    "chapter-03-mou-gong": 3,
    "chapter-04-jun-xing": 4,
    "chapter-05-bing-shi": 5,
    "chapter-06-xu-shi": 6,
    "chapter-07-jun-zheng": 7,
    "chapter-08-jiu-bian": 8,
    "chapter-09-xing-jun": 9,
    "chapter-10-di-xing": 10,
    "chapter-11-jiu-di": 11,
    "chapter-12-huo-gong": 12,
    "chapter-13-yong-jian": 13,
}


def yq(s):
    """YAML 安全字符串（双引号包裹）"""
    if s is None:
        return '""'
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def generate_slug(original):
    """从原文生成 slug：忽略开头「孙子曰：」，取 8-12 字，遇标点断，转拼音"""
    s = original
    # 忽略开头
    s = re.sub(r'^孙子曰[：:，,]', '', s)
    s = re.sub(r'^孙子曰', '', s)

    # 找 8-12 字最近的标点
    chars = []
    for i, ch in enumerate(s):
        if ch in '、，。；;,':
            if len(chars) >= 8:
                break
            chars = []  # 太短，清空
            continue
        chars.append(ch)
        if len(chars) >= 12:
            break

    text = ''.join(chars) if chars else s[:12]
    pinyin = lazy_pinyin(text)
    slug = '-'.join(pinyin).lower()
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    return slug[:75]


def build_cover(q, slug):
    """生成 cover 字段"""
    chapter_slug = q["chapter_slug"]
    default_image = f"quotes/{chapter_slug}/{slug}.jpg"

    cover = q.get("cover", {}) or {}
    image = cover.get("image", default_image)

    return {
        "image": image,
        "alt": cover.get("alt", q.get("original", "")[:20]),
        "title": cover.get("title", q.get("chapter", "")),
        "caption": cover.get("caption", q.get("chapter", "")),
        "width": cover.get("width", 1200),
        "height": cover.get("height", 630),
    }


def build_front_matter(q, slug, is_v2):
    """构建 Front Matter（YAML 文本）"""
    chapter = q["chapter"]
    chapter_slug = q["chapter_slug"]
    chapter_order = q.get("chapter_order", CHAPTER_ORDER.get(chapter_slug, 1))

    # 标题
    title = q.get("title") or f"“{q['original']}”是什么意思？"
    description = q.get("description", f"《孙子兵法·{chapter}》名句的原文、白话解释与竞技应用。")

    lines = ["---"]
    lines.append(f"title: {yq(title)}")
    lines.append(f"description: {yq(description)}")
    lines.append(f"slug: {yq(slug)}")
    lines.append(f"date: {q.get('date', '2026-09-13')}")
    lines.append(f"lastmod: {q.get('lastmod', '2026-09-13')}")
    lines.append('type: "quotes"')
    # v2 数据里的 draft 是"编辑中"标记，不等于"Hugo 草稿"
    # Hugo 层面统一输出 draft: false，版本用 content_version 追踪
    lines.append("draft: false")

    lines.append(f"ads: {str(q.get('ads', True)).lower()}")
    lines.append(f"toc: {str(q.get('toc', True)).lower()}")

    # 篇章归属
    lines.append(f"chapter: {yq(chapter)}")
    lines.append(f"chapter_slug: {yq(chapter_slug)}")
    lines.append(f"chapter_order: {chapter_order}")
    lines.append(f"quote_id: {yq(q.get('id', ''))}")
    lines.append(f"order: {q.get('order', 1)}")

    # 维度
    lines.append(f"quote_dimension: {yq(q.get('quote_dimension', ''))}")
    lines.append(f"quote_sub_dimension: {yq(q.get('quote_sub_dimension', ''))}")
    lines.append(f"core_dimension: {yq(q.get('quote_dimension', ''))}")
    lines.append(f"aux_dimension: {yq(q.get('quote_sub_dimension', ''))}")
    if q.get("dimension_focus"):
        lines.append(f"dimension_focus: {yq(q['dimension_focus'])}")

    # 作者
    lines.append(f"author: {yq(q.get('author', '吴雄山'))}")
    if q.get("authorTitle"):
        lines.append(f"authorTitle: {yq(q['authorTitle'])}")
    if q.get("authorLocation"):
        lines.append(f"authorLocation: {yq(q['authorLocation'])}")

    # 内容
    lines.append(f"original: {yq(q.get('original', ''))}")
    lines.append(f"translation: {yq(q.get('translation', ''))}")
    lines.append(f"source: {yq(q.get('source', ''))}")

    # 参考
    refs = q.get("references", [])
    if refs:
        lines.append("references:")
        for r in refs:
            lines.append(f"  - {yq(r)}")

    # 关键词
    kws = q.get("keywords", [])
    if kws:
        lines.append("keywords:")
        for k in kws:
            lines.append(f"  - {yq(k)}")

    # 奥运项目
    sports = q.get("olympic_sports", [])
    if sports:
        lines.append("olympic_sports:")
        for s in sports:
            lines.append(f"  - {yq(s)}")

    # 版本标记
    lines.append(f'content_version: "{ "v2" if is_v2 else "v0" }"')

    # TLDR
    tldr = q.get("tldr", [])
    if tldr:
        lines.append("tldr:")
        for t in tldr:
            lines.append(f"  - {yq(t)}")

    # Direct Answer
    if q.get("direct_answer"):
        lines.append(f"direct_answer: {yq(q['direct_answer'])}")

    # Defined Terms
    terms = q.get("defined_terms", [])
    if terms:
        lines.append("defined_terms:")
        for t in terms:
            lines.append(f"  - term: {yq(t.get('term', ''))}")
            lines.append(f"    description: {yq(t.get('description', ''))}")

    # HowTo
    howto = q.get("howto", [])
    if howto:
        lines.append("howto:")
        for h in howto:
            lines.append(f"  - name: {yq(h.get('name', ''))}")
            lines.append(f"    text: {yq(h.get('text', ''))}")

    # ItemList
    items = q.get("itemlist", [])
    if items:
        lines.append("itemlist:")
        for it in items:
            lines.append(f"  - name: {yq(it.get('name', ''))}")
            lines.append(f"    description: {yq(it.get('description', ''))}")

    # FAQ
    faq = q.get("faq", [])
    if faq:
        lines.append("faq:")
        for f in faq:
            lines.append(f"  - q: {yq(f.get('q', ''))}")
            lines.append(f"    a: {yq(f.get('a', ''))}")

    # Related
    related = q.get("related", [])
    if related:
        lines.append("related:")
        for r in related:
            lines.append(f"  - {yq(r)}")

    # Cover
    cover = build_cover(q, slug)
    lines.append("cover:")
    lines.append(f"  image: {yq(cover['image'])}")
    lines.append(f"  alt: {yq(cover['alt'])}")
    lines.append(f"  title: {yq(cover['title'])}")
    lines.append(f"  caption: {yq(cover['caption'])}")
    lines.append(f"  width: {cover['width']}")
    lines.append(f"  height: {cover['height']}")

    lines.append("---")
    return "\n".join(lines)


def build_body_v2(q):
    """v2 正文：从 sections 拼接"""
    sections = q.get("sections", {})
    parts = []
    for key in ["section1", "section2", "section3", "section4", "section5"]:
        if key in sections:
            parts.append(sections[key].strip())
    return "\n\n".join(parts)


def build_body_v0(q):
    """v0 骨架正文"""
    parts = []
    parts.append("## 原文\n")
    parts.append(q.get("original", "") + "\n")
    parts.append(f"出处：{q.get('source', '')}\n")
    parts.append("## 白话解释\n")
    parts.append(q.get("translation", "") + "\n")
    if q.get("sport_application"):
        parts.append("## 在体育竞技中的作用\n")
        parts.append(q["sport_application"] + "\n")
    # FAQ
    faq = q.get("faq_short", [])
    if faq:
        parts.append("## 常见问题\n")
        for f in faq:
            parts.append(f"### {f.get('q', '')}\n")
            parts.append(f.get("a", "") + "\n")
    return "\n".join(parts)


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def main():
    # 读取 v0
    print("📖 读取 data/quotes.yaml（v0）...")
    with open(V0_FILE, encoding="utf-8") as f:
        v0_data = yaml.safe_load(f)
    print(f"   {len(v0_data)} 条")

    # 读取 v2（如存在）
    v2_data = []
    if V2_FILE.exists():
        print("📖 读取 data/quotes_v2.yaml（v2）...")
        with open(V2_FILE, encoding="utf-8") as f:
            v2_data = yaml.safe_load(f) or []
        print(f"   {len(v2_data)} 条")

    # 建立 v2 索引（按 id）
    v2_map = {q["id"]: q for q in v2_data if q.get("id")}

    # 按篇分组
    by_chapter = {}
    count_v2 = 0
    count_v0 = 0

    for q in v0_data:
        qid = q.get("id")
        chapter_slug = q["chapter_slug"]

        # 决定用 v2 还是 v0
        if qid in v2_map:
            merged = {**q, **v2_map[qid]}  # v2 优先
            is_v2 = True
            count_v2 += 1
        else:
            merged = q
            is_v2 = False
            count_v0 += 1

        # slug：v2 有则用，否则从 original 生成
        slug = merged.get("slug") or generate_slug(merged.get("original", ""))

        # Front Matter
        fm = build_front_matter(merged, slug, is_v2)

        # 正文
        if is_v2 and merged.get("sections"):
            body = build_body_v2(merged)
        else:
            body = build_body_v0(merged)

        content = fm + "\n\n" + body + "\n"

        # 输出路径
        path = OUT_DIR / chapter_slug / slug / "index.md"
        write_file(str(path), content)

        # 记录到篇分组
        if chapter_slug not in by_chapter:
            by_chapter[chapter_slug] = {
                "title": merged.get("chapter", ""),
                "order": merged.get("chapter_order", CHAPTER_ORDER.get(chapter_slug, 1)),
                "count": 0,
            }
        by_chapter[chapter_slug]["count"] += 1

    # 生成各篇 _index.md
    for chapter_slug, info in by_chapter.items():
        idx_path = OUT_DIR / chapter_slug / "_index.md"
        idx_content = f"""---
title: {yq(info['title'])}
weight: {info['order']}
description: {yq(f"《孙子兵法·{info['title']}》经典语录。")}
type: "quotes"
chapter: {yq(info['title'])}
chapter_slug: {yq(chapter_slug)}
chapter_order: {info['order']}
cover:
  image: {yq(f"placeholder/quotes.jpg")}
  alt: {yq(info['title'])}
  caption: {yq(info['title'])}
draft: false
---
"""
        write_file(str(idx_path), idx_content)

    # 顶层 _index.md
    top_idx = OUT_DIR / "_index.md"
    if not top_idx.exists():
        top_content = """---
title: "经典语录"
description: "《孙子兵法》十三篇经典语录，按篇分类，每条附原文、翻译、FAQ 与竞技应用。"
type: "quotes"
cascade:
  type: "quotes"
---
"""
        write_file(str(top_idx), top_content)

    print(f"\n✅ 完成！")
    print(f"   v2 完整版：{count_v2} 条")
    print(f"   v0 骨架版：{count_v0} 条")
    print(f"   总计：{count_v2 + count_v0} 条")
    print(f"   篇数：{len(by_chapter)}")
    print(f"   输出：{OUT_DIR}")


if __name__ == "__main__":
    main()