"""
ArXiv论文获取模块

负责从ArXiv API获取论文元数据并保存到数据库
"""

import datetime
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Union

import feedparser
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import (
    ARXIV_CATEGORIES,
    DATABASE_URL,
    DAYS_TO_FETCH,
    MAX_RESULTS_PER_QUERY,
)
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


def parse_arxiv_date(date_str: str) -> datetime.datetime:
    """解析ArXiv日期字符串为datetime对象"""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        try:
            return datetime.datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
        except ValueError:
            logger.warning(f"无法解析日期: {date_str}，使用当前时间")
            return datetime.datetime.now()


def fetch_papers_by_category(
    category: str, days: int = 30, max_results: int = 100
) -> List[Dict]:
    """
    从ArXiv API获取指定类别的论文

    Args:
        category: ArXiv类别，如'cs.AI'
        days: 获取过去几天的论文，默认为30天
        max_results: 最大结果数量

    Returns:
        论文元数据列表
    """
    logger.info(f"获取类别 {category} 的论文，过去 {days} 天，最大 {max_results} 篇")

    # 构建查询URL - 使用更简单的查询，不使用日期过滤
    base_url = "http://export.arxiv.org/api/query?"
    query = f"search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending"
    url = f"{base_url}{query}&start=0&max_results={max_results}"

    # 发送请求
    try:
        logger.info(f"请求URL: {url}")
        response = feedparser.parse(url)
        if not response.entries:
            logger.warning(f"类别 {category} 没有找到论文")
            return []

        # 处理结果
        papers = []
        current_time = datetime.datetime.now()
        cutoff_date = current_time - datetime.timedelta(days=days)
        
        for entry in response.entries:
            # 解析日期
            published_date = parse_arxiv_date(entry.published)
            
            # 过滤掉早于截止日期的论文
            if published_date < cutoff_date:
                logger.debug(f"跳过较旧的论文: {entry.title} (发布于 {published_date})")
                continue
                
            # 解析作者
            authors = [author.name for author in entry.authors]

            # 解析分类
            primary_category = entry.arxiv_primary_category["term"]

            # 解析ArXiv ID和版本
            arxiv_id, version = parse_arxiv_id_and_version(entry.id)

            updated_date = parse_arxiv_date(entry.updated)

            # 构建论文数据
            paper = {
                "arxiv_id": arxiv_id,
                "version": version,
                "title": entry.title.replace("\n", " ").strip(),
                "authors": json.dumps(authors),
                "abstract": entry.summary.replace("\n", " ").strip(),
                "published_date": published_date,
                "updated_date": updated_date,
                "primary_category": primary_category,
                "pdf_url": f"http://arxiv.org/pdf/{arxiv_id}v{version}.pdf",
            }
            papers.append(paper)

        logger.info(f"已获取 {len(papers)} 篇 {category} 类别的论文")
        return papers

    except Exception as e:
        logger.error(f"获取论文失败: {e}")
        return []


def parse_arxiv_id_and_version(id_url: str) -> Tuple[str, int]:
    """从ArXiv ID URL解析ID和版本"""
    # 示例ID: http://arxiv.org/abs/2301.12345v1
    try:
        # 获取最后部分
        id_part = id_url.split("/")[-1]
        
        # 分离ID和版本
        if "v" in id_part:
            arxiv_id, version_str = id_part.split("v")
            version = int(version_str)
        else:
            arxiv_id = id_part
            version = 1
            
        return arxiv_id, version
    except Exception as e:
        logger.error(f"解析ArXiv ID失败: {id_url}, {e}")
        # 返回默认值
        return id_url, 1


def save_papers_to_db(papers: List[Dict]) -> int:
    """
    将论文保存到数据库

    Args:
        papers: 论文元数据列表

    Returns:
        保存的论文数量
    """
    if not papers:
        return 0

    try:
        db = get_db_session()
        saved_count = 0

        for paper_data in papers:
            # 检查论文是否已存在
            existing_paper = db.query(Paper).filter(Paper.arxiv_id == paper_data["arxiv_id"]).first()

            if existing_paper:
                # 如果新版本高于现有版本，则更新
                if paper_data["version"] > existing_paper.version:
                    logger.debug(f"更新论文 {paper_data['arxiv_id']} 从版本 {existing_paper.version} 到 {paper_data['version']}")
                    
                    # 更新现有论文
                    for key, value in paper_data.items():
                        setattr(existing_paper, key, value)
                    
                    saved_count += 1
            else:
                # 创建新论文
                new_paper = Paper(**paper_data)
                db.add(new_paper)
                saved_count += 1

        db.commit()
        logger.info(f"已保存 {saved_count} 篇论文到数据库")
        return saved_count

    except Exception as e:
        logger.error(f"保存论文到数据库失败: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


def fetch_all_categories() -> int:
    """
    获取所有配置的类别的论文

    Returns:
        保存的论文总数
    """
    total_saved = 0
    
    for category in ARXIV_CATEGORIES:
        logger.info(f"获取类别 {category} 的论文")
        papers = fetch_papers_by_category(
            category, 
            days=DAYS_TO_FETCH, 
            max_results=MAX_RESULTS_PER_QUERY
        )
        
        # 保存到数据库
        saved = save_papers_to_db(papers)
        total_saved += saved
        
        # 避免请求过于频繁
        time.sleep(3)
    
    return total_saved


def main():
    """主函数"""
    logger.info("开始获取论文...")
    total_saved = fetch_all_categories()
    logger.info(f"总共保存了 {total_saved} 篇论文")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main() 