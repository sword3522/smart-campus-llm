#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta, datetime
from typing import Any, Dict, List

# 确保能从项目根目录导入 nlp 包
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tqdm import tqdm

from nlp.llm_client import LLMClient
from nlp.prompts import build_history_qa_prompt_days
from nlp.utils import read_json_or_jsonl_any, append_jsonl


def parse_date_yyyy_mm_dd(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def build_date_index(summaries: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    将 summaries.identity.jsonl 中的 {date, student_summary} 索引为 {date_str: summary}
    """
    index: Dict[str, str] = {}
    for it in summaries:
        d = str(it.get("date") or "")
        s = str(it.get("student_summary") or "")
        if d and s:
            index[d] = s
    return index


def collect_window(index: Dict[str, str], end_date: date, days: int) -> List[Dict[str, str]]:
    """
    以 end_date 为“窗口末端”，向前回溯 days 天（含 end_date），收集存在的简报。
    返回按日期升序的 [{date, summary}]
    """
    start = end_date - timedelta(days=days - 1)
    out: List[Dict[str, str]] = []
    cur = start
    while cur <= end_date:
        dstr = cur.isoformat()
        if dstr in index:
            out.append({"date": dstr, "summary": index[dstr]})
        cur += timedelta(days=1)
    return out


def main():
    parser = argparse.ArgumentParser(description="从 summaries.identity.jsonl 构建历史记忆问答（History-Based QA）数据集")
    parser.add_argument("--summaries", type=str, default="/root/NLP/datasets/summaries.identity.jsonl", help="按日学生/教师汇总文件路径")
    parser.add_argument("--out", type=str, default="/root/NLP/datasets/history_qa.jsonl", help="输出的历史QA数据集文件路径")
    parser.add_argument("--days", type=int, default=7, help="窗口天数，默认7（向前连续N天，含结束日）")
    parser.add_argument("--min-lines", type=int, default=1, help="一个窗口中至少包含多少天的简报才生成样本，默认1")
    parser.add_argument("--provider", type=str, default="openai", help="LLM Provider（deepseek/openai/mock）")
    parser.add_argument("--model", type=str, default="qwen-plus", help="LLM模型名")
    args = parser.parse_args()

    # 读取 summaries.identity.jsonl
    summaries = read_json_or_jsonl_any(args.summaries)
    if not summaries:
        raise SystemExit("未读取到 summaries.identity.jsonl 的有效内容。请先运行差异化总结脚本生成该文件。")

    # 准备索引与日期序列（仅使用有学生版简报的日期）
    index = build_date_index(summaries)
    dates: List[date] = []
    for it in summaries:
        dstr = str(it.get("date") or "")
        d = parse_date_yyyy_mm_dd(dstr)
        if d and (dstr in index):
            dates.append(d)
    # 去重并排序
    dates = sorted(list({d for d in dates}))

    if not dates:
        raise SystemExit("未找到可用的日期。")

    client = LLMClient(provider=args.provider, model=args.model)
    # 清空旧文件，随后逐条追加写入
    open(args.out, "wb").close()
    total = 0

    for end_day in tqdm(dates, desc="生成历史QA（滑动窗口）"):
        window = collect_window(index, end_day, args.days)
        if len(window) < args.min_lines:
            continue
        messages = build_history_qa_prompt_days(window, args.days)
        resp = client.chat(messages)

        # 解析“问题/回答”
        question = ""
        answer = ""
        for line in resp.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("问题："):
                question = line.replace("问题：", "").strip()
            elif line.startswith("回答："):
                answer = line.replace("回答：", "").strip()
        if not question:
            question = "（未提供）"
        if not answer:
            answer = "最近没有该类新闻/通知，不知道。"

        # 组装输入文本
        lines = [f"[{b['date']}]：{b['summary']}" for b in window]
        history_text = "【历史简报】：\n" + "\n".join(lines) + f"\n\n【用户问题】：{question}"

        item = {
            "instruction": "你是一个智慧校园助手。当前用户是【学生】。请根据给定的【过去一段时间的新闻简报】，回答用户的问题。如果简报中没有相关信息，请直接说：最近没有该类新闻/通知，不知道。",
            "input": history_text,
            "output": answer
        }
        append_jsonl(item, args.out)
        total += 1

    if total == 0:
        raise SystemExit("未生成任何历史QA样本，请检查 --days 与数据覆盖范围。")

    print(f"已生成历史QA样本 {total} 条 -> {args.out}")


if __name__ == "__main__":
    main()


