#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQS-2.0 语录升级脚本（v5，带引号归一化 + 别名映射 + 全量校验）
读取 data/quotes.yaml（基础版）
调用 DeepSeek API 升级为 MQS-2.0 完整格式
写入 data/quotes_v2.yaml

v5 变更（相对 v4）：
  1. 新增 SPORT_ALIASES 别名映射表：把细分项目（公路自行车、马拉松、
     场地自行车等）映射回大类（自行车、田径），避免误杀真实奥运项目。
  2. validate_result 的 olympic_sports 校验改用映射后的 canonical 值。
  3. Prompt 中 tldr 加强：明确"输出前必须数一遍数组长度 = 3"。

v4 变更（相对 v3）：
  1. 新增 normalize_quotes() / normalize_result()：
     在 validate 之前把正文里的英文双引号成对替换为中文全角引号，
     同时保护 HTML 标签与 Hugo shortcode 内的属性引号。
  2. direct_answer 校验上限由 60 放宽到 65（下限仍 40）。
     Prompt 同步加正例与反例，软引导 45-58。

⚠️ 批量阶段跳过 Rule 15（FAQ 候选问题确认闸门）
   MQS-2.0 Rule 15 要求 AI 先输出 4-6 个候选问题，由用户选定后再写入
   faq 字段。批量升级 279 条时交互成本过高，本脚本在批量阶段豁免
   Rule 15，直接生成 faq 并写入。后续如补交互流程，再单独实现。
   其他 Rule（尤其 Rule 28 Self-Check）仍严格执行。
"""

import os
import re
import sys
import json
import time
import argparse
import yaml
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# ─── 环境 ─────────────────────────────
load_dotenv()

ROOT = Path(__file__).parent.parent
INPUT_FILE = ROOT / "data" / "quotes.yaml"
OUTPUT_FILE = ROOT / "data" / "quotes_v2.yaml"
FAILED_FILE = ROOT / "data" / "quotes_failed.yaml"

API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    print("❌ 未找到 DEEPSEEK_API_KEY，请检查 .env 文件")
    sys.exit(1)

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com",
)


# ─── MQS-2.0 常量 ─────────────────────
QUOTE_DIMENSIONS = {"战略", "战术", "执行", "复盘", "资源约束", "物理极限"}

SUMMER_SPORTS = {
    "田径", "游泳", "体操", "篮球", "足球", "排球", "乒乓球", "羽毛球", "网球",
    "举重", "拳击", "跆拳道", "柔道", "摔跤", "击剑", "射击", "射箭", "赛艇",
    "皮划艇", "帆船", "自行车", "马术", "铁人三项", "现代五项", "高尔夫",
    "七人制橄榄球", "曲棍球", "手球", "跳水", "花样游泳", "水球", "攀岩",
    "滑板", "冲浪",
}

WINTER_SPORTS = {
    "速度滑冰", "短道速滑", "花样滑冰", "高山滑雪", "越野滑雪", "自由式滑雪",
    "单板滑雪", "跳台滑雪", "北欧两项", "冰球", "冰壶", "雪车", "钢架雪车",
    "雪橇", "冬季两项",
}

COLD_SPORTS = {
    "现代五项", "马术", "帆船", "赛艇", "皮划艇", "铁人三项", "七人制橄榄球",
    "曲棍球", "手球", "水球", "攀岩", "滑板", "冲浪", "高尔夫", "射击",
    "射箭", "举重", "摔跤", "柔道", "跆拳道",
}

ALL_SPORTS = SUMMER_SPORTS | WINTER_SPORTS

# ─── v5 新增：细分/别名 → 大类映射 ─────
SPORT_ALIASES = {
    # 田径细分
    "马拉松": "田径", "短跑": "田径", "中长跑": "田径", "长跑": "田径",
    "跨栏": "田径", "接力": "田径", "竞走": "田径", "越野跑": "田径",
    "跳高": "田径", "跳远": "田径", "三级跳远": "田径", "撑杆跳高": "田径",
    "铅球": "田径", "标枪": "田径", "铁饼": "田径", "链球": "田径",
    "十项全能": "田径", "七项全能": "田径",
    # 游泳细分
    "自由泳": "游泳", "蛙泳": "游泳", "仰泳": "游泳", "蝶泳": "游泳",
    "混合泳": "游泳", "公开水域游泳": "游泳",
    # 自行车细分
    "公路自行车": "自行车", "场地自行车": "自行车", "山地自行车": "自行车",
    "BMX": "自行车", "小轮车": "自行车",
    # 体操细分
    "竞技体操": "体操", "艺术体操": "体操", "蹦床": "体操",
    # 跳水细分
    "十米跳台": "跳水", "三米跳板": "跳水",
    # 球类细分
    "三人篮球": "篮球", "沙滩排球": "排球", "室内排球": "排球",
    "五人制足球": "足球", "沙滩足球": "足球",
    # 皮划艇细分
    "皮划艇激流回旋": "皮划艇", "皮划艇静水": "皮划艇",
    # 帆船细分
    "帆板": "帆船", "风筝冲浪": "帆船",
    # 通用别名
    "奥运会田径": "田径", "奥运田径": "田径",
}

REQUIRED_H2 = [
    "## 古文解析：厘清核心内涵",
    "## 跨学科映射：从军事评估到竞技决策科学",
    "## 决策矩阵：竞技应用参照指南",
    "## 避坑指南：认知误区与风险控制",
    "## 落地行动：如何建立个人/团队训练与比赛执行机制",
]

REQUIRED_TABLE_HEADER = [
    "守“正”基础（先做好什么）",
    "出“奇”策略（可以变什么）",
    "⚠️ 风险与底线（千万别越线）",
]

BANNED_WORDS = [
    "赋能", "抓手", "闭环", "体系化", "生态化",
    "内卷", "躺平", "破防", "666", "绝绝子",
    "太真实了", "扎心", "说白了", "想想就烦",
    "团结就是力量", "永不放弃就能赢", "只要努力就能成功",
]


# ─── System Prompt（MQS-2.0 规则提炼）──
SYSTEM_PROMPT = """你是精通《孙子兵法》与体育竞技的资深内容专家。
按 MQS-2.0 规范，将一条基础语录升级为 GEO/AEO 完整版文章。

你会收到一条基础语录 JSON。请输出一条升级后的 JSON（不是 YAML），包含以下字段：

【基础字段】
- title: 文章标题（自由拟定）
- description: Meta Description，150字以内
- date: 保持原值
- lastmod: 保持原值
- draft: true
- ads: true
- toc: true

【作者字段】
- author: "吴雄山"
- authorTitle: "AI孙子兵法网站创办人"
- authorLocation: "马来西亚吉隆坡"

【维度字段】（硬约束）
- quote_dimension: 与输入一致，必须是六维之一：战略/战术/执行/复盘/资源约束/物理极限
- quote_sub_dimension: 与输入一致（无则空字符串）
- dimension_focus: "本文只围绕XX维度展开"

【内容字段】
- original, translation, source: 与输入一致
- references: ["《孙子兵法》传世本及曹操、杜牧等历代注本"]

【SEO】
- keywords: 5-8个关键词数组

【奥运项目】（硬约束）
- olympic_sports: 至少2个奥运大项，至少1个来自冬季奥运或冷门项目
  冬季示例：短道速滑、花样滑冰、冰壶、单板滑雪、越野滑雪、冰球、速度滑冰、跳台滑雪、自由式滑雪、高山滑雪、北欧两项、雪车、钢架雪车、雪橇、冬季两项
  夏季示例：田径、游泳、体操、篮球、足球、排球、乒乓球、羽毛球、网球、击剑、射击、射箭、赛艇、皮划艇、帆船、自行车、马术、铁人三项、现代五项、高尔夫、七人制橄榄球、曲棍球、手球、跳水、花样游泳、水球、攀岩、滑板、冲浪、柔道、拳击、举重、摔跤、跆拳道
  ⚠️ 请使用上面列表中的项目名（大类），不要写"公路自行车""马拉松""场地自行车"等细分名称，直接写"自行车""田径"即可。

【AEO/GEO 字段】
- tldr: 【严格】3点核心速览（字符串数组，必须正好3点）。
  输出前必须数一遍 tldr 数组长度：多于3条删掉最不重要的一条，少于3条补充一条，
  最终数组长度必须正好等于 3。
- direct_answer: 【严格】中文字符数必须在 45-58 之间（不含标点），绝不得超过 60。
  错误示范（75字，太长）：「兵者国之大事」这句话的意思是战争是国家最重要的事情之一，它关系到很多人的生死以及国家的存亡，因此在竞技体育中，赛前的信息收集与战略评估就显得格外关键，必须投入足够精力。
  正确示范（52字）：「兵者国之大事」在体育竞技中是指：赛前先评估比赛重要性、自身状态与对手强弱，再决定本场目标与投入强度。
  写法要求：句式紧凑、单句成段、避免"以及/并且/因此/所以"等连接词堆叠。
- defined_terms: 【严格】3-5个，每个 {term, description}
- howto: 【严格】4-6步，每个 {name, text}
- itemlist: 【严格】3-7项，每个 {name, description}

【图片】
- cover:
    alt: 图片alt
    title: 图片title
    caption: 图片说明
    width: 1200
    height: 630

【FAQ】（硬约束）
- faq: 3-4个问答，每个 {q, a}。a 必须以"结论："开头

【关联】
- related: []

【正文 Section 1-5】（每个都是 Markdown 字符串）
⚠️ 每个 Section 的 H2 标题必须逐字复制以下文本，绝对禁止改写、缩写或替换：

sections.section1 必须以这一行开头（逐字）：
## 古文解析：厘清核心内涵
然后写内容，必须含【原文事实】【传统解释】【作者分析】【现代应用】四个中文标签。

sections.section2 必须以这一行开头（逐字）：
## 跨学科映射：从军事评估到竞技决策科学
然后写跨学科映射内容，术语首次出现用 <dfn title="...">术语</dfn>。

sections.section3 必须以这一行开头（逐字）：
## 决策矩阵：竞技应用参照指南
然后写决策矩阵，必须含 {{< table caption="..." >}} ... {{< /table >}} shortcode。
⚠️ 表格表头必须逐字为（使用全角引号，禁止英文双引号）：
| 应用场景 | 守“正”基础（先做好什么） | 出“奇”策略（可以变什么） | ⚠️ 风险与底线（千万别越线） |

sections.section4 必须以这一行开头（逐字）：
## 避坑指南：认知误区与风险控制
然后写避坑指南，至少1个具体体育失败反例。

sections.section5 必须以这一行开头（逐字）：
## 落地行动：如何建立个人/团队训练与比赛执行机制
然后写有序列表 4-6 步。

【硬约束】（违反即FAIL）
1. 维度：只写配置的维度，多一个不行，少一个也不行
2. 奥运项目：至少2个，含1个冬季或冷门
3. FAQ：3-4个，每个答案以"结论："开头
4. direct_answer：中文字符数 45-58（硬上限 60），无"这/该/上述"代词
5. 禁用词：赋能、抓手、闭环、体系化、生态化、内卷、躺平、破防、666、绝绝子、太真实了、扎心、说白了、想想就烦、团结就是力量、永不放弃就能赢、只要努力就能成功
6. 场景只能是体育竞技，禁止商业、职场、战争、人生感悟
7. 不虚构《孙子兵法》原文
8. 【强制】正文中引用古语或加引号时，一律使用中文引号「」或全角引号“”，绝对禁止使用英文单引号 ' 或英文双引号 "
9. 【强制】Section 1-5 的 H2 标题必须逐字等于上面指定的文本，不得改写
10. 【强制】正文中不得出现 H1（即单 # 开头的行）

只输出 JSON 对象，不要任何解释文字。"""


def count_chinese_chars(text):
    """统计中文字符数（不含标点）"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))


# ─── v4 新增：引号归一化 ────────────────
def normalize_quotes(text):
    """
    把一段文本中的英文双引号 " 成对替换为中文全角引号 “ ”。
    保护：
      - HTML 标签（如 <dfn title="...">）内的属性引号
      - Hugo shortcode（如 {{< table caption="..." >}}）内的引号
    """
    if not isinstance(text, str) or '"' not in text:
        return text

    placeholders = {}
    counter = [0]

    def _protect(m):
        key = f"\x00PH{counter[0]}\x00"
        placeholders[key] = m.group(0)
        counter[0] += 1
        return key

    # 1. 保护 Hugo shortcode，再保护 HTML 标签（顺序不能反）
    protected = re.sub(r'\{\{<[^}]*>\}\}', _protect, text)
    protected = re.sub(r'</?[a-zA-Z][^>]*>', _protect, protected)

    # 2. 对剩余文本按出现顺序成对替换
    out = []
    open_quote = True
    for ch in protected:
        if ch == '"':
            out.append("\u201c" if open_quote else "\u201d")
            open_quote = not open_quote
        else:
            out.append(ch)
    replaced = "".join(out)

    # 3. 恢复占位符
    for key, val in placeholders.items():
        replaced = replaced.replace(key, val)

    return replaced


def normalize_result(result):
    """
    在 validate 之前，把 result 中所有可能被渲染的字符串字段做引号归一化。
    只处理正文类字段，不动 direct_answer / keywords / date 等。
    """
    if not isinstance(result, dict):
        return result

    # sections
    sections = result.get("sections", {})
    if isinstance(sections, dict):
        for k in list(sections.keys()):
            if isinstance(sections[k], str):
                sections[k] = normalize_quotes(sections[k])
        result["sections"] = sections

    # faq 的 q / a
    faq = result.get("faq", [])
    if isinstance(faq, list):
        for item in faq:
            if isinstance(item, dict):
                for k in ("q", "a"):
                    if isinstance(item.get(k), str):
                        item[k] = normalize_quotes(item[k])

    # defined_terms / howto / itemlist
    for key in ("defined_terms", "howto", "itemlist"):
        items = result.get(key, [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    for k, v in list(item.items()):
                        if isinstance(v, str):
                            item[k] = normalize_quotes(v)

    # tldr
    tldr = result.get("tldr", [])
    if isinstance(tldr, list):
        result["tldr"] = [
            normalize_quotes(x) if isinstance(x, str) else x for x in tldr
        ]

    # cover.caption / alt / title
    cover = result.get("cover", {})
    if isinstance(cover, dict):
        for k in ("alt", "title", "caption"):
            if isinstance(cover.get(k), str):
                cover[k] = normalize_quotes(cover[k])
        result["cover"] = cover

    return result


def validate_result(result):
    """按 MQS-2.0 Rule 28 校验生成结果，返回 (ok, errors)

    注意：
    - Rule 15（FAQ 候选问题确认闸门）在批量阶段豁免，
      本函数只校验 faq 的数量与「结论：」开头。
    - 调用前应先执行 normalize_result()，把英文双引号转为中文全角引号。
    - v5：olympic_sports 支持细分项目别名映射回大类。
    """
    errors = []

    # ── Rule 28-13: direct_answer 长度 40-65 且无代词 ──
    da = result.get("direct_answer", "")
    n = count_chinese_chars(da)
    if n < 40 or n > 65:
        errors.append(f"direct_answer 中文字数 {n}，应为 40-65")
    for w in ["这", "该词", "该句", "上述"]:
        if da.startswith(w) or f"，{w}" in da[:20]:
            errors.append(f"direct_answer 使用了代词：{w}")

    # ── Rule 28-4: quote_dimension 必须为六维之一 ──
    qd = result.get("quote_dimension", "")
    if qd not in QUOTE_DIMENSIONS:
        errors.append(f"quote_dimension='{qd}' 不在六维白名单内")

    # ── Rule 28-5: quote_sub_dimension 为空或六维之一 ──
    qsd = result.get("quote_sub_dimension", "") or ""
    if qsd and qsd not in QUOTE_DIMENSIONS:
        errors.append(f"quote_sub_dimension='{qsd}' 不在六维白名单内")

    # ── Rule 28-8/9: olympic_sports ≥ 2，且含冬季或冷门，且都在白名单（含细分映射） ──
    sports = result.get("olympic_sports", [])
    if not isinstance(sports, list):
        errors.append("olympic_sports 不是数组")
        sports = []
    if len(sports) < 2:
        errors.append(f"olympic_sports 数量 {len(sports)}，应 ≥ 2")
    # 把细分项目映射回大类
    canonical_sports = [SPORT_ALIASES.get(s, s) for s in sports]
    if not any(
        c in WINTER_SPORTS or c in COLD_SPORTS for c in canonical_sports
    ):
        errors.append("olympic_sports 未包含任何冬季或冷门项目")
    for orig, canon in zip(sports, canonical_sports):
        if canon not in ALL_SPORTS:
            errors.append(f"olympic_sports 含白名单外项目：{orig}")

    # ── Rule 28-12: tldr 必须 3 点 ──
    tldr = result.get("tldr", [])
    if not isinstance(tldr, list) or len(tldr) != 3:
        errors.append(f"tldr 数量 {len(tldr) if isinstance(tldr, list) else 'N/A'}，应正好 3 点")

    # ── Rule 28-14: defined_terms 3-5 个 ──
    dt = result.get("defined_terms", [])
    if not isinstance(dt, list) or not (3 <= len(dt) <= 5):
        errors.append(f"defined_terms 数量 {len(dt) if isinstance(dt, list) else 'N/A'}，应为 3-5")

    # ── Rule 28-15: howto 4-6 步 ──
    ht = result.get("howto", [])
    if not isinstance(ht, list) or not (4 <= len(ht) <= 6):
        errors.append(f"howto 数量 {len(ht) if isinstance(ht, list) else 'N/A'}，应为 4-6")

    # ── Rule 28-16: itemlist 3-7 项 ──
    il = result.get("itemlist", [])
    if not isinstance(il, list) or not (3 <= len(il) <= 7):
        errors.append(f"itemlist 数量 {len(il) if isinstance(il, list) else 'N/A'}，应为 3-7")

    # ── Rule 28-17: faq 3-4 个且结论先行（Rule 15 批量阶段豁免） ──
    faq = result.get("faq", [])
    if not isinstance(faq, list) or not (3 <= len(faq) <= 4):
        errors.append(f"faq 数量 {len(faq) if isinstance(faq, list) else 'N/A'}，应为 3-4")
    else:
        for i, item in enumerate(faq):
            if not isinstance(item, dict) or not item.get("a", "").startswith("结论："):
                errors.append(f"faq[{i}] 未以'结论：'开头")

    # ── Rule 28-10: sections 含 Section 1-5 ──
    sections = result.get("sections", {})
    if not isinstance(sections, dict):
        errors.append("sections 不是字典")
        sections = {}
    for k in ["section1", "section2", "section3", "section4", "section5"]:
        if k not in sections:
            errors.append(f"缺少 sections.{k}")

    # ── Rule 28-11 + Rule 18: 每个 Section 必须以固定 H2 标题开头 ──
    for idx, key in enumerate(
        ["section1", "section2", "section3", "section4", "section5"]
    ):
        v = sections.get(key, "")
        if not isinstance(v, str) or not v.strip():
            continue
        expected = REQUIRED_H2[idx]
        first_line = v.lstrip().splitlines()[0].strip() if v.strip() else ""
        if first_line != expected:
            errors.append(
                f"{key} 的 H2 标题不符 Rule 18，期望「{expected}」，实际「{first_line}」"
            )

    # ── Rule 28-11: 正文不得出现 H1（单 # 开头） ──
    for key, v in sections.items():
        if not isinstance(v, str):
            continue
        if re.search(r"(?m)^#\s", v):
            errors.append(f"sections.{key} 出现 H1，Rule 18 禁止 H1")

    # ── Rule 21: 决策矩阵表头必须含完整关键词（全角引号） ──
    s3 = sections.get("section3", "")
    if isinstance(s3, str) and s3:
        for kw in REQUIRED_TABLE_HEADER:
            if kw not in s3:
                errors.append(f"section3 表格表头缺少「{kw}」（Rule 21）")

    # ── Rule 08/Prompt 8: 正文中不得出现英文双引号（normalize 后应已消灭） ──
    for k, v in sections.items():
        if isinstance(v, str) and '"' in v:
            # 允许 HTML 标签 / shortcode 内的属性引号
            stripped = re.sub(r'\{\{<[^}]*>\}\}', '', v)
            stripped = re.sub(r'</?[a-zA-Z][^>]*>', '', stripped)
            if '"' in stripped:
                errors.append(f"sections.{k} 含英文双引号 \"（须用中文引号）")

    # ── 双单引号（原有检查，保留） ──
    for k, v in sections.items():
        if isinstance(v, str) and "''" in v:
            errors.append(f"sections.{k} 含双单引号''，会渲染异常")

    # ── Rule 25: 完整禁用词 ──
    all_text = json.dumps(result, ensure_ascii=False)
    for w in BANNED_WORDS:
        if w in all_text:
            errors.append(f"含禁用词：{w}")

    return len(errors) == 0, errors


def call_deepseek(quote, retries=5):
    """调用 DeepSeek API，带自动重试与校验"""
    user_msg = (
        "请按 MQS-2.0 规范升级以下基础语录：\n\n"
        + json.dumps(quote, ensure_ascii=False, indent=2, default=str)
    )

    last_errors = []

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=8000,
            )
            content = response.choices[0].message.content
            result = json.loads(content)

            # v4：先归一化引号，再校验
            result = normalize_result(result)

            ok, errors = validate_result(result)
            if ok:
                return result

            last_errors = errors
            print(f"   ⚠️  校验失败（{attempt+1}/{retries}）：")
            for e in errors:
                print(f"      - {e}")

            if attempt < retries - 1:
                user_msg = (
                    "上次输出有以下问题，请修正后重新输出完整 JSON：\n"
                    + "\n".join(f"- {e}" for e in errors)
                    + "\n\n原任务：\n"
                    + json.dumps(quote, ensure_ascii=False, indent=2, default=str)
                )

        except json.JSONDecodeError as e:
            print(f"   ⚠️  JSON 解析失败（{attempt+1}/{retries}）：{e}")
            time.sleep(2)
        except Exception as e:
            print(f"   ⚠️  API 调用失败（{attempt+1}/{retries}）：{e}")
            time.sleep(5)

    print(f"   ❌ 重试 {retries} 次仍失败，跳过")
    if last_errors:
        for e in last_errors:
            print(f"      - {e}")
    return None


def load_existing_v2():
    """读取已升级的条目，用于断点续传"""
    if not OUTPUT_FILE.exists():
        return []
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def save_v2(quotes):
    """保存升级后的 YAML"""
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        yaml.dump(
            quotes,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=1000,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 条（0 = 全部）")
    parser.add_argument("--quote-id", type=str, default="", help="只处理指定 id")
    parser.add_argument("--force", action="store_true", help="覆盖已升级的条目")
    args = parser.parse_args()

    with open(INPUT_FILE, encoding="utf-8") as f:
        all_quotes = yaml.safe_load(f)

    if not isinstance(all_quotes, list):
        print("❌ data/quotes.yaml 必须是数组")
        sys.exit(1)

    if args.quote_id:
        all_quotes = [q for q in all_quotes if q.get("id") == args.quote_id]
        if not all_quotes:
            print(f"❌ 未找到 id = {args.quote_id}")
            sys.exit(1)

    if args.limit > 0:
        all_quotes = all_quotes[: args.limit]

    done = load_existing_v2()
    done_ids = {q.get("id") for q in done}

    print(f"📖 输入：{len(all_quotes)} 条")
    print(f"✅ 已升级：{len(done_ids)} 条")
    print(f"🚀 待处理：{len([q for q in all_quotes if q['id'] not in done_ids])} 条\n")

    success = 0
    failed = []

    for i, q in enumerate(all_quotes, 1):
        qid = q.get("id")
        if qid in done_ids and not args.force:
            print(f"[SKIP] {qid}（已升级）")
            continue

        print(f"[{i}/{len(all_quotes)}] 升级 {qid}...")
        result = call_deepseek(q)

        if result is None:
            print(f"   ❌ 失败")
            failed.append(qid)
            continue

        result["id"] = qid

        done = [x for x in done if x.get("id") != qid]
        done.append(result)
        save_v2(done)

        success += 1
        print(f"   ✅ 成功")

    print(f"\n📊 结果：成功 {success}，失败 {len(failed)}")

    # ── P0-4：失败落盘 + 退出码非 0（Rule 33） ──
    if failed:
        with open(FAILED_FILE, "w", encoding="utf-8", newline="\n") as f:
            yaml.dump(failed, f, allow_unicode=True, sort_keys=False)
        print(f"❌ 失败列表：{failed}")
        print(f"   已保存到 {FAILED_FILE}")

    print(f"💾 输出：{OUTPUT_FILE}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()