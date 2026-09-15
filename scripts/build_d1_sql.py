#!/usr/bin/env python3
"""
build_d1_sql.py — 读 CSV 题库，生成可被 wrangler d1 execute 执行的 SQL。

用法（在项目根目录运行）：
    python scripts/build_d1_sql.py

默认：
    输入：scripts/questions.csv
    输出：sql/0002_seed.sql
"""
import csv
import sys
from pathlib import Path

# 项目根目录 = 本脚本的上两级
ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "scripts" / "questions.csv"
OUTPUT = ROOT / "sql" / "0002_seed.sql"

REQUIRED_COLS = ["id", "topic", "question", "A", "B", "C", "D", "answer", "explanation"]
VALID_ANSWERS = {"A", "B", "C", "D"}


def sql_str(s):
    """把 Python 字符串转义成 SQL 字面量（含引号）。"""
    if s is None:
        s = ""
    return "'" + str(s).replace("'", "''") + "'"


def main():
    if not INPUT.exists():
        print(f"[错误] 找不到 CSV：{INPUT}", file=sys.stderr)
        sys.exit(1)

    rows = []
    seen_ids = set()

    # utf-8-sig 能自动去掉 Excel / 记事本保存时可能带的 BOM
    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        # 校验列名
        missing = [c for c in REQUIRED_COLS if c not in reader.fieldnames]
        if missing:
            print(f"[错误] CSV 缺少列：{missing}", file=sys.stderr)
            print(f"       实际列：{reader.fieldnames}", file=sys.stderr)
            sys.exit(1)

        for lineno, row in enumerate(reader, start=2):
            # 去掉每个字段首尾空白
            row = {k: (v.strip() if v else "") for k, v in row.items()}

            # 跳过空行
            if not any(row.values()):
                continue

            # 校验 id
            raw_id = row["id"]
            if not raw_id.isdigit():
                print(f"[错误] 第 {lineno} 行 id 不是数字：{raw_id!r}", file=sys.stderr)
                sys.exit(1)
            qid = int(raw_id)
            if qid in seen_ids:
                print(f"[错误] 第 {lineno} 行 id 重复：{qid}", file=sys.stderr)
                sys.exit(1)
            seen_ids.add(qid)

            # 校验 answer
            ans = row["answer"].upper()
            if ans not in VALID_ANSWERS:
                print(
                    f"[错误] 第 {lineno} 行 answer 非法：{row['answer']!r}（应为 A/B/C/D）",
                    file=sys.stderr,
                )
                sys.exit(1)

            # 校验必填
            for col in ("question", "A", "B", "C", "D"):
                if not row[col]:
                    print(f"[错误] 第 {lineno} 行 {col} 为空", file=sys.stderr)
                    sys.exit(1)

            rows.append({
                "id": qid,
                "topic": row["topic"],
                "question": row["question"],
                "a": row["A"],
                "b": row["B"],
                "c": row["C"],
                "d": row["D"],
                "answer": ans,
                "explanation": row["explanation"],
            })

    if not rows:
        print("[错误] CSV 里没有任何数据行", file=sys.stderr)
        sys.exit(1)

    # 生成 SQL
    lines = []
    lines.append("-- 自动生成，请勿手动编辑")
    lines.append("-- 源文件：scripts/questions.csv")
    lines.append(f"-- 题目数：{len(rows)}")
    lines.append("")
    lines.append("DELETE FROM questions;")
    lines.append("")

    for r in rows:
        lines.append(
            "INSERT INTO questions (id, topic, question, option_a, option_b, option_c, option_d, answer, explanation) VALUES ("
            f"{r['id']}, "
            f"{sql_str(r['topic'])}, "
            f"{sql_str(r['question'])}, "
            f"{sql_str(r['a'])}, "
            f"{sql_str(r['b'])}, "
            f"{sql_str(r['c'])}, "
            f"{sql_str(r['d'])}, "
            f"{sql_str(r['answer'])}, "
            f"{sql_str(r['explanation'])}"
            ");"
        )

    lines.append("")
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] 已生成：{OUTPUT}")
    print(f"     共 {len(rows)} 题")


if __name__ == "__main__":
    main()