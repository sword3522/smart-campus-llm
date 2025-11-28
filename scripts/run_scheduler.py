#!/usr/bin/env python
"""
独立的定时任务调度器

每天早上7:00执行每日任务：
1. 爬取昨天的新闻
2. 调用微调模型生成日报

可以单独运行此脚本作为后台服务。

使用方式:
    # 直接运行（前台）
    python scripts/run_scheduler.py
    
    # 后台运行
    nohup python scripts/run_scheduler.py > scheduler.log 2>&1 &
"""
from __future__ import annotations

import sys
import os
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from services.daily_job import DailyJobService


def daily_task():
    """每日任务"""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 定时任务开始执行")
    print(f"{'='*60}")
    
    try:
        service = DailyJobService()
        result = service.run_daily_job()
        
        if result["status"] == "success":
            print(f"\n✓ 任务执行成功!")
            print(f"  - 爬取新闻数: {result['news_count']}")
            print(f"  - 日报日期: {result['report']['date']}")
        else:
            print(f"\n⚠️ 昨天没有新闻")
            
    except Exception as e:
        print(f"\n✗ 任务执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 定时任务执行完毕")
    print(f"{'='*60}\n")


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║              智慧校园助手 - 定时任务调度器                    ║
╠══════════════════════════════════════════════════════════════╣
║  每天 07:00 自动执行:                                        ║
║    1. 爬取昨天的新闻                                         ║
║    2. 调用微调模型生成日报（学生版 + 教师版）                ║
╠══════════════════════════════════════════════════════════════╣
║  按 Ctrl+C 停止服务                                          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    scheduler = BlockingScheduler()
    
    # 每天早上7:00执行
    scheduler.add_job(
        daily_task,
        CronTrigger(hour=7, minute=0),
        id='daily_news_job',
        name='每日新闻爬取与日报生成',
        replace_existing=True
    )
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 调度器已启动")
    print("  - 定时任务: 每天 07:00")
    print("\n等待任务执行...\n")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n调度器已停止")


if __name__ == "__main__":
    main()

