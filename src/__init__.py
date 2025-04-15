"""本地大模型问答系统"""
from src.qa_system import QASystem
from src.llm_service import LLMService
from src.middleware import LangchainMiddleware
from src.resume_rag import ResumeRAG
from src.utils import Config, setup_logger

__version__ = "0.1.0" 