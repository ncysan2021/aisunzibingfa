#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
    fm = text.split('---')[1]
    if 'type:' in fm:
        print(f'⏭  {f}（已有 type）')
        continue
    # 在 slug 行后插入 type
    new = re.sub(
        r'(slug:\s*"[^"]+"\s*\n)',
        r'\1type: "page"\n',
        text,
        count=1,
    )
    if new != text:
        p.write_text(new, encoding='utf-8')
        print(f'✅ {f}')