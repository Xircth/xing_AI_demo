import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from src.utils import Config, setup_logger
# from src.tools import WeatherTool # tools 可能在 middleware 中使用，此处不再直接需要
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any # 增加类型提示

class LLMService:
    # --- 定义常量 ---
    IM_START = "<|im_start|>"
    IM_END = "<|im_end|>"
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    PROMPT_TYPE_GENERAL = "general"
    PROMPT_TYPE_RAG = "rag"
    PROMPT_TYPE_WEATHER_TIP = "weather_tip"
    # --- 常量定义结束 ---

    def __init__(self):
        self.cfg: Dict[str, Any] = Config().get('model')
        self.logger = setup_logger('log')
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None
        # self.target_device = self.cfg.get('device', 'cuda' if torch.cuda.is_available() else 'cpu') # 获取设备
        # 使用 device_map="auto" 后，此变量主要用于日志记录偏好
        self.target_device_preference: str = self.cfg.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
        self.logger.info(f"设备偏好设置: {self.target_device_preference} (实际由 device_map='auto' 决定)")
        self.load_model()

    def load_model(self) -> None:
        """加载模型和分词器 (使用 device_map='auto')"""
        try:
            model_id_or_path: str = self.cfg['path']
            self.logger.info(f"开始加载模型: {model_id_or_path} (使用 device_map='auto')")
            self.tokenizer = AutoTokenizer.from_pretrained(model_id_or_path)
            self.logger.info("分词器加载完成。")
            # 使用 device_map="auto" 让 accelerate 自动处理
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id_or_path,
                torch_dtype=torch.float16, # 保持 float16
                device_map="auto" # 重新启用并设置为 "auto"
            )
            # self.logger.info("模型架构加载完成。正在移动到目标设备...")
            # self.model.to(self.target_device) # 不再需要手动移动
            self.logger.info(f"模型已通过 device_map='auto' 加载完成。模型设备: {self.model.device}")
        except Exception as e:
            self.logger.error(f"模型加载失败: {e}", exc_info=True)
            if "out of memory" in str(e).lower(): self.logger.error("GPU显存不足。尝试减小模型或使用 CPU。")
            elif "meta tensor" in str(e).lower(): self.logger.error("遇到 Meta Tensor 问题，device_map='auto'未能解决。")
            # 检查 accelerate 是否安装
            try:
                import accelerate
                self.logger.info(f"Accelerate 已安装，版本: {accelerate.__version__}")
            except ImportError:
                 self.logger.error("Accelerate 未安装。请运行 'pip install accelerate'。device_map='auto' 需要此库。")
            raise

    def _format_history(self, history: List[Dict[str, Any]]) -> str:
        """将历史记录格式化为 Qwen prompt 字符串"""
        history_prompt_part = ""
        for message in history:
            role = message.get("role")
            content = message.get("content")
            if isinstance(content, dict): content = content.get("response", str(content))
            if role == self.USER:
                 history_prompt_part += f"{self.IM_START}{self.USER}\n{content}{self.IM_END}\n"
            elif role == self.ASSISTANT:
                 history_prompt_part += f"{self.IM_START}{self.ASSISTANT}\n{content}{self.IM_END}\n"
        return history_prompt_part

    def _get_prompt(self, prompt_type: str, query: Optional[str] = None, history: Optional[List[Dict[str, Any]]] = None, context: Optional[str] = None) -> str:
        """获取最终的、格式化好的 Prompt 字符串 (包含历史和上下文)"""
        history = history or []
        system_prompts = {
            self.PROMPT_TYPE_GENERAL: """你是一个有用的中文助手，能够回答各种问题并提供天气查询等功能。
对于用户的问题，你需要判断：
1. 如果是天气相关查询，请明确指出需要调用天气查询工具获取最新数据
2. 如果是关于个人经历、工作经验、项目经验等问题，请说明需要查询知识库获取准确信息
3. 对于其他一般性问题，你可以直接回答""",
            self.PROMPT_TYPE_RAG: """**你必须严格遵守以下规则：**
1. 你叫谢兴，是成都大学大三计算机学院的一名学生。
2. 你必须根据获取到的资料信息来回答我的问题，绝不能乱编造，尽量详尽，字数尽可能多，可以自己扩充但不能有虚假信息。
3. 你的回答应该详尽，比如当我问到你做过什么项目时，你不能只回答"我参与了项目A"，而是应该回答"我参与了项目A，负责用户登录模块开发"。
4. 如果我询问你关于"工作"有关的任何问题，都需要从资料中的项目和技术栈出发进行阐述，不能胡编乱造。
5. 可以直接引用资料原文，可以使用emoji表情进行回复。
6. 请务必使用markdown格式进行输出！！
""",
            self.PROMPT_TYPE_WEATHER_TIP: """你是一个友好的天气助手。请根据提供的天气状况，生成一句温馨提示。要求：
1. 简短自然，不超过20字，契合天气状况，15度以下比较冷需要提示保暖，15~25度比较温暖需要提示增减衣物，25度以上较热提示防晒，30度以上提示多喝水，少户外活动。
2. 使用emoji表情让提示更亲切。
3. 不要重复已知的天气信息
4. 务必使用markdown格式输出！"""
        }
        system_prompt = system_prompts.get(prompt_type, system_prompts[self.PROMPT_TYPE_GENERAL])
        history_prompt_part = self._format_history(history)
        if prompt_type == self.PROMPT_TYPE_RAG and context:
            user_prompt = f"""参考资料:\n---\n{context}\n---\n\n用户问题: {query}\n\n请严格按照系统提示的规则回答问题。"""
        elif prompt_type == self.PROMPT_TYPE_WEATHER_TIP: user_prompt = query
        else: user_prompt = query if query else ""
        formatted_prompt = (
            f"{self.IM_START}{self.SYSTEM}\n{system_prompt}{self.IM_END}\n"
            f"{history_prompt_part}"
            f"{self.IM_START}{self.USER}\n{user_prompt}{self.IM_END}\n"
            f"{self.IM_START}{self.ASSISTANT}\n"
        )
        # self.logger.debug(f"Formatted Prompt:\n{formatted_prompt}")
        return formatted_prompt

    def generate_response(self, query: str, history: Optional[List[Dict[str, Any]]] = None, max_length: Optional[int] = None, temperature: Optional[float] = None, prompt_type: str = PROMPT_TYPE_GENERAL, context: Optional[str] = None) -> str:
        """生成回复 (包含历史记录)"""
        if self.model is None or self.tokenizer is None:
             self.logger.error("模型或分词器未加载...")
             return "错误：模型或分词器未初始化。"
        history = history or []
        try:
            max_tokens = max_length or self.cfg.get('max_length', 2048)
            default_temp = self.cfg.get('temperature', 0.7)
            temp = 0.1 if prompt_type == self.PROMPT_TYPE_RAG else (temperature or default_temp)
            formatted_prompt = self._get_prompt(prompt_type, query, history, context)
            input_device = self.model.device
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(input_device)
            with torch.no_grad():
                is_rag = prompt_type == self.PROMPT_TYPE_RAG
                current_do_sample = not is_rag and temp > 0
                gen_kwargs = {
                    "max_new_tokens": max_tokens,
                    "do_sample": current_do_sample,
                    "repetition_penalty": 1.2,
                    "pad_token_id": self.tokenizer.eos_token_id
                }
                if current_do_sample:
                    gen_kwargs["temperature"] = temp
                    gen_kwargs["top_p"] = self.cfg.get('top_p', 0.8)
                outputs = self.model.generate(**inputs, **gen_kwargs)
            response_ids = outputs[0][inputs.input_ids.shape[1]:]
            response = self.tokenizer.decode(response_ids, skip_special_tokens=True)
            response = response.replace("<|endoftext|>", "").replace(self.IM_END, "").strip()
            return response
        except Exception as e:
            self.logger.error(f"生成回复失败: {e}", exc_info=True)
            return f"生成回复时出错: {str(e)}"
    
    def _extract_weather_params(self, query: str) -> Optional[Dict[str, Any]]:
        """从查询中提取天气参数"""
        try:
            # 支持的城市列表
            supported_cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "武汉", "南京", "西安"]
            
            # 在查询中查找城市
            location = next((city for city in supported_cities if city in query), None)
            if not location:
                return None
                
            # 确定查询日期
            date = "today"
            if "明天" in query:
                date = "tomorrow"
            elif "后天" in query:
                date = "after_tomorrow"
                
            return {
                "function": "get_weather",
                "data": {
                    "location": location,
                    "date": date
                }
            }
        except Exception as e:
            self.logger.error(f"提取天气参数失败: {e}", exc_info=True)
            return None
    
    def process_tool_result(self, query: str, tool_name: str, tool_result: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
        """处理工具调用结果 (考虑历史)"""
        history = history or []
        context_for_tool = f"你刚刚调用了工具 '{tool_name}'，得到结果如下：\n---\n{tool_result}\n---\n现在请根据这个结果回答用户最初的问题：'{query}'"
        return self.generate_response(query=context_for_tool, history=history, prompt_type=self.PROMPT_TYPE_GENERAL)
    
    def process_rag_query(self, query: str, context: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
        """处理带知识库上下文的查询 (包含历史)"""
        history = history or []
        return self.generate_response(query, history=history, prompt_type=self.PROMPT_TYPE_RAG, context=context) 