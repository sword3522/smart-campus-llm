#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import random
from typing import Any, Dict, List, Tuple
import sys

# 确保能从项目根目录导入 nlp 包
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nlp.utils import read_json_or_jsonl_any, write_jsonl, shuffle_and_split


def main():
    parser = argparse.ArgumentParser(description="将 identity.jsonl 与 history_qa.jsonl 混合、打乱并划分 train/val")
    parser.add_argument("--identity", type=str, default="/root/NLP/datasets/identity.jsonl", help="identity.jsonl 路径")
    parser.add_argument("--history", type=str, default="/root/NLP/datasets/history_qa.jsonl", help="history_qa.jsonl 路径")
    parser.add_argument("--out-dir", type=str, default="/root/NLP/datasets", help="输出目录")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="验证集比例，默认 0.1")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    identity_items: List[Dict[str, Any]] = read_json_or_jsonl_any(args.identity)
    history_items: List[Dict[str, Any]] = read_json_or_jsonl_any(args.history)
    mixed: List[Dict[str, Any]] = identity_items + history_items

    train, val = shuffle_and_split(mixed, val_ratio=args.val_ratio, seed=args.seed)

    train_path = os.path.join(args.out_dir, "train.jsonl")
    val_path = os.path.join(args.out_dir, "val.jsonl")
    write_jsonl(train, train_path)
    write_jsonl(val, val_path)

    print(f"混合完成。train: {len(train)}, val: {len(val)}")
    print(f"train -> {train_path}")
    print(f"val   -> {val_path}")


if __name__ == "__main__":
    main()


