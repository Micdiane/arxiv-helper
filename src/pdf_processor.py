"""
PDF处理模块

负责下载PDF文件和提取文本内容
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from .config import DATABASE_URL, PDF_PATH, USE_FULL_TEXT
from .models import Paper

# 设置日志
logger = logging.getLogger(__name__)

# 创建数据库会话
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def download_pdf(paper: Paper) -> Optional[Path]:
    """
    下载论文PDF文件

    Args:
        paper: 论文对象

    Returns:
        下载的PDF文件路径，下载失败则返回None
    """
    # 检查论文是否已有本地PDF
    if paper.has_pdf:
        logger.info(f"论文 {paper.arxiv_id_v} 已存在本地PDF: {paper.local_pdf_path}")
        return Path(paper.local_pdf_path)

    # 确保PDF目录存在
    PDF_PATH.mkdir(exist_ok=True, parents=True)

    # 构建保存路径
    filename = f"{paper.arxiv_id_v.replace('/', '_')}.pdf"
    save_path = PDF_PATH / filename

    # 下载PDF
    try:
        logger.info(f"开始下载论文 {paper.arxiv_id_v} 的PDF...")
        response = requests.get(paper.pdf_url, stream=True, timeout=30)
        response.raise_for_status()

        # 保存文件
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 更新数据库中的本地路径
        db = get_db_session()
        db_paper = db.query(Paper).filter(Paper.arxiv_id == paper.arxiv_id).first()
        if db_paper:
            db_paper.local_pdf_path = str(save_path)
            db.commit()

        logger.info(f"论文 {paper.arxiv_id_v} 的PDF下载完成: {save_path}")
        return save_path

    except Exception as e:
        logger.error(f"下载论文 {paper.arxiv_id_v} 的PDF失败: {e}")
        # 清理可能的部分下载文件
        if save_path.exists():
            save_path.unlink()
        return None


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    从PDF文件中提取文本

    Args:
        pdf_path: PDF文件路径

    Returns:
        提取的文本内容
    """
    try:
        logger.info(f"从PDF提取文本: {pdf_path}")
        text = ""
        
        # 打开PDF文件
        with fitz.open(pdf_path) as doc:
            # 获取页数
            page_count = len(doc)
            
            # 如果不使用全文，只提取前几页（通常包含摘要）
            if not USE_FULL_TEXT:
                # 提取前2页或全部页面（如果页数少于2）
                max_pages = min(2, page_count)
                for page_num in range(max_pages):
                    page = doc[page_num]
                    page_text = page.get_text()
                    text += page_text
            else:
                # 提取全文
                for page_num in range(page_count):
                    page = doc[page_num]
                    page_text = page.get_text()
                    text += page_text
        
        # 清理文本（删除多余空白字符）
        text = re.sub(r'\s+', ' ', text).strip()
        
        logger.info(f"文本提取完成，长度: {len(text)}")
        return text
        
    except Exception as e:
        logger.error(f"提取PDF文本失败: {e}")
        return ""


def get_paper_text(paper: Paper) -> Optional[str]:
    """
    获取论文文本内容
    
    优先使用摘要，如果配置为使用全文，则下载并提取PDF内容
    
    Args:
        paper: 论文对象
        
    Returns:
        论文文本（摘要或全文）
    """
    # 如果不使用全文，直接返回摘要
    if not USE_FULL_TEXT:
        return paper.abstract
    
    # 如果使用全文，先检查是否有本地PDF
    pdf_path = None
    if paper.has_pdf:
        pdf_path = Path(paper.local_pdf_path)
    else:
        # 下载PDF
        pdf_path = download_pdf(paper)
    
    # 如果有PDF，提取文本
    if pdf_path and pdf_path.exists():
        full_text = extract_text_from_pdf(pdf_path)
        if full_text:
            return full_text
    
    # 如果无法获取全文，返回摘要
    logger.warning(f"无法获取论文 {paper.arxiv_id_v} 的全文，使用摘要")
    return paper.abstract


def download_missing_pdfs(limit: int = 0) -> int:
    """
    下载缺失的PDF文件
    
    Args:
        limit: 最大下载数量，0表示不限制
        
    Returns:
        下载的PDF文件数量
    """
    db = get_db_session()
    
    # 查询缺少PDF的论文
    query = db.query(Paper).filter(Paper.local_pdf_path.is_(None))
    
    if limit > 0:
        query = query.limit(limit)
    
    papers = query.all()
    logger.info(f"找到 {len(papers)} 篇缺少PDF的论文")
    
    # 下载PDF
    downloaded = 0
    for paper in papers:
        pdf_path = download_pdf(paper)
        if pdf_path:
            downloaded += 1
    
    logger.info(f"下载了 {downloaded} 篇论文的PDF")
    return downloaded


def main():
    """主函数"""
    logging.basicConfig(level=logging.INFO)
    logger.info("开始下载缺失的PDF文件...")
    downloaded = download_missing_pdfs()
    logger.info(f"共下载了 {downloaded} 篇论文的PDF")


if __name__ == "__main__":
    main() 