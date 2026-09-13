#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQS-2.0 语录升级脚本（v2，带自动校验）
读取 data/quotes.yaml（基础版）
调用 DeepSeek API 升级为 MQS-2.0 完整格式
写入 data/quotes_v2.yaml
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
- quote_dimension: 与输入一致
- quote_sub_dimension: 与输入一致（无则空字符串）
- dimension_focus: "本文只围绕XX维度展开"

【内容字段】
- original, translation, source: 与输入一致
- references: ["《孙子兵法》传世本及曹操、杜牧等历代注本"]

【SEO】
- keywords: 5-8个关键词数组

【奥运项目】（硬约束）
- olympic_sports: 至少2个奥运大项，至少1个来自冬季奥运或冷门项目
  冬季示例：短道速滑、花样滑冰、冰壶、单板滑雪、越野滑雪、冰球
  夏季示例：田径、游泳、体操、篮球、足球、羽毛球、网球、击剑、射击、柔道、拳击、举重、自行车、赛艇、皮划艇、铁人三项、跳水

【AEO/GEO 字段】
- tldr: 3点核心速览（字符串数组）
- direct_answer: 【严格】中文字符数必须在 45-58 之间（不要超过 58，不要低于 45），不使用"这""该词""该句""上述"等代词。先数一遍字数再输出。

【图片】
- cover:
    alt: 图片alt
    title: 图片title
    caption: 图片说明
    width: 1200
    height: 630

【术语】
- defined_terms: 3-5个，每个 {term, description}

【落地行动】
- howto: 4-6步，每个 {name, text}

【清单】
- itemlist: 3-7项，每个 {name, description}

【FAQ】（硬约束）
- faq: 3-4个问答，每个 {q, a}。a 必须以"结论："开头

【关联】
- related: []

【正文 Section 1-5】（每个都是 Markdown 字符串，含 H2 标题）
- sections:
    section1: 古文解析，必须含【原文事实】【传统解释】【作者分析】【现代应用】四个标签
    section2: 跨学科映射，术语首次出现用 <dfn title="...">术语</dfn>
    section3: 决策矩阵，含 {{< table caption="..." >}} ... {{< /table >}} shortcode，表格列：应用场景 | 守"正"基础 | 出"奇"策略 | ⚠️ 风险与底线
    section4: 避坑指南，至少1个具体体育失败反例
    section5: 落地行动，有序列表 4-6 步

【硬约束】（违反即FAIL）
1. 维度：只写配置的维度，多一个不行，少一个也不行
2. 奥运项目：至少2个，含1个冬季或冷门
3. FAQ：3-4个，每个答案以"结论："开头
4. direct_answer：中文字符数 40-60，无"这/该/上述"代词
5. 禁用词：赋能、抓手、闭环、内卷、躺平、破防、团结就是力量、永不放弃就能赢、只要努力就能成功
6. 场景只能是体育竞技，禁止商业、职场、战争、人生感悟
7. 不虚构《孙子兵法》原文
8. 【强制】引用古语或加引号时，一律使用中文引号「」或""（全角），绝对禁止使用英文单引号 ' 或英文双引号（YAML 转义会出问题）

只输出 JSON 对象，不要任何解释文字。"""


def count_chinese_chars(text):
    """统计中文字符数（不含标点）"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def validate_result(result):
    """校验生成结果，返回 (ok, errors)"""
    errors = []

    # direct_answer 长度
    da = result.get("direct_answer", "")
    n = count_chinese_chars(da)
    if n < 40 or n > 65:
        errors.append(f"direct_answer 中文字数 {n}，应为 40-60（允许60-65误差）")

    # direct_answer 无代词
    for w in ["这", "该词", "该句", "上述"]:
        if da.startswith(w) or f"，{w}" in da[:20]:
            errors.append(f"direct_answer 使用了代词：{w}")

    # faq 数量
    faq = result.get("faq", [])
    if len(faq) < 3 or len(faq) > 4:
        errors.append(f"faq 数量 {len(faq)}，应为 3-4")

    # faq 结论先行
    for i, item in enumerate(faq):
        if not item.get("a", "").startswith("结论："):
            errors.append(f"faq[{i}] 未以'结论：'开头")

    # 奥运项目
    sports = result.get("olympic_sports", [])
    if len(sports) < 2:
        errors.append(f"olympic_sports 数量 {len(sports)}，应 ≥ 2")

    # sections
    sections = result.get("sections", {})
    for k in ["section1", "section2", "section3", "section4", "section5"]:
        if k not in sections:
            errors.append(f"缺少 sections.{k}")

    # 单引号转义问题
    for k, v in sections.items():
        if isinstance(v, str) and "''" in v:
            errors.append(f"sections.{k} 含双单引号''，会渲染异常")

    # 禁用词
    banned = ["赋能", "抓手", "闭环", "内卷", "躺平", "破防",
              "团结就是力量", "永不放弃就能赢", "只要努力就能成功"]
    all_text = json.dumps(result, ensure_ascii=False)
    for w in banned:
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
    if failed:
        print(f"❌ 失败列表：{failed}")
        print(f"   已保存到 {FAILED_FILE}")

    print(f"💾 输出：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()