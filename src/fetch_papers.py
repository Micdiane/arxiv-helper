#!/usr/bin/env python3
"""
获取ArXiv论文

从ArXiv API获取指定类别的最新论文并保存到数据库
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

from src.fetcher import fetch_all_categories


def main():
    """主函数"""
    try:
        logger.info("开始获取ArXiv论文...")
        total_saved = fetch_all_categories()
        logger.info(f"论文获取完成，共保存 {total_saved} 篇论文")
    except Exception as e:
        logger.error(f"论文获取失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 