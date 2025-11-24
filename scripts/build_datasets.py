#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import random
from collections import defaultdict
from typing import Any, Dict, List, Tuple
import sys

# 确保能从项目根目录导入 nlp 包
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tqdm import tqdm

from nlp.config import get_settings
from nlp.llm_client import LLMClient
from nlp.prompts import build_daily_identity_summary_prompt
from nlp.utils import read_json_or_jsonl, normalize_text, to_date_str, try_parse_json, write_jsonl, append_jsonl


def collect_items_by_date(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    date_to_items: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for it in items:
        date_str = to_date_str(str(it.get("publish_time") or ""))
        # 记录清洗后的必要字段
        date_to_items[date_str].append({
            "id": str(it.get("id") or it.get("url") or ""),
            "title": normalize_text(str(it.get("title") or "")),
            "source": normalize_text(str(it.get("source") or "未知来源")),
            "publish_time": str(it.get("publish_time") or ""),
            "content_clean": normalize_text(str(it.get("content_clean") or it.get("content_raw") or "")),
        })
    return date_to_items


def pick_contiguous_dates(date_to_items: Dict[str, List[Dict[str, Any]]], start_date: str | None, days: int) -> List[str]:
    """
    选择连续days天的日期序列（YYYY-MM-DD），若start_date为空则从数据中最大日期往前推days-1天。
    返回该区间内的所有日期（包含起止），用于逐日生成日报；注意：当天若无新闻，后续会跳过不生成样本。
    """
    from datetime import date, timedelta
    all_dates_sorted = sorted(date_to_items.keys())
    if not all_dates_sorted:
        return []
    if start_date:
        # 兼容未加引号导致的数字/其它类型
        s = start_date if isinstance(start_date, str) else str(start_date)
        if "-" in s:
            try:
                y, m, d = [int(x) for x in s.split("-")]
                start = date(y, m, d)
            except Exception:
                # 回退：取最大日期为结束日
                y, m, d = [int(x) for x in all_dates_sorted[-1].split("-")]
                end = date(y, m, d)
                start = end - timedelta(days=days - 1)
        else:
            # 无法解析为YYYY-MM-DD，回退
            y, m, d = [int(x) for x in all_dates_sorted[-1].split("-")]
            end = date(y, m, d)
            start = end - timedelta(days=days - 1)
    else:
        y, m, d = [int(x) for x in all_dates_sorted[-1].split("-")]
        end = date(y, m, d)
        start = end - timedelta(days=days - 1)
    # 构建连续序列
    seq: List[str] = []
    from datetime import timedelta as td
    for i in range(days):
        cur = start + td(days=i)
        seq.append(cur.isoformat())
    return seq


def build_daily_identity_dataset(client: LLMClient, date_to_items: Dict[str, List[Dict[str, Any]]], date_seq: List[str], identity_path: str | None = None, summaries_path: str | None = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    基于日期序列逐日聚合生成差异化总结数据：
    - 返回 identity_data: 每天两条（学生/教师）指令样本
    - 返回 daily_summaries: [{date, student_summary, teacher_summary}]
    当天无新闻则跳过。
    """
    identity_data: List[Dict[str, Any]] = []
    daily_summaries: List[Dict[str, Any]] = []
    for d in tqdm(date_seq, desc="生成按日差异化总结"):
        items = date_to_items.get(d) or []
        # 无新闻则跳过
        valid = [it for it in items if (it.get("title") or it.get("content_clean"))]
        if not valid:
            continue
        messages = build_daily_identity_summary_prompt(d, valid)
        resp = client.chat(messages)
        parsed = try_parse_json(resp)
        if not parsed or "student_summary" not in parsed or "teacher_summary" not in parsed:
            parsed = {
                "student_summary": f"【学生版】{d} 当日新闻要点（请关注截止/学分/操作步骤）。",
                "teacher_summary": f"【教师版】{d} 当日新闻要点（请关注职责/督促/关键时间）。",
            }
        student_summary = normalize_text(str(parsed.get("student_summary") or ""))
        teacher_summary = normalize_text(str(parsed.get("teacher_summary") or ""))

        # 构造输入文本：按【新闻一】【新闻二】拼接
        blocks = [f"【日期】{d}"]
        for idx, it in enumerate(valid, 1):
            blocks.append(
                f"【新闻{idx}】\n"
                f"标题：{it.get('title') or ''}\n"
                f"来源：{it.get('source') or ''}\n"
                f"发布时间：{it.get('publish_time') or ''}\n"
                f"正文：\n{it.get('content_clean') or ''}\n"
            )
        day_input = "\n".join(blocks)

        # 两条训练样本：学生/教师
        student_item = {
            "instruction": "你是一个智慧校园助手。当前用户是【学生】，请总结以下教务通知。",
            "input": day_input,
            "output": student_summary
        }
        teacher_item = {
            "instruction": "你是一个智慧校园助手。当前用户是【教师】，请总结以下教务通知。",
            "input": day_input,
            "output": teacher_summary
        }
        identity_data.append(student_item)
        identity_data.append(teacher_item)
        if identity_path:
            append_jsonl(student_item, identity_path)
            append_jsonl(teacher_item, identity_path)

        day_summary = {
            "date": d,
            "student_summary": student_summary,
            "teacher_summary": teacher_summary,
        }
        daily_summaries.append(day_summary)
        if summaries_path:
            append_jsonl(day_summary, summaries_path)
    return identity_data, daily_summaries


def group_student_briefs_by_date(summaries: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    date_to_briefs: Dict[str, List[str]] = defaultdict(list)
    for s in summaries:
        d = str(s.get("date") or "")
        st = normalize_text(str(s.get("student_summary") or ""))
        if d and st:
            # 简单地将单条summary作为一行
            date_to_briefs[d].append(st)
    return date_to_briefs


def pick_daily_windows(date_to_briefs: Dict[str, List[str]], max_windows: int, window_days: int, seed: int) -> List[List[Dict[str, str]]]:
    """
    选取若干“时间窗”（例如过去7天中选5-10条简报），用于生成QA对
    返回：每个窗是 [{'date': 'YYYY-MM-DD', 'summary': '...'}, ...]
    """
    if not date_to_briefs:
        return []
    dates_sorted = sorted(date_to_briefs.keys())
    rng = random.Random(seed)
    windows: List[List[Dict[str, str]]] = []

    # 生成所有候选窗口（以每个日期为末端，回溯window_days天）
    all_windows: List[List[Dict[str, str]]] = []
    date_index = {d: i for i, d in enumerate(dates_sorted)}
    for end_date in dates_sorted:
        end_idx = date_index[end_date]
        start_idx = max(0, end_idx - (window_days - 1))
        sub_dates = dates_sorted[start_idx:end_idx + 1]
        chunk: List[Dict[str, str]] = []
        for d in sub_dates:
            # 合并当天多条简报为一段
            brief_text = "；".join(date_to_briefs[d])[:2000]
            if brief_text:
                chunk.append({"date": d, "summary": brief_text})
        if chunk:
            all_windows.append(chunk)

    if not all_windows:
        return []

    # 随机抽取指定数量窗口
    if max_windows >= len(all_windows):
        windows = all_windows
    else:
        windows = rng.sample(all_windows, max_windows)
    return windows


def build_history_qa_pairs(client: LLMClient, windows: List[List[Dict[str, str]]]) -> List[Dict[str, Any]]:
    qa_items: List[Dict[str, Any]] = []
    for chunk in tqdm(windows, desc="生成历史记忆问答"):
        messages = build_history_qa_prompt(chunk)
        resp = client.chat(messages)
        # 解析“问题：”“回答：”
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
        if not answer:
            # 兜底
            answer = "不知道。"
        history_text_lines = [f"[{b['date']}]：{b['summary']}" for b in chunk]
        history_text = "【历史简报】：\n" + "\n".join(history_text_lines) + f"\n\n【用户问题】：{question or '（未提供）'}"
        qa_items.append({
            "instruction": "你是一个智慧校园助手。当前用户是【学生】。请根据给定的【过去一段时间的新闻简报】，回答用户的问题。如果简报中没有相关信息，请直接说不知道。",
            "input": history_text,
            "output": answer
        })
    return qa_items


def main():
    parser = argparse.ArgumentParser(description="Step2: 构建微调数据集（仅差异化总结，按连续30天逐日聚合）")
    parser.add_argument("--raw", type=str, default="/root/NLP/origin_json_data/news_data.json", help="原始数据路径,例如： /root/NLP/origin_json_data/news_data.json")
    parser.add_argument("--out-dir", type=str, default="/root/NLP/datasets", help="输出目录，默认 datasets")
    parser.add_argument("--days", type=int, default=1000, help="连续天数，默认30")
    parser.add_argument("--start-date", type=str, default=None, help="起始日期 YYYY-MM-DD；为空则自动取数据中最大日期往前推")
    parser.add_argument("--provider", type=str, default="openai", help="LLM Provider（deepseek/openai/mock），默认读取环境变量")
    parser.add_argument("--model", type=str, default="qwen-plus", help="LLM模型名，默认读取环境变量")
    parser.add_argument("--seed", type=int, default=42, help="随机种子，默认读取环境变量")
    args = parser.parse_args()

    settings = get_settings()
    seed = args.seed if args.seed is not None else settings.seed
    random.seed(seed)

    os.makedirs(args.out_dir, exist_ok=True)

    # 读取原始新闻
    items = read_json_or_jsonl(args.raw)
    if not items:
        raise SystemExit("未读取到有效的新闻数据，请检查文件格式。")

    # 按日期聚合，并选择连续days天
    date_to_items = collect_items_by_date(items)
    date_seq = pick_contiguous_dates(date_to_items, start_date=args.start_date, days=args.days)

    # 初始化LLM
    client = LLMClient(provider=args.provider, model=args.model)

    # 输出文件路径并清空旧内容
    identity_path = os.path.join(args.out_dir, "identity.jsonl")
    summaries_path = os.path.join(args.out_dir, "summaries.identity.jsonl")
    # 清空旧文件（避免重复），随后边生成边追加
    open(identity_path, "wb").close()
    open(summaries_path, "wb").close()

    # 任务一：按日差异化总结（学生/教师），边生成边写入
    identity_data, daily_summaries = build_daily_identity_dataset(client, date_to_items, date_seq, identity_path, summaries_path)

    print(f"完成。identity: {len(identity_data)}（样本数，≈ 每日2条），daily_summaries: {len(daily_summaries)}（天数）")
    print(f"identity -> {identity_path}")
    print(f"summaries -> {summaries_path}")


if __name__ == "__main__":
    main()


