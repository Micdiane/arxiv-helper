# <p align="center">📚 ArXiv Helper</p>

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![ArXiv](https://img.shields.io/badge/ArXiv-API-B31B1B?style=flat&logo=arxiv&logoColor=white)](https://arxiv.org/help/api/index)
[![Sentence Transformers](https://img.shields.io/badge/Sentence_Transformers-2.2+-FF6F00?style=flat&logo=pytorch&logoColor=white)](https://www.sbert.net/)
[![Faiss](https://img.shields.io/badge/Faiss-1.7+-4285F4?style=flat)](https://github.com/facebookresearch/faiss)

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

<p align="center">
  <b>一个轻量级、本地化部署的Web应用，帮助用户高效浏览、搜索和管理arXiv论文</b>
</p>

<p align="center">
  <a href="#功能特点">✨ 功能</a> •
  <a href="#安装">🔧 安装</a> •
  <a href="#使用方法">📖 使用</a> •
  <a href="#运行示例">🖼️ 示例</a> •
  <a href="#详细配置参数">⚙️ 配置</a> •
  <a href="#常见问题及解决方案">💡 常见问题</a> •
  <a href="#实现原理">🔍 原理</a> •
  <a href="#性能优化建议">🚀 优化</a>
</p>

---

## 功能特点

- **论文获取与存储**: 从arXiv API获取指定领域的论文元数据（标题、作者、摘要等），存储到本地SQLite数据库
- **语义向量搜索**: 使用预训练的Sentence Transformer模型为论文摘要生成语义向量，通过Faiss快速查找相似论文
- **简洁Web界面**: 提供直观的界面浏览最新论文、搜索和管理收藏
- **原文访问选项**: 在Web界面中提供ArXiv原文链接和PDF下载按钮，按需获取全文
- **本地化部署**: 完全在本地运行，无需外部服务依赖，保护隐私

## 安装

### 环境要求

- Python 3.8+
- 必要的Python包（见requirements.txt）

### 安装步骤

1. **克隆本仓库**：
```bash
git clone https://github.com/yourusername/arxiv-helper.git
cd arxiv-helper
```

2. **创建并激活虚拟环境**（推荐）：
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**：
```bash
pip install -r requirements.txt
```

4. **配置应用**：
复制`.env.example`为`.env`并编辑配置项

## 使用方法

### 初始化数据库

```bash
python src/initialize_db.py
```

### 获取论文元数据

```bash
python src/fetch_papers.py
```

### 构建向量索引（默认仅使用摘要）

```bash
python src/update_index.py
```

如果您想同时下载PDF文件，可以添加`--download-pdf`参数：
```bash
python src/update_index.py --download-pdf
```

### 启动Web服务

```bash
python src/main.py
```
或者
```bash
uvicorn src.main:app --reload
```

访问 http://127.0.0.1:8000 使用应用

## 运行示例

以下是ArXiv Helper应用的运行截图和示例：

### 主页 - 最新论文列表
![主页](screenshots/homepage.png)

### 论文详情页面
![论文详情](screenshots/paper_detail.png)

### 语义搜索结果
![搜索结果](screenshots/search_results.png)

### 相似论文推荐
![相似论文](screenshots/similar_papers.png)

### 收藏夹
![收藏夹](screenshots/library.png)

### 示例论文

您可以查看[示例论文PDF](examples/example.pdf)来了解系统如何处理和展示论文内容。

## Web界面功能

系统提供了直观的Web界面，主要功能包括：

### 浏览论文
- 按时间顺序查看最新论文
- 分页浏览所有已获取的论文

### 论文详情
- 查看论文的完整元数据：标题、作者、摘要、发布日期等
- 提供ArXiv原文链接，直接跳转到ArXiv网站
- 提供PDF下载按钮，可按需下载论文全文

### 搜索功能
- 关键词搜索：在标题和摘要中搜索
- 语义相似度搜索：查找与当前论文语义上相似的其他论文

### 收藏管理
- 将感兴趣的论文添加到收藏夹
- 在专门的收藏页面集中查看已收藏论文

## 详细配置参数

在`.env`文件中可以配置以下选项：

### 应用基本配置
- `APP_HOST`: 应用监听地址，默认为"127.0.0.1"
- `APP_PORT`: 应用端口，默认为8000
- `DEBUG`: 是否开启调试模式，默认为True

### 数据配置
- `DATABASE_URL`: 数据库URL，默认为"sqlite:///./data/papers.db"
- `PDF_PATH`: PDF存储路径，默认为"./data/pdf"（仅当使用PDF下载功能时有效）
- `INDEX_PATH`: 索引文件存储路径，默认为"./data/index"

### ArXiv API配置
- `ARXIV_CATEGORIES`: arXiv类别，用逗号分隔，如"cs.AI,cs.CL,cs.CV,cs.LG"
- `MAX_RESULTS_PER_QUERY`: 每次API请求获取的最大论文数量，默认为100
- `DAYS_TO_FETCH`: 获取过去几天的论文，默认为7（建议初次使用设置为30，以获取足够的论文）

### 向量化配置
- `EMBEDDING_MODEL`: 使用的Sentence Transformer模型，默认为"all-MiniLM-L6-v2"
  - 轻量级选项: "paraphrase-MiniLM-L3-v2"（快速但精度较低）
  - 平衡选项: "all-MiniLM-L6-v2"（默认，平衡速度和精度）
  - 高精度选项: "all-mpnet-base-v2"（高精度但计算较慢）
- `USE_FULL_TEXT`: 是否使用全文生成向量，默认为False（仅使用摘要，若设为True，需先下载PDF）
- `FAISS_INDEX_TYPE`: Faiss索引类型，可选"Flat"或"IVFFlat"
  - "Flat": 最准确但速度较慢，适合小型数据集（<10,000篇论文）
  - "IVFFlat": 速度更快但可能略微降低精度，适合大型数据集
- `FAISS_NLIST`: 聚类数量，仅当`FAISS_INDEX_TYPE`为"IVFFlat"时使用，默认为100

## 常见问题及解决方案

### 问题: 添加索引数量少
**症状**: 运行`update_index.py`时，添加到索引中的论文数量很少。

**解决方案**:
1. 重置所有论文的向量化状态，强制重建索引：
   ```python
   from src.models import get_db_session, Paper
   db = get_db_session()
   db.query(Paper).update({Paper.is_vectorized: 0})
   db.commit()
   ```
2. 确保数据库中有足够的论文数量，可通过设置更大的`DAYS_TO_FETCH`值获取更多论文

### 问题: 无法获取ArXiv论文
**症状**: 运行`fetch_papers.py`时没有获取到任何论文，或出现API错误。

**解决方案**:
1. 检查网络连接是否正常
2. 修改`fetcher.py`中的查询方法，去除日期过滤逻辑，使用更简单的查询：
   ```python
   query = f"search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending"
   ```
3. 增加`DAYS_TO_FETCH`参数，如设置为30天，以获取更多论文
4. 在每次请求间添加延时（代码中已实现，间隔3秒）避免API限制

### 问题: FAISS_NLIST设置导致初始化失败
**症状**: 启动应用时出现Faiss相关错误。

**解决方案**:
1. 确保`.env`文件中的`FAISS_NLIST=100`后面没有空格或注释
2. 对于小型数据集，可以使用`FAISS_INDEX_TYPE=Flat`绕过这个问题

### 问题: 依赖库安装失败
**症状**: 执行`pip install -r requirements.txt`时某些库安装失败。

**解决方案**:
1. 尝试单独安装关键依赖: `pip install fastapi uvicorn sqlalchemy feedparser sentence-transformers faiss-cpu pymupdf`
2. 对于Windows用户，某些库可能需要先安装对应的C++编译器

### 问题: 语义搜索不准确
**症状**: 搜索结果与预期不符。

**解决方案**:
1. 使用更高质量的模型，如设置`EMBEDDING_MODEL=all-mpnet-base-v2`
2. 考虑启用全文索引：`USE_FULL_TEXT=True`（需要先下载PDF文件）
3. 确保有足够数量的论文在数据库中

## 实现原理

### 数据流程
1. **获取论文**: 通过ArXiv API获取论文元数据（标题、作者、摘要等），保存到SQLite数据库
2. **向量化**: 使用预训练的Sentence Transformer模型将论文摘要转换为高维向量
3. **索引构建**: 使用Faiss库构建向量索引，支持高效的相似性搜索
4. **Web界面**: 通过FastAPI提供REST API，使用Jinja2模板渲染前端界面
5. **原文访问**: 提供ArXiv链接和可选的PDF下载功能，按需获取全文

### 关键技术
- **语义搜索**: 不同于传统的关键词匹配，语义搜索能够理解上下文和概念间的关系
- **近似最近邻搜索**: Faiss库实现高效的向量相似性搜索，即使面对大规模数据集也能保持快速响应
- **增量更新**: 系统支持增量获取新论文和更新索引，无需重建整个数据库

## 性能优化建议

### 向量搜索优化
- 对于小型数据集(<5,000篇论文)，使用`FAISS_INDEX_TYPE=Flat`获得最准确的结果
- 对于中型数据集(5,000-50,000篇论文)，使用`FAISS_INDEX_TYPE=IVFFlat`和`FAISS_NLIST=100`平衡速度和精度
- 对于大型数据集(>50,000篇论文)，使用`FAISS_INDEX_TYPE=IVFFlat`和更大的`FAISS_NLIST`值(如400或1000)

### GPU加速
默认使用CPU版本的Faiss库。如果有支持CUDA的NVIDIA GPU，可以获得显著的性能提升：
1. 卸载CPU版本: `pip uninstall faiss-cpu`
2. 安装GPU版本: `pip install faiss-gpu`

无需更改代码，系统会自动使用GPU进行向量计算和搜索。

### 内存优化
- 如果内存有限，使用更小的模型如`paraphrase-MiniLM-L3-v2`
- 保持`USE_FULL_TEXT=False`仅使用摘要生成向量
- 考虑定期清理旧论文，特别是在长期运行的系统中

## 许可证

[MIT](LICENSE) © 2025 
