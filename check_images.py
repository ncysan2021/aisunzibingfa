import re
import sys
from pathlib import Path

TARGET = "img.aisunzibingfa.com"
ROOT = Path("content")

# 匹配三类图片引用
PATTERNS = [
    ("markdown",  re.compile(r'!\[[^\]]*\]\(([^)\s]+)')),
    ("html",      re.compile(r'<img[^>]*\ssrc=["\']([^"\']+)["\']')),
    ("cover",     re.compile(r'^\s*image:\s*["\']?([^"\'\s]+)["\']?\s*$', re.MULTILINE)),
]

def is_bad(url: str) -> bool:
    """返回 True 表示这个 URL 不在目标域名下"""
    if not url:
        return False
    # 只检查 http(s) 开头，或根路径 /
    if url.startswith(("http://", "https://")):
        return TARGET not in url
    if url.startswith("/"):
        # 本地绝对路径，通常没问题，跳过
        return False
    # 相对路径，交给 Hugo 处理，跳过
    return False

def scan(md_file: Path):
    text = md_file.read_text(encoding="utf-8")
    hits = []
    for label, pat in PATTERNS:
        for m in pat.finditer(text):
            url = m.group(1).strip()
            if is_bad(url):
                hits.append((label, url))
    return hits

def main():
    if not ROOT.exists():
        print(f"❌ 找不到 {ROOT.resolve()}")
        sys.exit(1)

    total_files = 0
    total_bad = 0
    results = []

    for md in ROOT.rglob("*.md"):
        total_files += 1
        hits = scan(md)
        if hits:
            results.append((md, hits))
            total_bad += len(hits)

    if not results:
        print(f"✅ 扫描了 {total_files} 个 .md 文件，全部图片 URL 都在 {TARGET}")
        return

    print(f"⚠️  扫描了 {total_files} 个 .md 文件，发现 {total_bad} 个非 {TARGET} 的图片 URL：\n")
    for md, hits in results:
        print(f"📄 {md}")
        for label, url in hits:
            print(f"   [{label}] {url}")
        print()

    print(f"共 {len(results)} 个文件受影响。")

if __name__ == "__main__":
    main()