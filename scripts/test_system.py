#!/usr/bin/env python
"""
系统功能测试脚本

测试各个模块是否正常工作。

使用方式:
    python scripts/test_system.py
"""
from __future__ import annotations

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_crawler():
    """测试爬虫功能"""
    print("\n" + "=" * 60)
    print("【测试1】爬虫功能")
    print("=" * 60)
    
    from services.daily_job import DailyJobService
    
    service = DailyJobService()
    news_list = service.crawl_yesterday_news()
    
    print(f"\n✓ 爬取完成，共 {len(news_list)} 条新闻")
    
    for i, news in enumerate(news_list[:3], 1):
        print(f"\n  [{i}] {news['title'][:50]}...")
        print(f"      发布时间: {news['publish_time']}")
    
    return news_list


def test_model_service():
    """测试模型服务"""
    print("\n" + "=" * 60)
    print("【测试2】模型服务")
    print("=" * 60)
    
    from services.model_service import get_model_service
    
    service = get_model_service()
    
    print("\n正在加载模型...")
    service.load()
    
    print("\n✓ 模型加载成功")
    
    # 测试生成
    print("\n正在测试生成功能...")
    test_input = """【日期】2025-11-27
【新闻1】
标题：关于2025年春季学期选课的通知
来源：教务处
发布时间：2025-11-27
正文：
各位同学：2025年春季选课将于12月1日开始，请登录教务系统完成选课。
"""
    
    response = service.summarize_news(test_input, user_identity="student")
    print(f"\n【学生版总结】:\n{response[:200]}...")
    
    return True


def test_qa_service():
    """测试问答服务"""
    print("\n" + "=" * 60)
    print("【测试3】问答服务")
    print("=" * 60)
    
    from services.qa_service import QAService
    
    service = QAService()
    
    # 获取可用日期
    dates = service.get_available_dates()
    print(f"\n可用日报日期: {dates[:5]}...")
    
    # 测试问答（如果有日报的话）
    if dates:
        print("\n正在测试问答功能...")
        result = service.answer_question(
            question="最近有什么重要通知？",
            days=7,
            user_identity="student"
        )
        print(f"\n【问题】: {result['question']}")
        print(f"【回答】: {result['answer'][:300]}...")
    else:
        print("\n⚠️ 没有可用的日报，跳过问答测试")
    
    return True


def test_daily_job():
    """测试完整的每日任务"""
    print("\n" + "=" * 60)
    print("【测试4】完整每日任务")
    print("=" * 60)
    
    from services.daily_job import DailyJobService
    
    service = DailyJobService()
    result = service.run_daily_job()
    
    print(f"\n任务状态: {result['status']}")
    print(f"新闻数量: {result['news_count']}")
    
    if result.get('report'):
        print(f"日报日期: {result['report']['date']}")
    
    return result


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║              智慧校园助手 - 系统测试                         ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', type=str, choices=['crawler', 'model', 'qa', 'daily', 'all'],
                       default='all', help='选择要测试的模块')
    args = parser.parse_args()
    
    try:
        if args.test in ['crawler', 'all']:
            test_crawler()
        
        if args.test in ['model', 'all']:
            test_model_service()
        
        if args.test in ['qa', 'all']:
            test_qa_service()
        
        if args.test == 'daily':
            test_daily_job()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

