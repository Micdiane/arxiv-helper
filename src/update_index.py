#!/usr/bin/env python3
"""
更新论文索引

1. 可选：下载PDF文件（默认不下载）
2. 为未向量化的论文生成向量并添加到Faiss索引
"""

import logging
import sys
from pathlib import Path
import argparse

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
from src.config import DEFAULT_BATCH_SIZE

parser = argparse.ArgumentParser()
parser.add_argument("--download-pdf", action="store_true", 
                   help="下载PDF文件（默认不下载，仅使用摘要生成索引）")
parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                   help=f"每次处理的论文批次大小，默认为{DEFAULT_BATCH_SIZE}")
args = parser.parse_args()

def main():
    """主函数"""
    try:
        # 仅当指定--download-pdf参数时才下载PDF
        if args.download_pdf:
            logger.info("开始下载缺失的PDF文件...")
            download_missing_pdfs()
            logger.info("PDF下载完成")
        else:
            logger.info("跳过PDF下载，仅使用摘要生成索引")
        
        # 更新索引
        logger.info(f"开始更新论文索引，批次大小: {args.batch_size}...")
        indexer = get_indexer()
        added_count = indexer.update_index(batch_size=args.batch_size)
        logger.info(f"索引更新完成，添加了 {added_count} 篇论文")
        
    except Exception as e:
        logger.error(f"更新索引失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 