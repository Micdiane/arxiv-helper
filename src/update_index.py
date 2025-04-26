#!/usr/bin/env python3
"""
更新论文索引

1. 下载缺失的PDF文件
2. 为未向量化的论文生成向量并添加到Faiss索引
"""

import logging
import sys
from pathlib import Path

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

from src.pdf_processor import download_missing_pdfs
from src.indexer import get_indexer


def main():
    """主函数"""
    try:
        # 下载缺失的PDF
        logger.info("开始下载缺失的PDF文件...")
        downloaded = download_missing_pdfs()
        logger.info(f"PDF下载完成，共下载 {downloaded} 篇论文的PDF")
        
        # 更新索引
        logger.info("开始更新论文索引...")
        indexer = get_indexer()
        added_count = indexer.update_index()
        logger.info(f"索引更新完成，添加了 {added_count} 篇论文")
        
    except Exception as e:
        logger.error(f"更新索引失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 