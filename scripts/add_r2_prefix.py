#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量给 content/ 下所有 index.md 的 cover.image 加 R2 前缀（若不是完整 URL）"""

import re
from pathlib import Path

R2_BASE = "https://pub-f9d6c3356fb44ce0b1e0f09cb4ddf49a.r2.dev"

count = 0
for p in Path("content").rglob("index.md"):
    text = p.read_text(encoding="utf-8")

    def repl(m):
        prefix = m.group(1)  # 前面的空白
        key = m.group(2)     # image: 
        quote = m.group(3)   # 引号
        val = m.group(4)     # 路径
        # 已经是完整 URL 就跳过
        if val.startswith(("http://", "https://")):
            return m.group(0)
        # 是绝对路径（以 / 开头）跳过
        if val.startswith("/"):
            return m.group(0)
        return f'{prefix}{key}{quote}{R2_BASE}/{val}{quote}'

    new = re.sub(
        r'^(\s*)(image:\s*)(["\'])([^"\']+)\3',
        repl,
        text,
        flags=re.MULTILINE,
    )

    if new != text:
        p.write_text(new, encoding="utf-8")
        print(f"✅ {p}")
        count += 1

print(f"\n共处理 {count} 个文件")