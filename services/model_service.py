from __future__ import annotations
from typing import Literal, Optional
from nlp.llm_client import LLMClient


class ModelService:
    """
    模型服务封装
    - 调用底层 LLMClient
    - 管理 Prompt
    """
    def __init__(self):
        self.client = LLMClient()

    def generate(self, instruction: str, input_text: str) -> str:
        """
        通用生成接口
        """
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": input_text}
        ]
        return self.client.chat(messages)

    def summarize_news(
        self,
        news_content: str,
        user_identity: Literal["student", "teacher"] = "student"
    ) -> str:
        """
        生成新闻总结（Markdown格式）
        """
        identity_cn = "学生" if user_identity == "student" else "教师"
        instruction = (
            f"你是一个智慧校园助手。当前用户是【{identity_cn}】，请总结以下教务通知。"
            f"请为每条独立的新闻生成一个总结卡片，严格遵守以下 Markdown 格式："
            f"1. 每条新闻标题前加 `### ` (例如：`### 2024年数学竞赛报名通知`)。"
            f"2. 关键信息（如时间、地点、要求）使用列表项 `- ` 列出。"
            f"3. 重要的实体（名称、日期）使用 `**` 加粗。"
            f"4. 新闻之间自然换行即可。"
            f"重要提示：总结时请务必保留关键实体信息，严禁使用模糊指代。"
        )
        return self.generate(instruction, news_content)

    def answer_question(
        self,
        history_briefs: str,
        user_question: str,
        user_identity: Literal["student", "teacher"] = "student"
    ) -> str:
        """
        基于历史简报回答问题
        """
        identity_cn = "学生" if user_identity == "student" else "教师"
        instruction = (
            f"你是一个智慧校园助手。当前用户是【{identity_cn}】。"
            f"请基于提供的【历史新闻简报】回答用户的问题。"
            f"如果简报中没有相关信息，请明确说明无法回答。"
            f"回答要求：\n"
            f"1. 语气亲切，简明扼要。\n"
            f"2. 必须提及具体的活动/通知名称、时间等关键信息，避免模糊指代。\n"
            f"3. 如果有多个相关通知，请分点列出。"
        )
        input_text = f"【历史新闻简报】\n{history_briefs}\n\n【用户问题】\n{user_question}"
        return self.generate(instruction, input_text)


_instance = None

def get_model_service() -> ModelService:
    """获取 ModelService 单例"""
    global _instance
    if _instance is None:
        _instance = ModelService()
    return _instance
