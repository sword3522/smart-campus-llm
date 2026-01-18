"""
每日任务模块 - 自动爬取新闻并生成日报总结
"""
from __future__ import annotations

import os
import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional, Literal

from .model_service import get_model_service


class DailyJobService:
    """
    每日任务服务
    - 爬取昨天的新闻
    - 调用微调模型生成日报总结（学生版/教师版）
    """
    
    def __init__(
        self,
        news_save_dir: str = "/root/NLP/grab_news/news_days",
        daily_report_dir: str = "/root/NLP/daily_reports",
        base_url: str = "https://dean.xjtu.edu.cn/"
    ):
        self.news_save_dir = news_save_dir
        self.daily_report_dir = daily_report_dir
        self.base_url = base_url
        
        # 确保目录存在
        os.makedirs(self.news_save_dir, exist_ok=True)
        os.makedirs(self.daily_report_dir, exist_ok=True)
    
    def crawl_news_by_date(self, target_date: str = None) -> List[Dict[str, Any]]:
        """
        爬取指定日期的新闻，整合了反爬验证绕过逻辑
        
        Args:
            target_date: 目标日期，支持格式：
                - YYYY-MM-DD (如 2025-11-27)
                - MM-DD (如 11-27，默认当前年份)
                - None (默认昨天)
        
        Returns:
            新闻列表，每条新闻包含 id, url, title, content_clean, publish_time 等字段
        """
        # 解析目标日期
        if target_date is None:
            target_mm_dd = (datetime.now() - timedelta(days=1)).strftime('%m-%d')
            target_full = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        elif '-' in target_date and len(target_date) == 10:
            # YYYY-MM-DD 格式
            target_full = target_date
            target_mm_dd = target_date[5:]  # 提取 MM-DD
        elif '-' in target_date and len(target_date) <= 5:
            # MM-DD 格式
            target_mm_dd = target_date.zfill(5)  # 确保是 MM-DD 格式
            current_year = datetime.now().year
            target_full = f"{current_year}-{target_mm_dd}"
        else:
            print(f"⚠️ 无法解析日期格式: {target_date}，使用昨天")
            target_mm_dd = (datetime.now() - timedelta(days=1)).strftime('%m-%d')
            target_full = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"正在爬取新闻: {self.base_url}")
        print(f"目标日期: {target_mm_dd} ({target_full})")

        # 使用 grab_news.py 中的更稳健的爬取逻辑
        try:
            from grab_news.grab_news import crawl_news
            
            # 直接调用封装好的 crawl_news 函数
            # 它会自动处理 Session、分页、详情页抓取和反爬绕过
            news_data = crawl_news(target_date=target_mm_dd, max_depth=5)
            
            if not news_data:
                print(f"目标日期 ({target_mm_dd}) 没有新闻")
                return []
            
            print(f"找到 {len(news_data)} 个新闻条目")
            
            # 对返回的数据进行简单的格式化，确保符合 DailyJobService 的预期
            formatted_data = []
            crawl_time = datetime.now().strftime('%Y-%m-%d')
            
            for i, item in enumerate(news_data, 1):
                # 确保 id 格式一致
                item['id'] = f"news_{crawl_time}_{i}"
                
                # 确保 publish_time 是完整日期
                if not item.get('publish_time'):
                     item['publish_time'] = target_full
                elif len(item['publish_time']) == 5: # 只有 MM-DD
                     current_year = datetime.now().year
                     item['publish_time'] = f"{current_year}-{item['publish_time']}"
                
                formatted_data.append(item)
            
            # 保存新闻数据
            if formatted_data:
                filename = f"news_{target_mm_dd.replace('-', '')}.json"
                save_path = os.path.join(self.news_save_dir, filename)
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(formatted_data, f, ensure_ascii=False, indent=2)
                print(f"\n✓ 已保存 {len(formatted_data)} 条新闻到: {save_path}")
            
            return formatted_data

        except ImportError:
            print("⚠️ 无法导入 grab_news 模块，回退到普通爬取模式")
            return []
        except Exception as e:
            print(f"✗ 爬取过程中发生错误: {e}")
            return []
    
    def crawl_yesterday_news(self) -> List[Dict[str, Any]]:
        """爬取昨天的新闻（兼容旧接口）"""
        return self.crawl_news_by_date(target_date=None)
    
    def load_news_from_file(self, target_date: str) -> Optional[List[Dict[str, Any]]]:
        """
        从已保存的文件加载新闻数据
        
        Args:
            target_date: 目标日期 (YYYY-MM-DD 或 MM-DD)
        
        Returns:
            新闻列表，如果文件不存在返回 None
        """
        # 解析日期获取 MM-DD 格式
        if len(target_date) == 10:
            mm_dd = target_date[5:]
        else:
            mm_dd = target_date.zfill(5)
        
        filename = f"news_{mm_dd.replace('-', '')}.json"
        file_path = os.path.join(self.news_save_dir, filename)
        
        if os.path.exists(file_path):
            print(f"📂 从文件加载新闻: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def _clean_content(self, content_div) -> str:
        """清洗HTML内容，提取纯文本"""
        # 处理段落标签
        for p_tag in content_div.find_all(['p', 'div']):
            if p_tag.get_text(strip=True):
                p_tag.append('\n')
        
        content_text = content_div.get_text(separator=' ', strip=True)
        
        # 清理多余空白
        content_text = re.sub(r' +', ' ', content_text)
        content_text = re.sub(r' \n', '\n', content_text)
        content_text = re.sub(r'\n ', '\n', content_text)
        content_text = re.sub(r'\n{2,}', '\n', content_text)
        content_text = content_text.strip()
        
        # 清理每行
        lines = content_text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                line = re.sub(r'\s+', ' ', line)
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def generate_daily_report(
        self,
        news_list: List[Dict[str, Any]],
        date_str: Optional[str] = None
    ) -> Dict[str, str]:
        """
        生成每日新闻总结报告（学生版 + 教师版）
        
        Args:
            news_list: 新闻列表
            date_str: 日期字符串 (YYYY-MM-DD)
        
        Returns:
            包含 student_summary 和 teacher_summary 的字典
        """
        if not news_list:
            return {
                "date": date_str or datetime.now().strftime('%Y-%m-%d'),
                "student_summary": "今日无重要新闻通知。",
                "teacher_summary": "今日无重要新闻通知。"
            }
        
        if not date_str:
            date_str = news_list[0].get('publish_time', datetime.now().strftime('%Y-%m-%d'))
        
        # 构建输入文本
        blocks = [f"【日期】{date_str}"]
        for idx, news in enumerate(news_list, 1):
            blocks.append(
                f"【新闻{idx}】\n"
                f"标题：{news.get('title', '')}\n"
                f"来源：{news.get('source', '教务处')}\n"
                f"发布时间：{news.get('publish_time', '')}\n"
                f"正文：\n{news.get('content_clean', '')[:2000]}\n"  # 限制长度
            )
        
        news_content = "\n".join(blocks)
        
        # 获取模型服务
        model_service = get_model_service()
        
        print("\n正在生成学生版日报...")
        student_summary = model_service.summarize_news(news_content, user_identity="student")
        
        print("正在生成教师版日报...")
        teacher_summary = model_service.summarize_news(news_content, user_identity="teacher")
        
        # 计算有效新闻数量（基于摘要中的标题数量）
        student_effective_count = student_summary.count("### ")
        teacher_effective_count = teacher_summary.count("### ")
        
        report = {
            "date": date_str,
            "news_count": len(news_list),
            "student_effective_count": student_effective_count,
            "teacher_effective_count": teacher_effective_count,
            "student_summary": student_summary,
            "teacher_summary": teacher_summary,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 保存日报
        report_filename = f"report_{date_str}.json"
        report_path = os.path.join(self.daily_report_dir, report_filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 日报已保存到: {report_path}")
        
        return report
    
    def run_daily_job(self, target_date: str = None) -> Dict[str, Any]:
        """
        执行完整的每日任务流程
        
        Args:
            target_date: 目标日期 (YYYY-MM-DD 或 MM-DD)，默认为昨天。
                        如果传入 "today"，则处理今天。
        
        Returns:
            任务执行结果，包含爬取的新闻数量和生成的日报
        """
        # 解析目标日期
        if target_date == "today":
            target_full = datetime.now().strftime('%Y-%m-%d')
            date_display = "今天"
        elif target_date is None:
            target_full = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            date_display = "昨天"
        elif '-' in target_date and len(target_date) == 10:
            target_full = target_date
            date_display = target_date
        elif '-' in target_date:
            mm_dd = target_date.zfill(5)
            current_year = datetime.now().year
            target_full = f"{current_year}-{mm_dd}"
            date_display = target_full
        else:
            target_full = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            date_display = "昨天"
        
        print("=" * 60)
        print(f"【每日任务启动】 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"【目标日期】 {date_display} ({target_full})")
        print("=" * 60)
        
        # Step 1: 尝试从文件加载，如果没有则爬取
        print(f"\n📰 Step 1: 获取 {target_full} 的新闻")
        news_list = self.load_news_from_file(target_full)
        
        if news_list is None:
            print("文件不存在，开始爬取...")
            news_list = self.crawl_news_by_date(target_date=target_full)
        else:
            print(f"✓ 从文件加载了 {len(news_list)} 条新闻")
        
        if not news_list:
            print(f"\n⚠️ {target_full} 没有新闻，生成空日报")
            # 生成空日报
            empty_report = {
                "date": target_full,
                "news_count": 0,
                "student_summary": "今日无重要新闻通知。",
                "teacher_summary": "今日无重要新闻通知。",
                "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            # 保存空日报
            report_filename = f"report_{target_full}.json"
            report_path = os.path.join(self.daily_report_dir, report_filename)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(empty_report, f, ensure_ascii=False, indent=2)
            print(f"✓ 空日报已保存到: {report_path}")
            
            return {
                "status": "no_news",
                "news_count": 0,
                "report": empty_report
            }
        
        # Step 2: 生成日报
        print("\n📝 Step 2: 生成日报总结")
        report = self.generate_daily_report(news_list, date_str=target_full)
        
        print("\n" + "=" * 60)
        print("【每日任务完成】")
        print(f"  - 新闻数量: {len(news_list)}")
        print(f"  - 日报日期: {report['date']}")
        print("=" * 60)
        
        return {
            "status": "success",
            "news_count": len(news_list),
            "report": report
        }
    
    def get_report_by_date(self, date_str: str) -> Optional[Dict[str, Any]]:
        """
        获取指定日期的日报
        
        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
        
        Returns:
            日报内容，如果不存在返回 None
        """
        report_path = os.path.join(self.daily_report_dir, f"report_{date_str}.json")
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_recent_reports(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取最近N天的日报
        
        Args:
            days: 天数
        
        Returns:
            日报列表（按日期倒序）
        """
        reports = []
        today = datetime.now().date()
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.isoformat()
            report = self.get_report_by_date(date_str)
            if report:
                reports.append(report)
        
        return reports


    def generate_weekly_report(
        self,
        end_date_str: str,
    ) -> Dict[str, Any]:
        """
        生成周报（过去7天）
        
        Args:
            end_date_str: 结束日期 (YYYY-MM-DD)
            
        Returns:
            周报数据
        """
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            # 如果格式不对，默认今天
            end_date = datetime.now()
            end_date_str = end_date.strftime('%Y-%m-%d')
            
        start_date = end_date - timedelta(days=6) # 7 days including end_date
        
        week_summaries = []
        news_count_total = 0
        
        print(f"正在生成周报: {start_date.strftime('%Y-%m-%d')} ~ {end_date_str}")
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            date_s = current_date.strftime('%Y-%m-%d')
            report = self.get_report_by_date(date_s)
            
            # 如果日报不存在，尝试现场抓取并生成
            if not report:
                print(f"  - {date_s} 日报缺失，正在尝试自动补全...")
                try:
                    # run_daily_job 会处理爬取和生成
                    job_result = self.run_daily_job(target_date=date_s)
                    report = job_result.get("report")
                except Exception as e:
                    print(f"  ⚠️ 自动补全 {date_s} 日报失败: {e}")
            
            if report and report.get('news_count', 0) > 0:
                news_count_total += report.get('news_count', 0)
                week_summaries.append({
                    "date": date_s,
                    "student": report.get("student_summary", ""),
                    "teacher": report.get("teacher_summary", "")
                })
        
        if not week_summaries:
             return {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date_str,
                "news_count": 0,
                "student_summary": "本周无重要新闻通知。",
                "teacher_summary": "本周无重要新闻通知。",
                "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        # 拼接每日总结作为输入
        combined_text_student = ""
        combined_text_teacher = ""
        
        for item in week_summaries:
            combined_text_student += f"【{item['date']}】\n{item['student']}\n\n"
            combined_text_teacher += f"【{item['date']}】\n{item['teacher']}\n\n"
            
        model_service = get_model_service()
        
        # 使用 summarize_news 生成周报，但添加前缀说明这是周报
        # 为了让模型知道这是汇总，我们可以稍微包装一下 summarize_news 或者直接用
        # 这里直接用，因为 summarize_news 的 prompt 比较通用 ("请总结以下教务通知")
        
        print("  - 生成学生版周报...")
        weekly_student = model_service.summarize_news(
            f"以下是过去一周的每日新闻总结，请根据它们生成一份周报：\n\n{combined_text_student}", 
            user_identity="student"
        )
        
        print("  - 生成教师版周报...")
        weekly_teacher = model_service.summarize_news(
            f"以下是过去一周的每日新闻总结，请根据它们生成一份周报：\n\n{combined_text_teacher}", 
            user_identity="teacher"
        )
        
        student_effective_count = weekly_student.count("### ")
        teacher_effective_count = weekly_teacher.count("### ")

        return {
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date_str,
            "news_count": news_count_total,
            "student_summary": weekly_student,
            "teacher_summary": weekly_teacher,
            "student_effective_count": student_effective_count,
            "teacher_effective_count": teacher_effective_count,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# 便捷函数
def run_daily_job() -> Dict[str, Any]:
    """执行每日任务"""
    service = DailyJobService()
    return service.run_daily_job()


if __name__ == "__main__":
    run_daily_job()

