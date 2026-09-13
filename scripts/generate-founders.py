#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI孙子兵法 · 创业故事生成脚本
生成 content/founders/ 下的 5 个故事骨架
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'content', 'founders')


STORIES = [
    {
        "slug": "manja-foods-supply-founder-jac-ho",
        "title": "Jac Ho：从 Manja Foods Supply 到食品供应创业",
        "founder": "Jac Ho",
        "company": "Manja Foods Supply",
        "industry": "食品供应",
        "theme": "食品供应链创业",
    },
    {
        "slug": "k-phonics-education-innovation-founder-charmaine-ong",
        "title": "Charmaine Ong：K-Phonics 教育创新的创业之路",
        "founder": "Charmaine Ong",
        "company": "K-Phonics",
        "industry": "教育创新",
        "theme": "儿童教育创业",
    },
    {
        "slug": "green-hope-community-ricky-wong-csr-brand-angel",
        "title": "Ricky Wong：Green Hope Community 与 CSR 品牌天使",
        "founder": "Ricky Wong",
        "company": "Green Hope Community",
        "industry": "社会企业",
        "theme": "CSR 与公益品牌",
    },
    {
        "slug": "ai-sunzi-bingfa-steven-tang-how-education-innovation",
        "title": "Steven Tang：AI孙子兵法与教育创新的结合",
        "founder": "Steven Tang",
        "company": "AI孙子兵法",
        "industry": "教育创新",
        "theme": "传统文化 + AI 教育",
    },
    {
        "slug": "andrew-chong-ai-sun-tzu-youth-strategy-program",
        "title": "Andrew Chong：AI孙子兵法青年战略计划",
        "founder": "Andrew Chong",
        "company": "AI孙子兵法",
        "industry": "青年教育",
        "theme": "青少年战略思维培训",
    },
]


def yq(s):
    """YAML 安全字符串"""
    if s is None:
        return '""'
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def build_front_matter(story):
    lines = []
    lines.append('---')
    lines.append(f'title: {yq(story["title"])}')
    lines.append(f'description: {yq(story["theme"] + " - " + story["company"] + " 创业故事。")}')
    lines.append(f'slug: {yq(story["slug"])}')
    lines.append('date: 2026-09-13')
    lines.append('lastmod: 2026-09-13')
    lines.append('type: "founders"')
    lines.append(f'founder: {yq(story["founder"])}')
    lines.append(f'company: {yq(story["company"])}')
    lines.append(f'industry: {yq(story["industry"])}')
    lines.append('stage: ""')
    lines.append('location: ""')
    lines.append('tags: []')
    lines.append('keywords: []')
    lines.append('faq: []')
    lines.append('cover:')
    lines.append(f'  image: {yq("placeholder/founders.jpg")}')
    lines.append(f'  alt: {yq(story["founder"] + " 创业故事")}')
    lines.append(f'  caption: {yq(story["company"])}')
    lines.append('draft: false')
    lines.append('ads:')
    lines.append('  top: true')
    lines.append('  bottom: true')
    lines.append('---')
    return '\n'.join(lines)


def build_body(story):
    parts = []
    parts.append('## 一句话摘要\n')
    parts.append(f'{story["founder"]}，{story["company"]} 创始人。本文讲述他的创业故事。\n')
    parts.append('## 人物背景\n')
    parts.append('（待补充）\n')
    parts.append('## 创业起点\n')
    parts.append('（待补充）\n')
    parts.append('## 关键转折\n')
    parts.append('（待补充）\n')
    parts.append('## 踩过的坑\n')
    parts.append('（待补充）\n')
    parts.append('## 现状与启示\n')
    parts.append('（待补充）\n')
    parts.append('## 常见问题\n')
    parts.append('（待补充）\n')
    return '\n'.join(parts)


def build_index():
    lines = [
        '---',
        'title: "朋友创业圈"',
        'description: "身边朋友的创业故事，真实、具体、可借鉴。"',
        'type: "founders"',
        'cascade:',
        '  type: "founders"',
        'cover:',
        '  image: "placeholder/founders.jpg"',
        '  alt: "朋友创业圈"',
        '  caption: "朋友创业圈"',
        '---',
    ]
    return '\n'.join(lines)


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)


def main():
    print('✍️  生成创业故事骨架...')

    # 顶层 _index.md
    write_file(os.path.join(OUT_DIR, '_index.md'), build_index())

    count = 0
    for story in STORIES:
        path = os.path.join(OUT_DIR, story['slug'], 'index.md')
        content = build_front_matter(story) + '\n\n' + build_body(story)
        write_file(path, content)
        print(f'   ✅ {story["slug"]}')
        count += 1

    print(f'\n✅ 完成！共生成 {count} 个创业故事骨架。')


if __name__ == '__main__':
    main()