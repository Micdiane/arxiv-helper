import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 应用基本配置
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/papers.db")

# ArXiv API配置
ARXIV_CATEGORIES = os.getenv("ARXIV_CATEGORIES", "cs.AI,cs.CL,cs.CV,cs.LG").split(",")
MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "100"))
DAYS_TO_FETCH = int(os.getenv("DAYS_TO_FETCH", "100"))

# 文件存储路径
PDF_PATH = Path(os.getenv("PDF_PATH", "./data/pdf")).resolve()
INDEX_PATH = Path(os.getenv("INDEX_PATH", "./data/index")).resolve()

# 向量化配置
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
USE_FULL_TEXT = os.getenv("USE_FULL_TEXT", "False").lower() in ("true", "1", "t")
FAISS_INDEX_TYPE = os.getenv("FAISS_INDEX_TYPE", "IVFFlat")
FAISS_NLIST = int(os.getenv("FAISS_NLIST", "100"))
DEFAULT_BATCH_SIZE = int(os.getenv("DEFAULT_BATCH_SIZE", "50"))

# 确保数据目录存在
PDF_PATH.mkdir(exist_ok=True, parents=True)
INDEX_PATH.mkdir(exist_ok=True, parents=True)

# Faiss索引文件路径
FAISS_INDEX_FILE = INDEX_PATH / "papers.index"

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs")).resolve()
LOG_DIR.mkdir(exist_ok=True, parents=True) 