import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from .config import DATABASE_URL, PDF_PATH

Base = declarative_base()


class Paper(Base):
    """论文数据模型"""

    __tablename__ = "papers"

    # 主键，ArXiv ID，例如 '2301.12345'
    arxiv_id = Column(String, primary_key=True)
    
    # 论文版本号
    version = Column(Integer, default=1)
    
    # 论文标题
    title = Column(String, nullable=False)
    
    # 作者列表，存储为JSON字符串
    authors = Column(String, nullable=False)
    
    # 论文摘要
    abstract = Column(String, nullable=False)
    
    # 发布日期
    published_date = Column(DateTime, nullable=False)
    
    # 更新日期
    updated_date = Column(DateTime, nullable=False)
    
    # 主要类别
    primary_category = Column(String, nullable=False)
    
    # PDF URL
    pdf_url = Column(String, nullable=False)
    
    # 本地PDF文件路径
    local_pdf_path = Column(String, nullable=True)
    
    # 是否已向量化并索引
    is_vectorized = Column(Boolean, default=False)
    
    # 是否已收藏
    is_favorite = Column(Boolean, default=False)
    
    # 添加时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    @property
    def authors_list(self) -> List[str]:
        """获取作者列表"""
        return json.loads(self.authors)

    @property
    def pdf_path(self) -> Optional[Path]:
        """获取本地PDF文件路径"""
        if self.local_pdf_path:
            return Path(self.local_pdf_path)
        return None

    @property
    def arxiv_id_v(self) -> str:
        """获取带版本号的ArXiv ID"""
        return f"{self.arxiv_id}v{self.version}"

    @property
    def arxiv_url(self) -> str:
        """获取ArXiv页面URL"""
        return f"https://arxiv.org/abs/{self.arxiv_id_v}"

    @property
    def has_pdf(self) -> bool:
        """检查是否有本地PDF文件"""
        if self.local_pdf_path:
            return Path(self.local_pdf_path).exists()
        return False

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "arxiv_id": self.arxiv_id,
            "version": self.version,
            "title": self.title,
            "authors": self.authors_list,
            "abstract": self.abstract,
            "published_date": self.published_date.isoformat(),
            "updated_date": self.updated_date.isoformat(),
            "primary_category": self.primary_category,
            "pdf_url": self.pdf_url,
            "local_pdf_path": self.local_pdf_path,
            "is_vectorized": self.is_vectorized,
            "is_favorite": self.is_favorite,
            "arxiv_id_v": self.arxiv_id_v,
            "arxiv_url": self.arxiv_url,
            "has_pdf": self.has_pdf,
        }


# 创建数据库引擎和表
def init_db():
    """初始化数据库"""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return engine 