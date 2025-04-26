#!/usr/bin/env python3
"""
ArXiv Helper 主应用

提供Web界面和API接口，用于浏览、搜索和管理arXiv论文
"""

import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from src.config import APP_HOST, APP_PORT, DEBUG
from src.api import router as api_router
from src.models import init_db

# 创建FastAPI应用
app = FastAPI(
    title="ArXiv Helper",
    description="浏览、搜索和管理arXiv论文的工具",
    version="0.1.0",
)

# 挂载静态文件
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static"
)

# 设置模板
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# 挂载API路由
app.include_router(api_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ArXiv Helper"}
    )


@app.get("/paper/{arxiv_id}", response_class=HTMLResponse)
async def paper_detail(request: Request, arxiv_id: str):
    """论文详情页"""
    return templates.TemplateResponse(
        "paper.html",
        {"request": request, "title": "论文详情", "arxiv_id": arxiv_id}
    )


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    """搜索页面"""
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "title": "搜索论文", "query": q}
    )


@app.get("/library", response_class=HTMLResponse)
async def library_page(request: Request):
    """收藏夹页面"""
    return templates.TemplateResponse(
        "library.html",
        {"request": request, "title": "收藏夹"}
    )


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("应用启动...")
    # 初始化数据库
    init_db()
    logger.info("数据库初始化完成")


def main():
    """主函数"""
    try:
        # 运行应用
        uvicorn.run(
            "src.main:app",
            host=APP_HOST,
            port=APP_PORT,
            reload=DEBUG,
            log_level="info",
        )
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 