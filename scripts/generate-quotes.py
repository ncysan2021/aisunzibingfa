#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI孙子兵法 · 语录生成脚本
从 data/quotes.yaml 生成 content/quotes/ 下的所有 Markdown 页面
"""

import os
import sys
import yaml

# ─── 路径配置 ─────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, 'data', 'quotes.yaml')
OUT_DIR = os.path.join(ROOT, 'content', 'quotes')

VALID_DIMENSIONS = ['战略', '战术', '执行', '复盘', '资源约束', '物理极限']


# ─── 读取数据 ─────────────────────────────
def load_quotes():
    with open(DATA_FILE, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        print('❌ data/quotes.yaml 必须是数组')
        sys.exit(1)
    return data


# ─── 校验 ─────────────────────────────────
def validate(quotes):
    required = ['id', 'slug', 'chapter', 'chapter_slug',
                'original', 'translation', 'source']
    for q in quotes:
        for k in required:
            if not q.get(k):
                print(f"❌ 语录 {q.get('id', '(无 id)')} 缺少字段：{k}")
                sys.exit(1)
        dim = q.get('quote_dimension')
        if dim not in VALID_DIMENSIONS:
            print(f"❌ {q['id']} quote_dimension 非法：{dim}")
            sys.exit(1)
        sub = q.get('quote_sub_dimension')
        if sub and sub not in VALID_DIMENSIONS:
            print(f"❌ {q['id']} quote_sub_dimension 非法：{sub}")
            sys.exit(1)


# ─── 按篇分组 ─────────────────────────────
def group_by_chapter(quotes):
    chapters = {}
    for q in quotes:
        slug = q['chapter_slug']
        if slug not in chapters:
            chapters[slug] = {
                'slug': slug,
                'title': q['chapter'],
                'order': q.get('chapter_order', len(chapters) + 1),
                'quotes': [],
            }
        chapters[slug]['quotes'].append(q)
    for ch in chapters.values():
        ch['quotes'].sort(key=lambda x: x.get('order', 0))
    return chapters


# ─── YAML 转义 ────────────────────────────
def yq(s):
    """把字符串转为 YAML 安全格式"""
    if s is None:
        return '""'
    s = str(s)
    # 使用双引号包裹，转义内部双引号
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


# ─── 生成单条语录的 Front Matter ──────────
def build_front_matter(q):
    lines = []
    lines.append('---')
    lines.append(f'title: {yq("“" + q["original"] + "”是什么意思？")}')
    lines.append(f'description: {yq(q["source"] + "名句的原文、白话解释与竞技应用。")}')
    lines.append(f'slug: {yq(q["slug"])}')
    lines.append(f'date: {q.get("date", "2026-09-12")}')
    lines.append(f'lastmod: {q.get("date", "2026-09-12")}')
    lines.append('type: "quotes"')
    lines.append(f'chapter: {yq(q["chapter"])}')
    lines.append(f'chapter_slug: {yq(q["chapter_slug"])}')
    lines.append(f'chapter_order: {q.get("chapter_order", 1)}')
    lines.append(f'quote_id: {yq(q["id"])}')
    lines.append(f'order: {q.get("order", 1)}')
    lines.append(f'core_dimension: {yq(q.get("quote_dimension", ""))}')
    lines.append(f'aux_dimension: {yq(q.get("quote_sub_dimension", ""))}')
    lines.append(f'quote_dimension: {yq(q.get("quote_dimension", ""))}')
    lines.append(f'quote_sub_dimension: {yq(q.get("quote_sub_dimension", ""))}')
    lines.append(f'original: {yq(q["original"])}')
    lines.append(f'translation: {yq(q["translation"])}')
    lines.append(f'source: {yq(q["source"])}')
    lines.append('content_version: "v0"')
    # FAQ
    faq = q.get('faq_short', [])
    if faq:
        lines.append('faq:')
        for item in faq:
            lines.append(f'  - q: {yq(item.get("q", ""))}')
            lines.append(f'    a: {yq(item.get("a", ""))}')
    else:
        lines.append('faq: []')
    # Cover
    lines.append('cover:')
    lines.append(f'  image: {yq("placeholder/quotes.jpg")}')
    lines.append(f'  alt: {yq(q["original"][:20])}')
    lines.append(f'  caption: {yq(q["chapter"] + "：" + q["original"][:10])}')
    lines.append('draft: false')
    lines.append('ads:')
    lines.append('  top: true')
    lines.append('  bottom: true')
    lines.append('---')
    return '\n'.join(lines)


# ─── 生成单条语录的正文 ───────────────────
def build_body(q):
    parts = []
    parts.append('## 原文\n')
    parts.append(q['original'] + '\n')
    parts.append(f'出处：{q["source"]}\n')
    parts.append('## 白话解释\n')
    parts.append(q['translation'] + '\n')
    if q.get('sport_application'):
        parts.append('## 在体育竞技中的作用\n')
        parts.append(q['sport_application'] + '\n')
    parts.append('## 常见问题\n')
    for item in q.get('faq_short', []):
        parts.append(f'### {item.get("q", "")}\n')
        parts.append(item.get('a', '') + '\n')
    return '\n'.join(parts)


# ─── 生成篇聚合页 _index.md ───────────────
def build_chapter_index(ch):
    lines = []
    lines.append('---')
    lines.append(f'title: {yq(ch["title"])}')
    lines.append(f'weight: {ch["order"]}')
    lines.append(f'description: {yq("《孙子兵法·" + ch["title"] + "》经典语录。")}')
    lines.append('type: "quotes"')
    lines.append(f'chapter: {yq(ch["title"])}')
    lines.append(f'chapter_slug: {yq(ch["slug"])}')
    lines.append(f'chapter_order: {ch["order"]}')
    lines.append('cover:')
    lines.append(f'  image: {yq("placeholder/quotes.jpg")}')
    lines.append(f'  alt: {yq(ch["title"])}')
    lines.append(f'  caption: {yq(ch["title"])}')
    lines.append('draft: false')
    lines.append('---')
    return '\n'.join(lines)


# ─── 生成顶层 _index.md ───────────────────
def build_top_index():
    lines = [
        '---',
        'title: "经典语录"',
        'description: "《孙子兵法》十三篇经典语录，按篇分类，每条附原文、翻译、FAQ 与竞技应用。"',
        'type: "quotes"',
        'cascade:',
        '  type: "quotes"',
        '---',
    ]
    return '\n'.join(lines)


# ─── 写入文件 ─────────────────────────────
def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)


# ─── 主流程 ───────────────────────────────
def main():
    print('📖 读取 data/quotes.yaml...')
    quotes = load_quotes()
    print(f'   共 {len(quotes)} 条')

    print('🔍 校验字段...')
    validate(quotes)

    print('📦 按篇分组...')
    chapters = group_by_chapter(quotes)
    print(f'   共 {len(chapters)} 篇')

    print('✍️  生成 Markdown...')
    count = 0

    # 顶层
    write_file(os.path.join(OUT_DIR, '_index.md'), build_top_index())

    for slug, ch in sorted(chapters.items(), key=lambda x: x[1]['order']):
        # 篇聚合页
        chapter_dir = os.path.join(OUT_DIR, slug)
        write_file(os.path.join(chapter_dir, '_index.md'), build_chapter_index(ch))

        # 每条语录
        for q in ch['quotes']:
            quote_dir = os.path.join(chapter_dir, q['slug'])
            path = os.path.join(quote_dir, 'index.md')
            content = build_front_matter(q) + '\n\n' + build_body(q)
            write_file(path, content)
            count += 1

    print(f'✅ 完成！生成 {count} 条语录页面，覆盖 {len(chapters)} 篇。')


if __name__ == '__main__':
    main()