#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删掉 6 个静态页 Front Matter 里的 type: "page" 行"""

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

    # 删除 type: "page" 行（含引号或不含）
    fm_new = re.sub(r'^type:\s*["\']?page["\']?\s*\n', '', fm, flags=re.MULTILINE)

    if fm_new == fm:
        print(f'⏭  {f}（无 type: page）')
        continue

    text_new = '---' + fm_new + '---' + body
    p.write_text(text_new, encoding='utf-8')
    print(f'✅ {f}')