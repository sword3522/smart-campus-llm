from __future__ import annotations

from typing import List, Dict


def build_identity_summary_prompt(title: str, source: str, publish_time: str, content_clean: str) -> list[dict]:
    system = (
        "你是一个资深教务秘书。请阅读以下新闻原文内容，分别生成【学生版总结】和【教师版总结】。\n"
        "学生版关注：截止日期、学分、操作步骤、报名/入口、注意事项。\n"
        "教师版关注：管理职责、督促事项、截止时间、需要协调的工作点。\n"
        "严格输出为JSON格式：{\"student_summary\": \"...\", \"teacher_summary\": \"...\"}。"
    )
    user = (
        f"【标题】{title}\n"
        f"【来源】{source}\n"
        f"【发布时间】{publish_time}\n"
        f"【正文】\n{content_clean}\n\n"
        "请输出JSON。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_history_qa_prompt(daily_briefs: List[Dict[str, str]]) -> list[dict]:
    """
    daily_briefs: [{ 'date': 'YYYY-MM-DD', 'summary': '学生版简报若干条拼接' }, ...]
    """
    system = (
        "你现在扮演一个全知的智慧校园助手。"
        "我会给你过去7天内的若干条【学生版新闻简报】。"
        "请你先以“迷茫学生”的口吻提出一个模糊但真实的问题（例如：最近有啥比赛没？）。"
        "然后再以“智慧助手”的口吻基于这些简报给出正确且简洁的回答。"
        "如果简报中没有相关信息，就明确回答不知道。"
        "输出格式为：\n"
        "问题：...\n"
        "回答：...\n"
    )
    briefs_text = []
    for b in daily_briefs:
        briefs_text.append(f"[{b.get('date')}]：{b.get('summary')}")
    user = "【历史简报】：\n" + "\n".join(briefs_text)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_daily_identity_summary_prompt(date: str, day_items: List[Dict[str, str]]) -> list[dict]:
    """
    用于“按天聚合”的差异化总结。将同一天多条新闻拼接为一个输入，生成学生/教师两个版本摘要。
    day_items: [{title, source, publish_time, content_clean}, ...]
    """
    system = (
        "你是一个资深教务秘书。以下是同一天内若干条教务/活动新闻。"
        "请分别生成【学生版总结】与【教师版总结】。\n"
        "学生版聚焦：截止日期、学分/综测、报名入口/操作步骤、注意事项。\n"
        "教师版聚焦：管理职责、督促/组织事项、关键节点时间、需要协调的工作点。\n"
        "当日若有多条新闻，请将要点分类并用有序列表清晰列出，使用格式为【简短要点子标题】：总结描述。\n"
        "严格输出为JSON：{\"student_summary\": \"...\", \"teacher_summary\": \"...\"}。"
    )
    blocks: List[str] = [f"【日期】{date}"]
    for idx, it in enumerate(day_items, 1):
        title = it.get("title") or ""
        source = it.get("source") or ""
        publish_time = it.get("publish_time") or ""
        content = it.get("content_clean") or it.get("content_raw") or ""
        blocks.append(
            f"【新闻{idx}】\n"
            f"标题：{title}\n"
            f"来源：{source}\n"
            f"发布时间：{publish_time}\n"
            f"正文：\n{content}\n"
        )
    user = "\n".join(blocks) + "\n请输出JSON。"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_history_qa_prompt_days(daily_briefs: List[Dict[str, str]], days: int) -> list[dict]:
    """
    满足用户指定的API Prompt策略文案：
    “我给你过去X天的N条新闻总结。请你扮演一个迷茫的大学生，根据这些总结提出一个模糊的问题，
     然后作为全知助手给出基于这些总结的正确回答。如果总结里没提，就说不知道。”
    并要求输出：
      问题：...
      回答：...
    """
    n = len(daily_briefs)
    system = (
        f"我给你过去一段时间的新闻总结。请你扮演一个迷茫的大学生，根据这些总结提出一个模糊的问题"
        f"例如：最近有啥比赛没？最近有没有啥活动可以参加？有没有什么可以加集体活动分的活动？最近有没有什么考试要截止了？等等类似的问题（不要照搬例子，请自行发挥类似的问题），然后作为全知助手给出基于这些总结的正确回答。"
        "如果总结里没提，就说：最近没有该类新闻/通知，不知道。\n"
        "输出格式为：\n"
        "问题：...\n"
        "回答：...\n"
    )
    briefs_text = []
    for b in daily_briefs:
        briefs_text.append(f"[{b.get('date')}]：{b.get('summary')}")
    user = "【历史简报】：\n" + "\n".join(briefs_text)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


