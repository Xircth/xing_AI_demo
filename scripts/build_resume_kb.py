import os
import json
# Add parent directory to sys.path to find src module
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from src.utils import Config, setup_logger
from langchain.retrievers import BM25Retriever, EnsembleRetriever

# 初始化配置和日志
cfg = Config()
logger = setup_logger('log')

# 读取简历内容 (adjust path relative to parent dir)
resume_file_path = os.path.join("..", "RAG.md")
with open(resume_file_path, "r", encoding="utf-8") as f:
    resume_text = f.read()

# 文本分块
text_splitter = CharacterTextSplitter(
    separator="\n## ",  # 按大标题分割
    chunk_size=500,
    chunk_overlap=100,
    length_function=len
)

# 一级分割
main_chunks = text_splitter.split_text("## " + resume_text)

# 细粒度分割
text_splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=200,
    chunk_overlap=50,
    length_function=len
)
chunks = []
for chunk in main_chunks:
    chunks.extend(text_splitter.split_text(chunk))

logger.info(f"简历共分割为 {len(chunks)} 个文本块")

# 嵌入向量化
embeddings = HuggingFaceEmbeddings(
    model_name=cfg.get('embedding')['model_name'],
    model_kwargs={'device': 'cpu'}
)

# 创建向量存储库 (adjust path relative to parent dir)
vector_store_path_relative = cfg.get('vector_db')['path']
vector_store_path = os.path.join("..", vector_store_path_relative)
os.makedirs(vector_store_path, exist_ok=True)

# 构建向量索引
vector_store = FAISS.from_texts(chunks, embeddings)
vector_store.save_local(vector_store_path)

# 保存原始文本块以便跟踪
with open(os.path.join(vector_store_path, "resume_chunks.json"), "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

logger.info(f"简历知识库已创建并保存到 {vector_store_path}")

# 在检索时混合使用关键词和向量检索

# 关键词检索器
bm25_retriever = BM25Retriever.from_texts(chunks)
bm25_retriever.k = 5

# 向量检索器
vector_retriever = vector_store.as_retriever(search_kwargs={"k": 5})

# 混合检索器
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.3, 0.7]
)

def main():
    logger = setup_logger('log')
    logger.info("开始构建简历知识库")