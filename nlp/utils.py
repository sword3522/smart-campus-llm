from __future__ import annotations

import datetime as dt
import json
import random
import re
from typing import Any, Dict, Iterable, List, Tuple

import orjson


def try_parse_json(text: str) -> Dict[str, Any] | None:
    # 先尝试完整解析
    try:
        return orjson.loads(text)
    except Exception:
        pass
    # 尝试提取第一个花括号JSON片段
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        snippet = match.group(0)
        try:
            return orjson.loads(snippet)
        except Exception:
            return None
    return None


def read_json_or_jsonl(path: str) -> List[Dict[str, Any]]:
    """
    兼容两种格式：
    - 纯JSON数组
    - JSONL（每行一个对象）
    仅保留含有新闻关键字段的对象（需要 'title' 或 'content_clean'），用于原始新闻数据读取。
    """
    with open(path, "rb") as f:
        data = f.read()
    text = data.decode("utf-8", errors="ignore").strip()
    items: List[Dict[str, Any]] = []
    if text.startswith("["):
        try:
            items = orjson.loads(text)
        except Exception:
            # 回退标准json解析
            items = json.loads(text)
    else:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(orjson.loads(line))
            except Exception:
                try:
                    items.append(json.loads(line))
                except Exception:
                    # 跳过无法解析的行
                    continue
    # 过滤无效项
    valid = []
    for it in items:
        if isinstance(it, dict) and ("title" in it or "content_clean" in it):
            valid.append(it)
    return valid


def read_json_or_jsonl_any(path: str) -> List[Dict[str, Any]]:
    """
    与 read_json_or_jsonl 类似，但不做字段过滤。
    适用于读取诸如 summaries.identity.jsonl（仅含 date/student_summary 等）的通用数据。
    """
    with open(path, "rb") as f:
        data = f.read()
    text = data.decode("utf-8", errors="ignore").strip()
    items: List[Dict[str, Any]] = []
    if text.startswith("["):
        try:
            items = orjson.loads(text)
        except Exception:
            items = json.loads(text)
    else:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(orjson.loads(line))
            except Exception:
                try:
                    items.append(json.loads(line))
                except Exception:
                    continue
    # 仅保留 dict
    return [it for it in items if isinstance(it, dict)]


def normalize_text(s: str | None) -> str:
    if not s:
        return ""
    # 合并多余空白
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = s.strip()
    return s


def to_date_str(dt_str: str | None) -> str:
    if not dt_str:
        return ""
    # 常见时间格式解析
    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    for fmt in candidates:
        try:
            d = dt.datetime.strptime(dt_str, fmt)
            return d.date().isoformat()
        except Exception:
            continue
    # 兜底：只取日期部分
    m = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", dt_str)
    if m:
        parts = re.split(r"[-/]", m.group(0))
        y = int(parts[0])
        mth = int(parts[1])
        d = int(parts[2])
        try:
            return dt.date(y, mth, d).isoformat()
        except Exception:
            return dt.date.today().isoformat()
    return dt.date.today().isoformat()


def write_jsonl(items: Iterable[Dict[str, Any]], path: str) -> None:
    with open(path, "wb") as f:
        for it in items:
            f.write(orjson.dumps(it, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z))
            f.write(b"\n")

def append_jsonl(item: Dict[str, Any], path: str) -> None:
    with open(path, "ab") as f:
        f.write(orjson.dumps(item, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z))
        f.write(b"\n")


def shuffle_and_split(items: List[Dict[str, Any]], val_ratio: float, seed: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rng = random.Random(seed)
    rng.shuffle(items)
    n = len(items)
    n_val = max(1, int(n * val_ratio)) if n > 0 else 0
    val = items[:n_val]
    train = items[n_val:]
    return train, val


