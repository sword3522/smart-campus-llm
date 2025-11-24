from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests
from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type

from .config import get_settings


class LLMError(Exception):
    pass


class LLMClient:
    """
    一个简单的LLM客户端封装，支持：
    - DeepSeek（OpenAI兼容接口）
    - OpenAI（或其它OpenAI兼容服务）
    - Mock（无网络环境下用于快速开发/调试）
    """

    def __init__(self, provider: Optional[str] = None, api_key: Optional[str] = None,
                 api_base: Optional[str] = None, model: Optional[str] = None,
                 timeout_seconds: Optional[int] = None):
        settings = get_settings()
        self.provider = (provider or settings.llm_provider).lower()
        self.api_key = api_key or settings.api_key or "sk-mock"
        self.api_base = api_base or settings.api_base
        self.model = model or settings.model
        self.timeout_seconds = timeout_seconds or settings.timeout_seconds

        # 默认 base
        if not self.api_base:
            if self.provider == "deepseek":
                self.api_base = "https://api.deepseek.com"
            elif self.provider == "openai":
                self.api_base = "https://api.openai.com/v1"
            else:
                self.api_base = "http://localhost"  # mock时不使用

    @retry(wait=wait_exponential_jitter(initial=1, max=10), stop=stop_after_attempt(get_settings().max_retries),
           retry=retry_if_exception_type((requests.RequestException, LLMError)))
    def chat(self, messages: List[Dict[str, str]], temperature: float | None = None,
             max_tokens: Optional[int] = None) -> str:
        if self.provider == "mock":
            return self._chat_mock(messages)
        elif self.provider in ("deepseek", "openai"):
            return self._chat_openai_compatible(messages, temperature, max_tokens)
        else:
            raise LLMError(f"Unsupported provider: {self.provider}")

    def _chat_openai_compatible(self, messages: List[Dict[str, str]], temperature: float | None,
                                max_tokens: Optional[int]) -> str:
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else get_settings().temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout_seconds)
        if resp.status_code >= 400:
            raise LLMError(f"HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise LLMError(f"Invalid response: {data}") from e

    def _chat_mock(self, messages: List[Dict[str, str]]) -> str:
        # 简单的可重复输出，方便调试无需外网
        last_user = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user = m["content"]
                break
        # 根据提示词中的任务类型，生成固定结构的JSON或答案
        if "分别生成【学生版总结】和【教师版总结】" in last_user or "学生版总结" in last_user:
            return json.dumps({
                "student_summary": "【学生版】时间/截止/学分/操作步骤要点（mock）。",
                "teacher_summary": "【教师版】职责/截止/督促要点（mock）。"
            }, ensure_ascii=False)
        if "扮演一个迷茫的大学生" in last_user or "根据给定的【过去一段时间的新闻简报】" in last_user:
            return "问题：最近有啥活动？\n回答：根据简报，近期有“校园歌手大赛”（mock），可加美育分。"
        # 默认回显
        return "好的（mock）。"


