"""
问答服务模块 - 基于历史日报的智能问答
"""
from __future__ import annotations

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Literal

from .model_service import get_model_service


class QAService:
    """
    问答服务
    - 读取历史日报
    - 基于历史简报回答用户问题
    """
    
    def __init__(
        self,
        daily_report_dir: str = "/root/NLP/daily_reports",
        default_days: int = 7
    ):
        self.daily_report_dir = daily_report_dir
        self.default_days = default_days
    
    def get_history_briefs(
        self,
        days: int = None,
        user_identity: Literal["student", "teacher"] = "student"
    ) -> str:
        """
        获取最近N天的新闻简报文本
        
        Args:
            days: 天数，默认使用 default_days
            user_identity: 用户身份，决定使用学生版还是教师版简报
        
        Returns:
            格式化的历史简报文本
        """
        if days is None:
            days = self.default_days
        
        reports = self._load_recent_reports(days)
        
        if not reports:
            return "【历史简报】：\n暂无最近的新闻简报。"
        
        # 选择对应身份的简报
        summary_key = "student_summary" if user_identity == "student" else "teacher_summary"
        
        briefs_lines = []
        for report in reports:
            date = report.get("date", "未知日期")
            summary = report.get(summary_key, "无内容")
            
            # 清理和截断过长的简报
            summary = summary.strip()
            if len(summary) > 1500:
                summary = summary[:1500] + "..."
            
            briefs_lines.append(f"[{date}]：{summary}")
        
        history_text = "【历史简报】：\n" + "\n".join(briefs_lines)
        return history_text
    
    def _load_recent_reports(self, days: int) -> List[Dict[str, Any]]:
        """
        加载最近N天的日报
        
        注意：会过滤掉 news_count=0 的空日报
        """
        reports = []
        today = datetime.now().date()
        
        for i in range(1, days + 1):  # 从昨天开始
            date = today - timedelta(days=i)
            date_str = date.isoformat()
            
            report_path = os.path.join(self.daily_report_dir, f"report_{date_str}.json")
            if os.path.exists(report_path):
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        # 过滤掉 news_count=0 的空日报
                        if report.get("news_count", 0) > 0:
                            reports.append(report)
                        else:
                            print(f"  跳过空日报: {date_str} (news_count=0)")
                except Exception as e:
                    print(f"加载日报失败 {date_str}: {e}")
        
        # 按日期排序（旧到新）
        reports.sort(key=lambda x: x.get("date", ""))
        return reports
    
    def answer_question(
        self,
        question: str,
        days: int = None,
        user_identity: Literal["student", "teacher"] = "student"
    ) -> Dict[str, Any]:
        """
        回答用户问题
        
        Args:
            question: 用户的问题
            days: 参考的历史天数
            user_identity: 用户身份
        
        Returns:
            包含答案和元信息的字典
        """
        if days is None:
            days = self.default_days
        
        # 获取历史简报
        history_briefs = self.get_history_briefs(days, user_identity)
        
        # 获取模型服务并生成回答
        model_service = get_model_service()
        
        print(f"\n🔍 正在处理问题: {question}")
        print(f"   - 参考天数: {days}")
        print(f"   - 用户身份: {user_identity}")
        
        answer = model_service.answer_question(
            history_briefs=history_briefs,
            user_question=question,
            user_identity=user_identity
        )
        
        return {
            "question": question,
            "answer": answer,
            "days_referenced": days,
            "user_identity": user_identity,
            "answered_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_available_dates(self) -> List[str]:
        """获取所有可用的日报日期"""
        dates = []
        if os.path.exists(self.daily_report_dir):
            for filename in os.listdir(self.daily_report_dir):
                if filename.startswith("report_") and filename.endswith(".json"):
                    date_str = filename.replace("report_", "").replace(".json", "")
                    dates.append(date_str)
        
        dates.sort(reverse=True)
        return dates
    
    def get_report_summary(
        self,
        date_str: str = None,
        user_identity: Literal["student", "teacher"] = "student"
    ) -> Optional[str]:
        """
        获取指定日期的日报简报
        
        Args:
            date_str: 日期字符串，默认为昨天
            user_identity: 用户身份
        
        Returns:
            对应身份的简报内容
        """
        if date_str is None:
            date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        report_path = os.path.join(self.daily_report_dir, f"report_{date_str}.json")
        
        if not os.path.exists(report_path):
            return None
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            summary_key = "student_summary" if user_identity == "student" else "teacher_summary"
            return report.get(summary_key)
        except Exception as e:
            print(f"读取日报失败: {e}")
            return None


class QASession:
    """
    问答会话管理
    支持多轮对话和上下文记忆
    """
    
    def __init__(
        self,
        user_identity: Literal["student", "teacher"] = "student",
        days: int = 7
    ):
        self.qa_service = QAService()
        self.user_identity = user_identity
        self.days = days
        self.history: List[Dict[str, str]] = []
    
    def ask(self, question: str) -> str:
        """提问并获取回答"""
        result = self.qa_service.answer_question(
            question=question,
            days=self.days,
            user_identity=self.user_identity
        )
        
        # 记录对话历史
        self.history.append({
            "role": "user",
            "content": question
        })
        self.history.append({
            "role": "assistant",
            "content": result["answer"]
        })
        
        return result["answer"]
    
    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.history.copy()
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.history.clear()
    
    def set_identity(self, identity: Literal["student", "teacher"]) -> None:
        """切换用户身份"""
        self.user_identity = identity
    
    def set_days(self, days: int) -> None:
        """设置参考天数"""
        self.days = days


# 便捷函数
def ask_question(
    question: str,
    days: int = 7,
    user_identity: Literal["student", "teacher"] = "student"
) -> str:
    """
    快速提问
    
    Args:
        question: 问题
        days: 参考的历史天数
        user_identity: 用户身份
    
    Returns:
        回答文本
    """
    service = QAService()
    result = service.answer_question(question, days, user_identity)
    return result["answer"]


if __name__ == "__main__":
    # 简单测试
    service = QAService()
    
    # 显示可用日期
    dates = service.get_available_dates()
    print(f"可用日报日期: {dates}")
    
    # 测试问答
    result = service.answer_question(
        question="最近有什么竞赛可以参加？",
        days=7,
        user_identity="student"
    )
    print(f"\n问题: {result['question']}")
    print(f"回答: {result['answer']}")

