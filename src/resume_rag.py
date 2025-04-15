import os
from PIL import Image
import pytesseract
import torch # 导入 torch
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from src.utils import Config, setup_logger

class ResumeRAG:
    def __init__(self):
        self.cfg = Config() # 获取配置
        self.embedding_cfg = self.cfg.get('embedding')
        self.vector_db_path = self.cfg.get('vector_db')['path']
        self.logger = setup_logger('log')
        self.embeddings = None
        self.vector_db = None
        # 确定嵌入模型设备 (优先配置, 否则默认CPU)
        self.embedding_device = self.embedding_cfg.get('device', 'cpu') 
        self.logger.info(f"嵌入模型将加载到设备: {self.embedding_device}")
        self.initialize() # 初始化嵌入模型和向量库
        
    def initialize(self):
        """初始化嵌入模型和向量库"""
        try:
            self.logger.info(f"初始化嵌入模型: {self.embedding_cfg['model_name']} on device: {self.embedding_device}")
            # 确保faiss-cpu已安装
            try:
                import faiss
                self.logger.info("FAISS库已加载")
            except ImportError:
                self.logger.error("缺少FAISS库，尝试安装faiss-cpu...")
                import subprocess
                subprocess.check_call(["pip", "install", "faiss-cpu", "--no-cache-dir"])
                self.logger.info("FAISS安装完成，请重启应用")
                raise ImportError("需要重启应用以加载新安装的依赖")
                
            # 加载嵌入模型, 明确指定设备
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_cfg['model_name'],
                model_kwargs={'device': self.embedding_device} # 明确指定设备
            )
            self.logger.info(f"嵌入模型加载完成到设备: {self.embedding_device}")
            
            # 确保向量库目录存在
            os.makedirs(os.path.dirname(self.vector_db_path), exist_ok=True)
            
            # 加载向量库（如果存在）
            if os.path.exists(self.vector_db_path):
                self.logger.info(f"加载向量库: {self.vector_db_path}")
                self.vector_db = FAISS.load_local(
                    self.vector_db_path, 
                    self.embeddings, # 使用已配置好设备的实例
                    allow_dangerous_deserialization=True
                )
                self.logger.info("向量库加载成功")
            else:
                self.logger.info("向量库不存在，需要先构建知识库")
        except Exception as e:
            self.logger.error(f"初始化失败: {e}", exc_info=True)
            raise
    
    def process_resume_image(self, image_path):
        """使用OCR提取图片文本"""
        try:
            self.logger.info(f"处理简历图片: {image_path}")
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            return text
        except Exception as e:
            self.logger.error(f"图片处理失败: {e}", exc_info=True) # 添加 exc_info
            return ""
    
    def process_resume_text(self, text_file):
        """处理简历文本文件"""
        try:
            self.logger.info(f"处理简历文本: {text_file}")
            with open(text_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"文本处理失败: {e}", exc_info=True) # 添加 exc_info
            return ""
    
    def build_knowledge_base(self, text_content, images=None):
        """构建知识库"""
        try:
            self.logger.info("开始构建知识库")
            all_text = text_content
            
            # 处理图片（如果有）
            if images:
                for img_path in images:
                    img_text = self.process_resume_image(img_path)
                    all_text += "\n" + img_text
            
            # 切分文本
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.embedding_cfg['chunk_size'],
                chunk_overlap=self.embedding_cfg['chunk_overlap']
            )
            docs = text_splitter.create_documents([all_text])
            self.logger.info(f"文本已切分为{len(docs)}个块")
            
            if not self.embeddings:
                 self.logger.error("嵌入模型未初始化，无法构建知识库。")
                 return False
            self.vector_db = FAISS.from_documents(docs, self.embeddings)
            # 确保目录存在
            os.makedirs(os.path.dirname(self.vector_db_path), exist_ok=True)
            self.vector_db.save_local(self.vector_db_path)
            self.logger.info(f"知识库已保存至: {self.vector_db_path}")
            return True
        except Exception as e:
            self.logger.error(f"构建知识库失败: {e}", exc_info=True)
            return False
    
    def search(self, query, k=3):
        """检索相关内容"""
        try:
            if not self.vector_db:
                self.logger.warning("向量库未初始化，无法执行检索")
                return []
            
            self.logger.info(f"执行检索: {query}, k={k}")
            results = self.vector_db.similarity_search(query, k=k)
            self.logger.info(f"检索到{len(results)}条结果")
            return results
        except Exception as e:
            self.logger.error(f"检索失败: {e}", exc_info=True)
            return [] 