"""
智慧校园助手 - FastAPI Web API

提供 RESTful API 接口:
- POST /ask: 问答接口
- GET /report: 获取日报
- POST /daily-job: 手动触发每日任务
- GET /reports: 获取可用日报列表
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Literal, List

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.daily_job import DailyJobService
from services.qa_service import QAService


# ============ API Models ============

class AskRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., description="用户的问题", example="最近有什么竞赛可以参加？")
    days: int = Field(default=7, ge=1, le=30, description="参考的历史天数")
    identity: Literal["student", "teacher"] = Field(default="student", description="用户身份")


class AskResponse(BaseModel):
    """问答响应"""
    question: str
    answer: str
    days_referenced: int
    user_identity: str
    answered_at: str


class ReportResponse(BaseModel):
    """日报响应"""
    date: str
    news_count: Optional[int] = None
    effective_news_count: Optional[int] = None # 新增字段
    student_summary: Optional[str] = None
    teacher_summary: Optional[str] = None
    generated_at: Optional[str] = None


class DailyJobResponse(BaseModel):
    """每日任务响应"""
    status: str
    message: str
    news_count: int = 0
    report_date: Optional[str] = None


class ReportListResponse(BaseModel):
    """日报列表响应"""
    available_dates: List[str]
    count: int


# ============ FastAPI App ============

app = FastAPI(
    title="智慧校园助手 API",
    description="""
## 智慧校园助手 - 新闻总结与智能问答系统

### 功能特点:
- 🗞️ **每日日报**: 自动爬取学校新闻，生成差异化总结（学生版/教师版）
- 🤖 **智能问答**: 基于历史新闻简报回答用户问题
- 👤 **身份识别**: 根据用户身份（学生/教师）提供不同角度的信息

### 使用场景:
1. 查询"最近有什么竞赛？"
2. 查询"有没有能加学分的活动？"
3. 查看每日新闻摘要
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ API Endpoints ============

@app.get("/", tags=["基础"])
async def root():
    """返回 Web 界面"""
    index_path = os.path.join(os.path.dirname(__file__), "web/index.html")
    return FileResponse(index_path)


@app.get("/health", tags=["基础"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/ask", response_model=AskResponse, tags=["问答"])
async def ask_question(request: AskRequest):
    """
    智能问答接口
    
    根据用户身份和历史新闻简报回答问题。
    
    **参数说明:**
    - `question`: 用户的问题
    - `days`: 参考的历史天数（1-30）
    - `identity`: 用户身份（student/teacher）
    
    **示例问题:**
    - "最近有什么竞赛可以参加？"
    - "有没有能加学分的活动？"
    - "最近有什么重要通知？"
    """
    try:
        service = QAService()
        result = service.answer_question(
            question=request.question,
            days=request.days,
            user_identity=request.identity
        )
        
        return AskResponse(
            question=result["question"],
            answer=result["answer"],
            days_referenced=result["days_referenced"],
            user_identity=result["user_identity"],
            answered_at=result["answered_at"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理问题时发生错误: {str(e)}")


@app.get("/report", response_model=ReportResponse, tags=["日报"])
async def get_report(
    date: Optional[str] = Query(
        None, 
        description="日期 (YYYY-MM-DD)，默认为昨天",
        example="2025-11-27"
    ),
    identity: Literal["student", "teacher"] = Query(
        "student",
        description="用户身份，决定返回学生版还是教师版"
    )
):
    """
    获取指定日期的日报
    
    **参数说明:**
    - `date`: 日期 (YYYY-MM-DD)，默认为昨天
    - `identity`: 用户身份，决定返回哪个版本的摘要
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    service = DailyJobService()
    report = service.get_report_by_date(date)
    
    if report is None:
        raise HTTPException(status_code=404, detail=f"未找到 {date} 的日报")
    
    # 根据身份返回对应的摘要
    summary_key = "student_summary" if identity == "student" else "teacher_summary"
    effective_count_key = "student_effective_count" if identity == "student" else "teacher_effective_count"
    
    # 如果日报中没有存储有效新闻数量，尝试从摘要中实时计算
    # 这对于代码更新前生成的但格式已符合 Markdown 要求的日报有效
    effective_count = report.get(effective_count_key)
    if effective_count is None:
        summary_text = report.get(summary_key, "")
        effective_count = summary_text.count("### ")
    
    return ReportResponse(
        date=report.get("date", date),
        news_count=report.get("news_count"),
        effective_news_count=effective_count,
        student_summary=report.get("student_summary") if identity == "student" else None,
        teacher_summary=report.get("teacher_summary") if identity == "teacher" else None,
        generated_at=report.get("generated_at")
    )


@app.get("/report/full", response_model=ReportResponse, tags=["日报"])
async def get_full_report(
    date: Optional[str] = Query(
        None,
        description="日期 (YYYY-MM-DD)，默认为昨天",
        example="2025-11-27"
    )
):
    """
    获取完整日报（包含学生版和教师版）
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    service = DailyJobService()
    report = service.get_report_by_date(date)
    
    if report is None:
        raise HTTPException(status_code=404, detail=f"未找到 {date} 的日报")
    
    # 同样为完整日报补充实时计算逻辑
    student_eff = report.get("student_effective_count")
    if student_eff is None:
        student_eff = report.get("student_summary", "").count("### ")
        
    teacher_eff = report.get("teacher_effective_count")
    if teacher_eff is None:
        teacher_eff = report.get("teacher_summary", "").count("### ")
    
    return ReportResponse(
        date=report.get("date", date),
        news_count=report.get("news_count"),
        # 这里 full 接口并没有定义 separate effective counts for student/teacher in the response model explicitly 
        # based on previous tool outputs, ReportResponse has effective_news_count (single int).
        # But wait, get_full_report returns ReportResponse which has ONE effective_news_count.
        # Usually full report might need structure adjustment if we want both.
        # But looking at previous definition of ReportResponse:
        # effective_news_count: Optional[int] = None
        # It seems ambiguous which one it refers to in 'full' mode. 
        # Let's just sum them or return student's for now to match the model, 
        # or maybe the user doesn't use full report for the specific UI card.
        # The UI uses /report endpoint usually.
        # For safety, let's just use student count or sum, but standard use is /report with identity.
        effective_news_count=student_eff, # Defaulting to student count for general stat
        student_summary=report.get("student_summary"),
        teacher_summary=report.get("teacher_summary"),
        generated_at=report.get("generated_at")
    )


@app.get("/report/weekly", response_model=ReportResponse, tags=["日报"])
async def get_weekly_report(
    date: Optional[str] = Query(
        None, 
        description="结束日期 (YYYY-MM-DD)，默认为今天",
        example="2025-11-27"
    ),
    identity: Literal["student", "teacher"] = Query(
        "student",
        description="用户身份，决定返回学生版还是教师版"
    )
):
    """
    获取指定日期这一周的周报（过去7天汇总）
    
    如果周报数据不存在，会尝试现场生成。
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    service = DailyJobService()
    
    # 现场生成周报
    report = service.generate_weekly_report(end_date_str=date)
    
    if report.get("news_count", 0) == 0 and report.get("student_summary") == "本周无重要新闻通知。":
         # 虽然是正常返回，但对于前端来说可能希望是一个友好的提示
         # 不过 api 层面我们还是返回 200，让前端处理展示
         pass

    # 返回格式化响应
    # 将日期字段显示为范围 "start ~ end"
    display_date = f"{report['start_date']} ~ {report['end_date']}"
    
    effective_count = report.get("student_effective_count") if identity == "student" else report.get("teacher_effective_count")
    if effective_count is None:
        summary = report.get("student_summary") if identity == "student" else report.get("teacher_summary")
        effective_count = (summary or "").count("### ")

    return ReportResponse(
        date=display_date,
        news_count=report.get("news_count"),
        effective_news_count=effective_count,
        student_summary=report.get("student_summary") if identity == "student" else None,
        teacher_summary=report.get("teacher_summary") if identity == "teacher" else None,
        generated_at=report.get("generated_at")
    )


@app.get("/reports", response_model=ReportListResponse, tags=["日报"])
async def list_reports():
    """
    获取所有可用的日报日期列表
    """
    service = QAService()
    dates = service.get_available_dates()
    
    return ReportListResponse(
        available_dates=dates,
        count=len(dates)
    )


@app.get("/reports/recent", tags=["日报"])
async def get_recent_reports(
    days: int = Query(7, ge=1, le=30, description="获取最近N天的日报")
):
    """
    获取最近N天的日报列表
    """
    service = DailyJobService()
    reports = service.get_recent_reports(days)
    
    return {
        "count": len(reports),
        "days_requested": days,
        "reports": reports
    }


@app.post("/daily-job", response_model=DailyJobResponse, tags=["管理"])
async def trigger_daily_job(
    background_tasks: BackgroundTasks,
    date: Optional[str] = Query(None, description="指定日期，可以是 'today' 或 YYYY-MM-DD")
):
    """
    手动触发每日任务
    
    执行以下操作：
    1. 爬取新闻（默认昨天，如果 date='today' 则爬取今天）
    2. 生成日报总结（学生版 + 教师版）
    
    **注意**: 任务在后台执行，可能需要几分钟完成。
    """
    try:
        service = DailyJobService()
        # 如果是 'today'，直接同步执行以便即时反馈（或者也可以用 background_tasks，但前端需要轮询）
        # 为了前端体验，对于单日生成我们这里选择同步等待结果，
        # 如果爬取时间过长可能会超时，生产环境建议用 WebSocket 或轮询。
        # 考虑到 demo 演示，直接同步调用。
        result = service.run_daily_job(target_date=date)
        
        if result["status"] == "no_news":
            return DailyJobResponse(
                status="no_news",
                message=f"{date or '昨天'}没有新闻，跳过日报生成",
                news_count=0
            )
        
        return DailyJobResponse(
            status="success",
            message="每日任务执行成功",
            news_count=result["news_count"],
            report_date=result["report"]["date"] if result.get("report") else None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行每日任务时发生错误: {str(e)}")


@app.get("/briefs", tags=["日报"])
async def get_history_briefs(
    days: int = Query(7, ge=1, le=30, description="天数"),
    identity: Literal["student", "teacher"] = Query("student", description="用户身份")
):
    """
    获取历史简报文本
    
    用于调试和查看将要传递给模型的上下文内容。
    """
    service = QAService()
    briefs = service.get_history_briefs(days, identity)
    
    return {
        "days": days,
        "identity": identity,
        "briefs": briefs
    }


# 静态文件路由
web_dir = os.path.join(os.path.dirname(__file__), "web")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """避免浏览器请求 favicon.ico 时报错"""
    return Response(status_code=204)

@app.get("/style.css", tags=["静态资源"])
async def get_css():
    """返回CSS样式文件"""
    css_path = os.path.join(web_dir, "style.css")
    return FileResponse(css_path, media_type="text/css")

@app.get("/main.js", tags=["静态资源"])
async def get_js():
    """返回JavaScript文件"""
    js_path = os.path.join(web_dir, "main.js")
    return FileResponse(js_path, media_type="application/javascript")


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

