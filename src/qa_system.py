import os, json
from src.utils import Config, setup_logger
from src.llm_service import LLMService
from src.middleware import LangchainMiddleware
from src.resume_rag import ResumeRAG
import difflib

class QASystem:
    _instance = None
    def __new__(cls): return cls._instance if cls._instance else super().__new__(cls) # 单例模式
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.logger = setup_logger('log')
            self.logger.info("初始化问答系统")
            
            # 初始化组件
            try:
                self.llm_service = LLMService() # 初始化LLM服务
                self.middleware = LangchainMiddleware(self.llm_service) # 初始化中间件
                self.resume_rag = ResumeRAG() # 初始化简历RAG系统
                self.fixed_qa_data = self._load_fixed_qa()
                self.initialized = True
                self.logger.info("问答系统初始化完成 (包含固定问答)")
                
            except Exception as e:
                self.logger.error(f"问答系统初始化失败: {e}", exc_info=True)
                raise
    
    def _load_fixed_qa(self, filepath="src/fixed_qa.json"):
        """加载固定问答数据"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.logger.info(f"成功加载固定问答数据: {filepath}")
                    return data.get("fixed_answers", [])
            else:
                self.logger.warning(f"固定问答文件未找到: {filepath}")
                return []
        except Exception as e:
            self.logger.error(f"加载固定问答数据失败: {e}", exc_info=True)
            return []

    def _check_fixed_qa(self, query, threshold=0.7):
        """检查查询是否匹配固定问答 (使用 SequenceMatcher)"""
        if not self.fixed_qa_data: return None
        best_match_answer, highest_similarity = None, 0
        matched_predefined_q = None
        cleaned_query = ''.join(filter(str.isalnum, query)).lower()
        for item in self.fixed_qa_data:
            for predefined_q in item.get("questions", []):
                cleaned_predefined_q = ''.join(filter(str.isalnum, predefined_q)).lower()
                similarity = difflib.SequenceMatcher(None, cleaned_query, cleaned_predefined_q).ratio()
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    if similarity >= threshold:
                        best_match_answer = item.get("answer")
                        matched_predefined_q = predefined_q
        if best_match_answer:
             log_msg = f"查询 '{query}' 命中固定问答 (匹配问题: '{matched_predefined_q}', 相似度: {highest_similarity:.2f})"
             self.logger.info(log_msg)
             # 只返回 response 和 type，rag_context 将使用实际检索结果
             return {
                 "response": best_match_answer,
                 "type": "fixed_answer"
             }
        return None

    def process_query(self, query, history=None, use_rag=True, rag_k=3):
        """处理用户查询的主入口 (RAG模式下先检索再检查固定问答)"""
        self.logger.info(f"处理查询: {query}, use_rag={use_rag}, rag_k={rag_k}, history_len={len(history) if history else 0}")
        history = history or []

        try:
            if use_rag:
                # --- 修改：步骤 1: 先执行 RAG 检索 ---
                self.logger.info("RAG 模式：执行知识库检索...")
                context_docs = self.resume_rag.search(query, k=rag_k)
                rag_context_for_display = "" # 初始化用于显示的 rag_context
                llm_context = "" # 初始化传递给 LLM 的 context
                if context_docs:
                    self.logger.info(f"检索到相关上下文: {len(context_docs)}条")
                    llm_context = "\n".join([doc.page_content for doc in context_docs])
                    rag_context_for_display = f"找到 {len(context_docs)} 条相关内容：\n\n" + "\n\n---\n\n".join(
                        f"**相关度 {i+1}**：\n{doc.page_content}" for i, doc in enumerate(context_docs)
                    )
                else: self.logger.info("未找到相关上下文 (RAG)")
                # --- RAG 检索结束 ---

                # --- 修改：步骤 2: 检查固定问答 ---
                fixed_response = self._check_fixed_qa(query, threshold=0.7)
                if fixed_response:
                    self.logger.info("命中固定问答，将使用预设答案，但展示实际检索到的上下文。")
                    fixed_response["rag_context"] = rag_context_for_display # 使用实际检索的上下文
                    return fixed_response
                # --- 固定问答检查结束 ---

                # 如果未命中固定问答，继续 RAG 流程 (使用已检索的上下文)
                self.logger.info("未命中固定问答，继续执行 LLM RAG 处理")
                if llm_context: # 确保有上下文传递给 LLM
                    response_from_middleware = self.middleware.process_query(
                        query, history=history, rag_context=llm_context
                    )
                    final_response = response_from_middleware
                    if isinstance(response_from_middleware, str): final_response = {"response": response_from_middleware}
                    final_response["rag_context"] = rag_context_for_display # 添加用于显示的上下文
                    return final_response
                else:
                    # RAG 模式但未检索到上下文，且未命中固定问答
                    self.logger.info("RAG 模式但无上下文且未命中固定答案，转为通用处理")
                    return self.middleware.process_query(query, history=history, rag_context=None)

            # 如果没有启用RAG，使用普通处理 (调用中间件)
            response = self.middleware.process_query(query, history=history, rag_context=None)
            return response

        except Exception as e:
            self.logger.error(f"查询处理失败: {e}", exc_info=True)
            return { "type": "error", "error": str(e), "response": f"抱歉...错误: {str(e)}" }
    
    def upload_resume(self, text_content, images=None):
        """上传并构建简历知识库"""
        self.logger.info("上传简历并构建知识库")
        try:
            success = self.resume_rag.build_knowledge_base(text_content, images)
            return {
                "success": success,
                "message": "简历上传成功并已构建知识库" if success else "简历上传失败"
            }
        except Exception as e:
            self.logger.error(f"简历上传失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"简历上传失败: {str(e)}"
            } 