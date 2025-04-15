from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import tool
from src.utils import Config, setup_logger
from src.tools import get_weather
from typing import List, Dict, Any, Optional
import logging
from src.llm_service import LLMService
import re
from datetime import datetime, timedelta

class LangchainMiddleware:
    """中间件处理用户查询和工具调用"""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.logger = setup_logger('log')
        self.tools = [get_weather]  # 直接初始化工具列表
        
    def find_tool(self, tool_name: str) -> Optional[BaseTool]:
        """根据工具名称查找对应工具"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
        
    def process_query(self, query, history=None, rag_context=None):
        """处理用户查询，调用对应的工具并生成回复 (优先处理RAG, 包含历史)"""
        self.logger.info(f"中间件处理查询: {query}, history_len={len(history) if history else 0}, rag_context_present={rag_context is not None}")
        history = history or [] # 确保 history 是列表

        try:
            # 优先处理 RAG
            if rag_context:
                self.logger.info("检测到 RAG 上下文，直接使用 RAG 处理查询 (传递历史)")
                # --- 修改：将 history 传递给 process_rag_query ---
                return self.llm_service.process_rag_query(query, history=history, context=rag_context)
                # --- 修改结束 ---

            # 如果没有 RAG 上下文，再执行原来的逻辑：
            # 1. 让模型判断查询类型 (传递历史)
            # --- 修改：将 history 传递给 generate_response ---
            response = self.llm_service.generate_response(query, history=history, prompt_type="general")
            # --- 修改结束 ---

            # 如果模型返回了需要使用工具的指示
            if isinstance(response, dict) and response.get("function"):
                if response.get("function") == "get_weather":
                    # 天气查询通常不严重依赖历史，但可以传递以防万一
                    return self._handle_weather_query(query, history=history, params=response.get("data"))
                elif response.get("function") == "need_rag":
                    return {"function": "need_rag", "message": "这个问题可能需要查询知识库获取准确信息，请尝试在简历问答模式下提问。"}

            # 3. 关键词检查 (判断是否需要 RAG - 在非 RAG 模式下)
            if any(keyword in query for keyword in [
                "经历", "经验", "项目", "工作", "职业", "技能", "能力", "学习", "教育",
                "做过", "参与", "负责", "开发", "设计", "实现", "完成", "成果"
            ]):
                return {"function": "need_rag", "message": "这个问题可能需要查询知识库获取准确信息，请尝试在简历问答模式下提问。"}

            # 4. 天气查询处理（后备检查 - 在非 RAG 模式下）
            if any(keyword in query for keyword in ["天气", "气温", "温度", "下雨", "下雪","热","冷","出门","宅家","防晒","保暖"]):
                return self._handle_weather_query(query, history=history)

            # 5. 返回模型的通用回复
            return response

        except Exception as e:
            self.logger.error(f"处理查询失败: {e}", exc_info=True)
            return f"处理您的请求时出现错误: {str(e)}"
    
    def _handle_weather_query(self, query, history=None, params=None):
        """处理天气查询"""
        history = history or []
        try:
            # 获取查询参数
            if not params:
                weather_params = self.llm_service._extract_weather_params(query)
                if not weather_params:
                    return "无法解析天气查询参数"
                params = weather_params.get("data", {})
            
            # 查找并调用天气工具
            tool = self.find_tool("get_weather")
            if not tool:
                return "天气查询服务不可用"
                
            location = params.get("location", "")
            date = params.get("date", "today")
            tool_result = tool.invoke(f"{location},{date}")
            
            # 解析天气数据
            # 尝试匹配温度范围（最低温~最高温）
            temp_range_match = re.search(r'温度(-?\d+)~(-?\d+)℃', tool_result)
            if temp_range_match:
                temp_min = temp_range_match.group(1)
                temp_max = temp_range_match.group(2)
                temp = f"{temp_min}~{temp_max}"
            else:
                # 如果没有温度范围，尝试匹配单个温度
                temp_match = re.search(r'温度(-?\d+)℃', tool_result)
                temp = temp_match.group(1) if temp_match else "未知"
            
            weather_conditions = ["晴", "阴", "多云", "雨", "雪"]
            weather = next((w for w in weather_conditions if w in tool_result), "未知")
            
            wind_match = re.search(r'<(\d+)级', tool_result)
            wind = wind_match.group(1) if wind_match else "未知"
            
            # 生成温馨提示
            tip_prompt = f"根据{location}的天气状况（{weather}，气温{temp}℃，风力{wind}级），给出一句温馨提示。要简短自然，不要重复天气相关信息，可以用emoji表情显得更加亲切。"
            # --- 修改：可以考虑将 history 传给 generate_response，但需调整 prompt ---
            tip = self.llm_service.generate_response(tip_prompt, history=[], prompt_type="weather_tip", max_length=50) # 暂时不传 history
            # --- 修改结束 ---
            
            # 根据日期参数生成不同的时间描述
            date_desc = {
                "today": f"今天是{datetime.now().strftime('%Y年%m月%d日')}",
                "tomorrow": f"明天是{(datetime.now() + timedelta(days=1)).strftime('%Y年%m月%d日')}",
                "after_tomorrow": f"后天是{(datetime.now() + timedelta(days=2)).strftime('%Y年%m月%d日')}"
            }.get(date, f"今天是{datetime.now().strftime('%Y年%m月%d日')}")
            
            # 返回格式化结果，使用两个换行符确保分隔
            return f"{date_desc}，{location}天气{weather}，气温{temp}℃，风力{wind}级。\n\n温馨提示：{tip}"
            
        except Exception as e:
            self.logger.error(f"处理天气查询失败: {e}", exc_info=True)
            return f"天气查询失败: {str(e)}" 