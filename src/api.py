"""
API模块

提供Web API接口用于获取和搜索论文
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, func, desc, or_
from sqlalchemy.orm import Session, sessionmaker

from .config import DATABASE_URL
from .indexer import get_indexer
from .models import Paper

# 设置日志
logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建API路由
router = APIRouter()


def get_db():
    """依赖函数，获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic模型用于API请求和响应
class PaperBase(BaseModel):
    """论文基本模型"""
    arxiv_id: str
    version: int
    title: str
    authors: List[str]
    abstract: str
    published_date: str
    updated_date: str
    primary_category: str
    arxiv_url: str
    pdf_url: str
    has_pdf: bool
    is_favorite: bool
    is_vectorized: bool


class PaperList(BaseModel):
    """论文列表响应模型"""
    papers: List[PaperBase]
    total: int
    skip: int
    limit: int


class SimilarPaperList(BaseModel):
    """相似论文列表响应模型"""
    papers: List[PaperBase]
    query_id: str
    total: int


class SearchResult(BaseModel):
    """搜索结果响应模型"""
    papers: List[PaperBase]
    query: str
    total: int


class ToggleFavoriteResponse(BaseModel):
    """切换收藏响应模型"""
    arxiv_id: str
    is_favorite: bool


@router.get("/papers", response_model=PaperList)
async def get_papers(
    skip: int = Query(0, ge=0, description="跳过的数量"),
    limit: int = Query(50, ge=1, le=100, description="返回的数量"),
    sort: str = Query("date", description="排序方式: date 或 relevance"),
    favorite_only: bool = Query(False, description="仅显示收藏的论文"),
    db: Session = Depends(get_db),
):
    """
    获取论文列表，支持分页、排序和筛选
    """
    try:
        # 构建基本查询
        query = db.query(Paper)
        
        # 筛选收藏的论文
        if favorite_only:
            query = query.filter(Paper.is_favorite == True)
        
        # 计算总数
        total = query.count()
        
        # 应用排序
        if sort == "date":
            query = query.order_by(desc(Paper.published_date))
        else:  # relevance 或其他，暂时按ID排序
            query = query.order_by(desc(Paper.created_at))
        
        # 应用分页
        papers = query.offset(skip).limit(limit).all()
        
        # 转换为API模型
        result = {
            "papers": [paper_to_dict(paper) for paper in papers],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
        return result
    
    except Exception as e:
        logger.error(f"获取论文列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取论文列表失败: {str(e)}")


@router.get("/search", response_model=SearchResult)
async def search_papers(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回的数量"),
    db: Session = Depends(get_db),
):
    """
    搜索论文，支持标题和摘要的关键词搜索
    """
    try:
        # 构建搜索查询
        query = db.query(Paper).filter(
            or_(
                Paper.title.ilike(f"%{q}%"),
                Paper.abstract.ilike(f"%{q}%"),
            )
        ).order_by(desc(Paper.published_date))
        
        # 计算总数
        total = query.count()
        
        # 应用限制
        papers = query.limit(limit).all()
        
        # 转换为API模型
        result = {
            "papers": [paper_to_dict(paper) for paper in papers],
            "query": q,
            "total": total,
        }
        
        return result
    
    except Exception as e:
        logger.error(f"搜索论文失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索论文失败: {str(e)}")


@router.get("/similar/{arxiv_id}", response_model=SimilarPaperList)
async def get_similar_papers(
    arxiv_id: str = Path(..., description="论文的ArXiv ID"),
    k: int = Query(10, ge=1, le=50, description="返回的相似论文数量"),
    db: Session = Depends(get_db),
):
    """
    获取与指定论文相似的论文列表
    """
    try:
        # 清理ArXiv ID（可能包含版本号）
        clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
        
        # 检查论文是否存在
        paper = db.query(Paper).filter(Paper.arxiv_id == clean_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail=f"未找到ArXiv ID为 {clean_id} 的论文")
        
        # 获取索引器
        indexer = get_indexer()
        
        # 查找相似论文
        similar_paper_ids = indexer.find_similar_papers_by_id(clean_id, k)
        
        if not similar_paper_ids:
            # 如果没有相似论文（可能是索引为空），返回空列表
            return {"papers": [], "query_id": clean_id, "total": 0}
        
        # 提取ArXiv ID
        arxiv_ids = [paper_id for paper_id, _ in similar_paper_ids]
        
        # 从数据库获取完整论文信息
        similar_papers = db.query(Paper).filter(Paper.arxiv_id.in_(arxiv_ids)).all()
        
        # 按相似度排序
        id_to_score = {paper_id: score for paper_id, score in similar_paper_ids}
        sorted_papers = sorted(
            similar_papers,
            key=lambda p: id_to_score.get(p.arxiv_id, float("inf"))
        )
        
        # 转换为API模型
        result = {
            "papers": [paper_to_dict(paper) for paper in sorted_papers],
            "query_id": clean_id,
            "total": len(sorted_papers),
        }
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取相似论文失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取相似论文失败: {str(e)}")


@router.get("/semantic-search", response_model=SearchResult)
async def semantic_search(
    q: str = Query(..., min_length=1, description="搜索文本"),
    k: int = Query(10, ge=1, le=50, description="返回的论文数量"),
    db: Session = Depends(get_db),
):
    """
    使用语义搜索查找与查询文本相似的论文
    """
    try:
        # 获取索引器
        indexer = get_indexer()
        
        # 语义搜索
        similar_paper_ids = indexer.find_similar_papers_by_text(q, k)
        
        if not similar_paper_ids:
            # 如果没有相似论文，返回空列表
            return {"papers": [], "query": q, "total": 0}
        
        # 提取ArXiv ID
        arxiv_ids = [paper_id for paper_id, _ in similar_paper_ids]
        
        # 从数据库获取完整论文信息
        similar_papers = db.query(Paper).filter(Paper.arxiv_id.in_(arxiv_ids)).all()
        
        # 按相似度排序
        id_to_score = {paper_id: score for paper_id, score in similar_paper_ids}
        sorted_papers = sorted(
            similar_papers,
            key=lambda p: id_to_score.get(p.arxiv_id, float("inf"))
        )
        
        # 转换为API模型
        result = {
            "papers": [paper_to_dict(paper) for paper in sorted_papers],
            "query": q,
            "total": len(sorted_papers),
        }
        
        return result
    
    except Exception as e:
        logger.error(f"语义搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"语义搜索失败: {str(e)}")


@router.get("/paper/{arxiv_id}", response_model=PaperBase)
async def get_paper(
    arxiv_id: str = Path(..., description="论文的ArXiv ID"),
    db: Session = Depends(get_db),
):
    """
    获取单篇论文的详细信息
    """
    try:
        # 清理ArXiv ID（可能包含版本号）
        if "v" in arxiv_id:
            clean_id = arxiv_id.split("v")[0]
            version = int(arxiv_id.split("v")[1])
            paper = db.query(Paper).filter(
                Paper.arxiv_id == clean_id, Paper.version == version
            ).first()
        else:
            # 如果没有指定版本，返回最新版本
            paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
        
        if not paper:
            raise HTTPException(status_code=404, detail=f"未找到ArXiv ID为 {arxiv_id} 的论文")
        
        # 转换为API模型
        return paper_to_dict(paper)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取论文详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取论文详情失败: {str(e)}")


@router.post("/library/{arxiv_id}/toggle", response_model=ToggleFavoriteResponse)
async def toggle_favorite(
    arxiv_id: str = Path(..., description="论文的ArXiv ID"),
    db: Session = Depends(get_db),
):
    """
    切换论文的收藏状态
    """
    try:
        # 清理ArXiv ID（可能包含版本号）
        clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
        
        # 查找论文
        paper = db.query(Paper).filter(Paper.arxiv_id == clean_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail=f"未找到ArXiv ID为 {clean_id} 的论文")
        
        # 切换收藏状态
        paper.is_favorite = not paper.is_favorite
        db.commit()
        
        return {"arxiv_id": clean_id, "is_favorite": paper.is_favorite}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换收藏状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"切换收藏状态失败: {str(e)}")


@router.get("/library", response_model=PaperList)
async def get_library(
    skip: int = Query(0, ge=0, description="跳过的数量"),
    limit: int = Query(50, ge=1, le=100, description="返回的数量"),
    db: Session = Depends(get_db),
):
    """
    获取收藏夹中的论文
    """
    try:
        # 构建查询
        query = db.query(Paper).filter(Paper.is_favorite == True)
        
        # 计算总数
        total = query.count()
        
        # 应用排序和分页
        papers = query.order_by(desc(Paper.updated_at)).offset(skip).limit(limit).all()
        
        # 转换为API模型
        result = {
            "papers": [paper_to_dict(paper) for paper in papers],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
        return result
    
    except Exception as e:
        logger.error(f"获取收藏夹失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取收藏夹失败: {str(e)}")


def paper_to_dict(paper: Paper) -> dict:
    """
    将Paper对象转换为API响应字典
    """
    return {
        "arxiv_id": paper.arxiv_id,
        "version": paper.version,
        "title": paper.title,
        "authors": paper.authors_list,
        "abstract": paper.abstract,
        "published_date": paper.published_date.isoformat(),
        "updated_date": paper.updated_date.isoformat(),
        "primary_category": paper.primary_category,
        "arxiv_url": paper.arxiv_url,
        "pdf_url": paper.pdf_url,
        "has_pdf": paper.has_pdf,
        "is_favorite": paper.is_favorite,
        "is_vectorized": paper.is_vectorized,
    } 