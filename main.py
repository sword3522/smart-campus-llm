#!/usr/bin/env python
"""
智慧校园助手 - 主服务入口

功能:
1. 每日定时任务: 每天早上7:00自动爬取昨天的新闻并生成日报
2. 问答服务接口: 基于历史日报回答用户问题

使用方式:
    # 启动完整服务（包含定时任务和API）
    python main.py serve
    
    # 仅运行一次每日任务
    python main.py daily-job
    
    # 命令行问答测试
    python main.py ask "最近有什么竞赛？" --days 7 --identity student
"""
from __future__ import annotations

import argparse
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from typing import Literal


def run_daily_job(target_date: str = None):
    """
    执行每日任务
    
    Args:
        target_date: 目标日期 (YYYY-MM-DD 或 MM-DD)，默认为昨天
    """
    from services.daily_job import DailyJobService
    
    service = DailyJobService()
    result = service.run_daily_job(target_date=target_date)
    
    return result


def ask_question(
    question: str,
    days: int = 7,
    user_identity: Literal["student", "teacher"] = "student"
):
    """问答功能"""
    from services.qa_service import QAService
    
    service = QAService()
    result = service.answer_question(
        question=question,
        days=days,
        user_identity=user_identity
    )
    
    print("\n" + "=" * 60)
    print(f"【问题】: {result['question']}")
    print(f"【身份】: {result['user_identity']}")
    print(f"【参考天数】: {result['days_referenced']}")
    print("=" * 60)
    print(f"\n【回答】:\n{result['answer']}")
    print("\n" + "=" * 60)
    
    return result


def start_scheduler():
    """启动定时调度器"""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    
    scheduler = BackgroundScheduler()
    
    # 每天早上7:00执行每日任务
    scheduler.add_job(
        run_daily_job,
        CronTrigger(hour=7, minute=0),
        id='daily_news_job',
        name='每日新闻爬取与日报生成',
        replace_existing=True
    )
    
    scheduler.start()
    print("✓ 定时调度器已启动")
    print("  - 每日任务: 每天 07:00 执行")
    
    return scheduler


def start_api_server(host: str = "0.0.0.0", port: int = 8000):
    """启动 API 服务器"""
    import uvicorn
    from api import app
    
    print(f"\n🚀 正在启动 API 服务器: http://{host}:{port}")
    print("   - API 文档: http://{host}:{port}/docs")
    
    uvicorn.run(app, host=host, port=port)


def start_full_service(host: str = "0.0.0.0", port: int = 8000):
    """启动完整服务（定时任务 + API）"""
    print("\n" + "=" * 60)
    print("【智慧校园助手】服务启动中...")
    print("=" * 60)
    
    # 启动定时调度器
    scheduler = start_scheduler()
    
    try:
        # 启动API服务器（阻塞）
        start_api_server(host, port)
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
    finally:
        scheduler.shutdown()
        print("服务已关闭")


def interactive_qa():
    """交互式问答模式"""
    from services.qa_service import QASession
    
    print("\n" + "=" * 60)
    print("【智慧校园助手】交互式问答")
    print("=" * 60)
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'student' 或 'teacher' 切换身份")
    print("输入 'days N' 设置参考天数 (例如: days 14)")
    print("=" * 60)
    
    session = QASession(user_identity="student", days=7)
    print(f"\n当前身份: 学生 | 参考天数: 7")
    
    while True:
        try:
            user_input = input("\n📝 请输入问题: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            
            if user_input.lower() == 'student':
                session.set_identity("student")
                print("✓ 已切换为学生身份")
                continue
            
            if user_input.lower() == 'teacher':
                session.set_identity("teacher")
                print("✓ 已切换为教师身份")
                continue
            
            if user_input.lower().startswith('days '):
                try:
                    days = int(user_input.split()[1])
                    session.set_days(days)
                    print(f"✓ 参考天数已设置为 {days}")
                except (IndexError, ValueError):
                    print("⚠️ 格式错误，请使用: days N (例如: days 14)")
                continue
            
            # 回答问题
            answer = session.ask(user_input)
            print(f"\n🤖 【回答】:\n{answer}")
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n⚠️ 发生错误: {e}")


def get_today_report(identity: str = "student"):
    """获取今日日报"""
    from services.qa_service import QAService
    from datetime import timedelta
    
    service = QAService()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    summary = service.get_report_summary(yesterday, identity)
    
    if summary:
        print(f"\n【{yesterday} 日报 - {'学生版' if identity == 'student' else '教师版'}】")
        print("=" * 60)
        print(summary)
        print("=" * 60)
    else:
        print(f"⚠️ 未找到 {yesterday} 的日报")


def main():
    parser = argparse.ArgumentParser(
        description="智慧校园助手服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py serve                    # 启动完整服务
  python main.py serve --port 8080        # 指定端口启动
  python main.py daily-job                # 手动执行每日任务（昨天）
  python main.py daily-job --date 2025-11-25  # 指定日期生成日报
  python main.py daily-job --date 11-25   # 简写日期格式
  python main.py ask "最近有什么竞赛？"    # 命令行问答
  python main.py interactive              # 交互式问答
  python main.py report                   # 查看今日日报
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # serve 命令
    serve_parser = subparsers.add_parser('serve', help='启动完整服务')
    serve_parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址')
    serve_parser.add_argument('--port', type=int, default=8000, help='端口号')
    
    # daily-job 命令
    daily_parser = subparsers.add_parser('daily-job', help='手动执行每日任务')
    daily_parser.add_argument('--date', type=str, default=None,
                             help='指定日期 (YYYY-MM-DD 或 MM-DD)，默认为昨天')
    
    # ask 命令
    ask_parser = subparsers.add_parser('ask', help='命令行问答')
    ask_parser.add_argument('question', type=str, help='问题内容')
    ask_parser.add_argument('--days', type=int, default=7, help='参考天数')
    ask_parser.add_argument('--identity', type=str, choices=['student', 'teacher'], 
                           default='student', help='用户身份')
    
    # interactive 命令
    subparsers.add_parser('interactive', help='交互式问答模式')
    
    # report 命令
    report_parser = subparsers.add_parser('report', help='查看今日日报')
    report_parser.add_argument('--identity', type=str, choices=['student', 'teacher'],
                              default='student', help='用户身份')
    
    args = parser.parse_args()
    
    if args.command == 'serve':
        start_full_service(args.host, args.port)
    
    elif args.command == 'daily-job':
        run_daily_job(target_date=args.date)
    
    elif args.command == 'ask':
        ask_question(args.question, args.days, args.identity)
    
    elif args.command == 'interactive':
        interactive_qa()
    
    elif args.command == 'report':
        get_today_report(args.identity)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

