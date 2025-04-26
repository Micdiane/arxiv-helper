#!/usr/bin/env python3
"""
初始化数据库

创建所需的数据库表结构并进行初始设置
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

from src.models import init_db


def main():
    """初始化数据库"""
    try:
        logger.info("开始初始化数据库...")
        engine = init_db()
        logger.info(f"数据库初始化完成: {engine.url}")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 