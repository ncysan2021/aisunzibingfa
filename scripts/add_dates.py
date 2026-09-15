#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 6 个静态页补充 date 和 lastmod"""

import re
from pathlib import Path

files = [
    'content/about/index.md',
    'content/blueprint/index.md',
    'content/brand-story/index.md',
    'content/contact/index.md',
    'content/exam/index.md',
    'content/privacy/index.md',
]

DATE = '2026-09-15'

for f in files:
    p = Path(f)
    text = p.read_text(encoding='utf-8')

    # 拆分 Front Matter
    parts = text.split('---', 2)
    if len(parts) < 3:
        print(f'⏭  {f}（Front Matter 格式异常）')
        continue

    fm = parts[1]
    body = parts[2]

    if 'date:' in fm:
        print(f'⏭  {f}（已有 date）')
        continue

    # 在 slug: xxx 行后插入 date 和 lastmod
    fm_new = re.sub(
        r'(slug:\s*"[^"]+"\s*\n)',
        r'\1' + f'date: {DATE}\nlastmod: {DATE}\n',
        fm,
        count=1,
    )

    if fm_new == fm:
        print(f'❌ {f}（未找到 slug 行）')
        continue

    text_new = '---' + fm_new + '---' + body
    p.write_text(text_new, encoding='utf-8')
    print(f'✅ {f}')