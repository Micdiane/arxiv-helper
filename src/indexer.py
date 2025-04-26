"""
论文索引构建模块

负责为论文生成向量表示，并构建Faiss索引用于语义搜索
"""

import logging
import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from .config import (
    DATABASE_URL,
    EMBEDDING_MODEL,
    FAISS_INDEX_FILE,
    FAISS_INDEX_TYPE,
    FAISS_NLIST,
    INDEX_PATH,
    DEFAULT_BATCH_SIZE
)
from .models import Paper
from .pdf_processor import get_paper_text

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


class PaperIndexer:
    """论文索引器"""

    def __init__(self):
        """初始化索引器"""
        self.model = None
        self.index = None
        self.id_map = {}  # 映射Faiss索引ID到ArXiv ID
        self.reverse_id_map = {}  # 映射ArXiv ID到Faiss索引ID

        # 确保索引目录存在
        INDEX_PATH.mkdir(exist_ok=True, parents=True)

        # 映射文件路径
        self.id_map_file = INDEX_PATH / "id_map.pkl"

        # 加载模型
        self._load_model()

        # 如果索引文件存在，则加载
        if FAISS_INDEX_FILE.exists() and self.id_map_file.exists():
            self._load_index()
        else:
            # 否则创建新索引
            self._create_index()

    def _load_model(self):
        """加载Sentence Transformer模型"""
        try:
            logger.info(f"加载Sentence Transformer模型: {EMBEDDING_MODEL}")
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("模型加载完成")
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            raise

    def _create_index(self):
        """创建新的Faiss索引"""
        try:
            logger.info(f"创建新的Faiss索引，类型: {FAISS_INDEX_TYPE}")
            
            # 获取向量维度
            d = self.model.get_sentence_embedding_dimension()
            logger.info(f"向量维度: {d}")
            
            # 根据配置创建不同类型的索引
            if FAISS_INDEX_TYPE == "Flat":
                # 精确但较慢的L2距离索引
                base_index = faiss.IndexFlatL2(d)
            elif FAISS_INDEX_TYPE == "IVFFlat":
                # 近似但较快的IVF索引
                quantizer = faiss.IndexFlatL2(d)
                base_index = faiss.IndexIVFFlat(quantizer, d, FAISS_NLIST)
                # 需要训练，但现在没有数据，稍后会处理
            else:
                # 默认使用精确索引
                logger.warning(f"未知的索引类型: {FAISS_INDEX_TYPE}，使用默认Flat索引")
                base_index = faiss.IndexFlatL2(d)
            
            # 使用IDMap包装基础索引，以便使用外部ID
            self.index = faiss.IndexIDMap(base_index)
            self.id_map = {}
            self.reverse_id_map = {}
            
            logger.info("创建索引完成")
        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            raise

    def _load_index(self):
        """加载保存的Faiss索引和ID映射"""
        try:
            logger.info(f"加载Faiss索引: {FAISS_INDEX_FILE}")
            self.index = faiss.read_index(str(FAISS_INDEX_FILE))
            
            logger.info(f"加载ID映射: {self.id_map_file}")
            with open(self.id_map_file, "rb") as f:
                id_maps = pickle.load(f)
                self.id_map = id_maps["id_map"]
                self.reverse_id_map = id_maps["reverse_id_map"]
            
            logger.info(f"索引加载完成，包含 {self.index.ntotal} 个向量")
        except Exception as e:
            logger.error(f"加载索引失败: {e}，创建新索引")
            self._create_index()

    def save_index(self):
        """保存索引到文件"""
        try:
            logger.info(f"保存Faiss索引: {FAISS_INDEX_FILE}")
            faiss.write_index(self.index, str(FAISS_INDEX_FILE))
            
            logger.info(f"保存ID映射: {self.id_map_file}")
            with open(self.id_map_file, "wb") as f:
                pickle.dump(
                    {
                        "id_map": self.id_map,
                        "reverse_id_map": self.reverse_id_map
                    },
                    f
                )
            
            logger.info("索引保存完成")
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
            raise

    def generate_embedding(self, text: str) -> np.ndarray:
        """为文本生成向量表示"""
        try:
            embedding = self.model.encode(text, show_progress_bar=False)
            return embedding
        except Exception as e:
            logger.error(f"生成向量失败: {e}")
            raise

    def add_paper_to_index(self, paper: Paper) -> bool:
        """
        将论文添加到索引
        
        Args:
            paper: 论文对象
            
        Returns:
            添加是否成功
        """
        try:
            # 如果论文已经在索引中，先移除
            if paper.arxiv_id in self.reverse_id_map:
                logger.info(f"论文 {paper.arxiv_id} 已存在于索引中，先移除")
                self.remove_paper_from_index(paper.arxiv_id)
            
            # 获取论文文本（根据配置使用摘要或全文）
            paper_text = get_paper_text(paper)
            
            if not paper_text:
                logger.error(f"论文 {paper.arxiv_id} 没有文本内容，无法添加到索引")
                return False
            
            # 生成向量
            embedding = self.generate_embedding(paper_text)
            
            # 分配索引ID
            if self.id_map:
                # 使用最大ID + 1
                index_id = max(self.id_map.keys()) + 1
            else:
                # 第一个条目
                index_id = 1
            
            # 更新ID映射
            self.id_map[index_id] = paper.arxiv_id
            self.reverse_id_map[paper.arxiv_id] = index_id
            
            # 添加到索引
            self.index.add_with_ids(
                np.array([embedding], dtype=np.float32),
                np.array([index_id], dtype=np.int64)
            )
            
            # 更新数据库中的向量化状态
            db = get_db_session()
            db_paper = db.query(Paper).filter(Paper.arxiv_id == paper.arxiv_id).first()
            if db_paper:
                db_paper.is_vectorized = True
                db.commit()
            
            logger.info(f"论文 {paper.arxiv_id} 已添加到索引，ID: {index_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加论文 {paper.arxiv_id} 到索引失败: {e}")
            return False

    def remove_paper_from_index(self, arxiv_id: str) -> bool:
        """
        从索引中移除论文
        
        Args:
            arxiv_id: 论文的ArXiv ID
            
        Returns:
            移除是否成功
        """
        try:
            if arxiv_id not in self.reverse_id_map:
                logger.warning(f"论文 {arxiv_id} 不在索引中，无需移除")
                return True
            
            # 获取索引ID
            index_id = self.reverse_id_map[arxiv_id]
            
            # 从索引中移除
            self.index.remove_ids(np.array([index_id], dtype=np.int64))
            
            # 更新映射
            del self.id_map[index_id]
            del self.reverse_id_map[arxiv_id]
            
            # 更新数据库中的向量化状态
            db = get_db_session()
            db_paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
            if db_paper:
                db_paper.is_vectorized = False
                db.commit()
            
            logger.info(f"论文 {arxiv_id} 已从索引中移除")
            return True
            
        except Exception as e:
            logger.error(f"从索引中移除论文 {arxiv_id} 失败: {e}")
            return False

    def find_similar_papers(
        self, query_embedding: np.ndarray, top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        查找与查询向量最相似的论文
        
        Args:
            query_embedding: 查询向量
            top_k: 返回的结果数量
            
        Returns:
            类似论文的ArXiv ID和相似度分数列表
        """
        try:
            # 确保索引不为空
            if self.index.ntotal == 0:
                logger.warning("索引为空，无法进行相似性搜索")
                return []
            
            # 查询向量需要是2D数组
            if query_embedding.ndim == 1:
                query_embedding = np.array([query_embedding], dtype=np.float32)
            
            # 在索引中搜索最近邻
            top_k = min(top_k, self.index.ntotal)  # 确保不超过索引中的向量数量
            distances, indices = self.index.search(query_embedding, top_k)
            
            # 将索引ID转换为ArXiv ID
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1:  # -1表示未找到
                    arxiv_id = self.id_map.get(int(idx))
                    if arxiv_id:
                        distance = distances[0][i]
                        results.append((arxiv_id, float(distance)))
            
            return results
            
        except Exception as e:
            logger.error(f"查找相似论文失败: {e}")
            return []

    def find_similar_papers_by_id(
        self, arxiv_id: str, top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        根据ArXiv ID查找相似论文
        
        Args:
            arxiv_id: 论文的ArXiv ID
            top_k: 返回的结果数量
            
        Returns:
            类似论文的ArXiv ID和相似度分数列表
        """
        try:
            db = get_db_session()
            paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
            
            if not paper:
                logger.error(f"找不到ArXiv ID为 {arxiv_id} 的论文")
                return []
            
            # 获取论文文本
            paper_text = get_paper_text(paper)
            
            if not paper_text:
                logger.error(f"论文 {arxiv_id} 没有文本内容，无法搜索相似论文")
                return []
            
            # 生成查询向量
            query_embedding = self.generate_embedding(paper_text)
            
            # 查找相似论文
            similar_papers = self.find_similar_papers(query_embedding, top_k + 1)  # +1因为可能包含查询论文本身
            
            # 过滤掉查询论文本身
            similar_papers = [(id, score) for id, score in similar_papers if id != arxiv_id]
            
            # 返回前top_k个结果
            return similar_papers[:top_k]
            
        except Exception as e:
            logger.error(f"根据ID查找相似论文失败: {e}")
            return []

    def find_similar_papers_by_text(
        self, query_text: str, top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        根据文本查询相似论文
        
        Args:
            query_text: 查询文本
            top_k: 返回的相似论文数量
            
        Returns:
            相似论文ID和相似度列表 [(arxiv_id, score), ...]
        """
        if not query_text.strip():
            logger.warning("查询文本为空")
            return []
            
        try:
            # 生成查询文本的向量
            query_embedding = self.generate_embedding(query_text)
            
            # 搜索相似论文
            return self.find_similar_papers(query_embedding, top_k)
            
        except Exception as e:
            logger.error(f"文本查询相似论文失败: {e}")
            return []

    def update_index(self, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
        """
        更新索引，处理未向量化的论文
        
        Args:
            batch_size: 每批处理的论文数量
            
        Returns:
            新添加到索引的论文数量
        """
        try:
            logger.info("开始更新索引...")
            db = get_db_session()
            
            # 获取未向量化的论文
            unvectorized_papers = db.query(Paper).filter(Paper.is_vectorized == False).limit(batch_size).all()
            
            if not unvectorized_papers:
                logger.info("没有找到需要向量化的论文")
                return 0
            
            logger.info(f"找到 {len(unvectorized_papers)} 篇未向量化的论文")
            
            # 训练索引（如果需要）
            if FAISS_INDEX_TYPE == "IVFFlat" and isinstance(self.index.index, faiss.IndexIVFFlat) and not self.index.is_trained:
                logger.info("IVF索引需要训练，获取训练数据...")
                
                # 获取一批论文用于训练
                sample_papers = unvectorized_papers[:min(100, len(unvectorized_papers))]
                training_vectors = []
                
                for paper in sample_papers:
                    paper_text = get_paper_text(paper)
                    if paper_text:
                        embedding = self.generate_embedding(paper_text)
                        training_vectors.append(embedding)
                
                if training_vectors:
                    logger.info(f"使用 {len(training_vectors)} 个向量训练索引...")
                    training_data = np.array(training_vectors, dtype=np.float32)
                    self.index.train(training_data)
                    logger.info("索引训练完成")
            
            # 添加论文到索引
            added_count = 0
            for paper in unvectorized_papers:
                success = self.add_paper_to_index(paper)
                if success:
                    added_count += 1
                
                # 每10篇保存一次索引
                if added_count > 0 and added_count % 10 == 0:
                    self.save_index()
            
            # 保存索引
            if added_count > 0:
                self.save_index()
            
            logger.info(f"索引更新完成，添加了 {added_count} 篇论文")
            return added_count
            
        except Exception as e:
            logger.error(f"更新索引失败: {e}")
            return 0


# 全局索引器实例
_indexer = None


def get_indexer() -> PaperIndexer:
    """获取索引器实例（单例模式）"""
    global _indexer
    if _indexer is None:
        _indexer = PaperIndexer()
    return _indexer


def main():
    """主函数，用于独立更新索引"""
    logging.basicConfig(level=logging.INFO)
    logger.info("开始更新论文索引...")
    
    indexer = get_indexer()
    added_count = indexer.update_index()
    
    logger.info(f"索引更新完成，添加了 {added_count} 篇论文")


if __name__ == "__main__":
    main() 