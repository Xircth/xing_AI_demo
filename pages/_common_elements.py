import streamlit as st
import json, time, io, sys, os
from src.utils import Config, setup_logger # 保持对 utils 的依赖
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import docx2txt
import pdfplumber

# 确保 src 目录在路径中 (可能需要，因为页面在 pages 目录下运行)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 获取项目根目录 (上两级)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 日志记录器 (如果需要在 common 中使用)
logger = setup_logger('log')

# 自定义CSS样式
def load_css(): # 从 app.py 移动
    return """
    <style>
    /* 全局样式 */
    .main {
        background-color: #fafafa; /* 极简浅灰背景 */
        padding: 0;
        color: #333;
        margin-top: 0;
        font-family: 'Noto Sans', 'Noto Sans SC', -apple-system, sans-serif; /* 优雅字体 */
    }
    
    /* 暗黑模式支持 */
    @media (prefers-color-scheme: dark) {
        .main {
            background-color: #121212;
            color: #e0e0e0;
        }
    }
    
    /* 页面标题 - 这个可能只在主 app.py 或页面内部需要 */
    /* .app-header ... */ 
    /* .app-title ... */
    
    /* 自定义聊天消息样式 */
    [data-testid="stChatMessage"] {
        background-color: rgba(252,252,252,0.95) !important;
        border-radius: 8px !important; /* 更小的圆角 */
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important; /* 较浅阴影 */
        margin-bottom: 8px !important;
        border: 1px solid rgba(0,0,0,0.05) !important;
    }
    
    /* 暗黑模式聊天消息 */
    @media (prefers-color-scheme: dark) {
        [data-testid="stChatMessage"] {
            background-color: rgba(30,30,30,0.95) !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
        }
    }
    
    /* 用户消息 */
    [data-testid="stChatMessage"][data-testid*="user"] {
        border-left: 2px solid #6e7882 !important; /* 低饱和度的左边框 */
    }
    
    /* 助手消息 */
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        border-left: 2px solid #9ab0c2 !important; /* 优雅蓝灰色 */
    }
    
    /* 聊天容器样式 */
    [data-testid="stChatMessageContent"] {
        font-family: 'Noto Sans', 'Noto Sans SC', -apple-system, sans-serif !important;
        font-size: 0.92em !important;
        line-height: 1.6 !important; /* 更大的行高 */
    }
    
    /* 聊天输入框 */
    [data-testid="stChatInput"] {
        background-color: rgba(252,252,252,0.95) !important;
        border-radius: 6px !important; /* 更小的圆角 */
        border: 1px solid rgba(0,0,0,0.08) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        margin-top: 8px !important;
    }
    
    /* 暗黑模式聊天输入框 */
    @media (prefers-color-scheme: dark) {
        [data-testid="stChatInput"] {
            background-color: rgba(30,30,30,0.95) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
        }
    }
    
    /* 聊天输入框内部输入元素 */
    [data-testid="stChatInput"] input {
        font-family: 'Noto Sans', 'Noto Sans SC', -apple-system, sans-serif !important;
        font-size: 0.92em !important;
        color: #333 !important;
    }
    
    /* 暗黑模式输入框文字 */
    @media (prefers-color-scheme: dark) {
        [data-testid="stChatInput"] input {
            color: #e0e0e0 !important;
        }
    }
    
    /* 聊天图标样式 */
    [data-testid="stChatMessage"] [data-testid="userAvatar"],
    [data-testid="stChatMessage"] [data-testid="avatarImage"] {
        margin-right: 8px !important;
    }
    
    /* 自定义滚动条 */
    ::-webkit-scrollbar {
        width: 4px; /* 更细的滚动条 */
        height: 4px;
    }
    
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(0,0,0,0.1); /* 更浅色的滚动条 */
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(0,0,0,0.15);
    }
    
    /* 暗黑模式滚动条 */
    @media (prefers-color-scheme: dark) {
        ::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.1);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255,255,255,0.15);
        }
    }
    
    /* 侧边栏样式 */
    .sidebar .sidebar-content {
        background-color: rgba(250,250,250,0.98) !important;
        color: #333 !important;
        border-right: 1px solid rgba(0,0,0,0.05) !important;
    }
    
    /* 暗黑模式侧边栏 */
    @media (prefers-color-scheme: dark) {
        .sidebar .sidebar-content {
            background-color: rgba(18,18,18,0.98) !important;
            color: #e0e0e0 !important;
            border-right: 1px solid rgba(255,255,255,0.05) !important;
        }
    }
    
    /* 侧边栏关于部分固定在底部 */
    .sidebar-about {
        position: fixed;
        bottom: 12px;
        left: 16px;
        font-size: 0.75em;
        opacity: 0.65;
        font-style: italic; /* 斜体呈现 */
    }
    
    /* 修复Streamlit控件样式 */
    button, .stButton>button {
        border-radius: 4px !important; /* 更小的圆角 */
        background-color: #f5f5f5 !important; /* 优雅浅灰 */
        color: #555 !important; /* 深灰色文本 */
        border: 1px solid rgba(0,0,0,0.05) !important;
        padding: 6px 12px !important; /* 较小的内边距 */
        font-weight: 400 !important; /* 更细的字重 */
        transition: all 0.15s !important;
        box-shadow: none !important;
        font-size: 0.85em !important; /* 较小字体 */
    }
    
    button:hover, .stButton>button:hover {
        background-color: #efefef !important;
        border-color: rgba(0,0,0,0.08) !important;
    }
    
    .stButton>button[data-baseweb="button"][kind="primary"] {
        background-color: #5c7a99 !important; /* 优雅蓝灰色 */
        color: white !important;
        border: none !important;
    }
    
    .stButton>button[data-baseweb="button"][kind="primary"]:hover {
        background-color: #4e697f !important;
    }
    
    /* 暗黑模式按钮 */
    @media (prefers-color-scheme: dark) {
        button, .stButton>button {
            background-color: #252525 !important;
            color: #ccc !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
        }
        
        button:hover, .stButton>button:hover {
            background-color: #2a2a2a !important;
            border-color: rgba(255,255,255,0.08) !important;
        }
        
        .stButton>button[data-baseweb="button"][kind="primary"] {
            background-color: #5d7d9a !important;
            color: white !important;
        }
        
        .stButton>button[data-baseweb="button"][kind="primary"]:hover {
            background-color: #4e6a85 !important;
        }
    }
    
    .stAlert {
        border-radius: 4px !important;
        background-color: rgba(92,122,153,0.05) !important;
        color: #333 !important;
        border: 1px solid rgba(92,122,153,0.1) !important;
        box-shadow: none !important;
    }
    
    .stSelectbox>div>div {
        border-radius: 4px !important;
        background-color: rgba(0,0,0,0.02) !important;
        border: 1px solid rgba(0,0,0,0.05) !important;
        color: #333 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        border-radius: 4px !important;
        background-color: #f5f5f5 !important;
        padding: 2px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 3px !important;
        color: #555 !important;
        padding: 6px 12px !important;
        font-size: 0.85em !important;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: white !important;
        font-weight: 500 !important;
    }
    
    /* 暗黑模式其他控件 */
    @media (prefers-color-scheme: dark) {
        .stAlert {
            background-color: rgba(92,122,153,0.05) !important;
            color: #e0e0e0 !important;
            border: 1px solid rgba(92,122,153,0.1) !important;
        }
        
        .stSelectbox>div>div {
            background-color: rgba(255,255,255,0.05) !important;
            color: #e0e0e0 !important;
            border: 1px solid rgba(255,255,255,0.05) !important;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            background-color: #252525 !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            color: #ccc !important;
        }
        
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: #2a2a2a !important;
        }
    }
    
    [data-testid="stMarkdownContainer"] {
        color: inherit !important;
    }
    
    /* 隐藏输入框标签 */
    .stTextInput label {
        display: none !important;
    }
    
    /* 隐藏成功状态 */
    .element-container:has(.stStatusWidget) {
        display: none !important;
    }
    
    /* 移除Streamlit默认的顶部黑色区域 */
    .stApp > header {
        display: none !important;
    }
    
    /* 调整Streamlit的主容器和块元素 */
    .stApp {
        margin-top: 0 !important;
        background-color: #fafafa !important;
    }
    
    /* 暗黑模式主App */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: #121212 !important;
        }
    }
    
    .block-container {
        padding-top: 0 !important;
        max-width: 100% !important;
    }
    
    /* 响应式样式 */
    @media (max-width: 768px) {
        [data-testid="stChatMessage"] {
            max-width: 90% !important;
        }
    }
    </style>
    """

def process_uploaded_file(uploaded_file): # 从 app.py 移动
    """处理上传的文件，返回文本内容"""
    file_type = uploaded_file.name.split('.')[-1].lower()
    text = "" # 初始化text
    progress_bar = None # 初始化progress_bar
    try: # 使用try...finally确保进度条被清理
        if file_type in ['txt', 'md']:
            try:
                text = uploaded_file.read().decode('utf-8')
                if file_type == 'md': st.sidebar.info("处理Markdown, 保留格式")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                text = uploaded_file.read().decode('gbk', errors='ignore')
        elif file_type == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                total_pages = len(pdf.pages)
                st.sidebar.info(f"处理PDF, 共 {total_pages} 页...")
                progress_text = "处理进度"
                progress_bar = st.sidebar.progress(0, text=progress_text)
                for i, page in enumerate(pdf.pages):
                    text += page.extract_text() or ""
                    progress_bar.progress((i + 1) / total_pages, text=f"{progress_text} {i+1}/{total_pages}")
                progress_bar.empty() # 显式清空
                progress_bar = None # 重置变量
            if len(text.strip()) < 50:
                st.sidebar.info("PDF可能是扫描件, 尝试OCR...")
                uploaded_file.seek(0)
                images = convert_from_bytes(uploaded_file.read())
                total_images = len(images)
                progress_text = "OCR进度"
                progress_bar = st.sidebar.progress(0, text=progress_text)
                for i, img in enumerate(images):
                    text += pytesseract.image_to_string(img, lang='chi_sim+eng') + "\n"
                    progress_bar.progress((i + 1) / total_images, text=f"{progress_text} {i+1}/{total_images}")
                progress_bar.empty() # 显式清空
                progress_bar = None # 重置变量
        elif file_type == 'docx':
            text = docx2txt.process(io.BytesIO(uploaded_file.read()))
        else:
            st.sidebar.warning(f"不支持的文件类型: {file_type}")
            return f"不支持的文件类型: {file_type}" # 返回错误信息
        return text # 返回提取的文本
    except Exception as e:
        logger.error(f"文件处理失败 ({file_type}): {e}")
        st.sidebar.error(f"{file_type.upper()} 处理失败: {e}")
        return f"{file_type.upper()} 处理失败: {e}" # 返回错误信息
    finally:
        if progress_bar: progress_bar.empty() # 确保进度条消失

def init_session_state(): # 从 app.py 移动, 需要 QASystem
    """初始化会话状态"""
    from src.qa_system import QASystem # 在函数内部导入以避免循环依赖
    
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": """欢迎使用兴之助之天气助手"""} # 简化欢迎信息
        ]
    if 'mode' not in st.session_state: # 模式可能不再需要全局管理，由页面决定
        st.session_state.mode = "普通问答" # 保留默认值，但可能被页面覆盖
    if 'current_session' not in st.session_state:
        st.session_state.current_session = f"会话_{time.strftime('%Y%m%d_%H%M%S')}"
    if 'sessions' not in st.session_state:
        st.session_state.sessions = [st.session_state.current_session]
    if 'history' not in st.session_state:
        st.session_state.history = {
            st.session_state.current_session: st.session_state.messages.copy()
        }
    if 'knowledge_base' not in st.session_state:
        st.session_state.knowledge_base = None
    if 'system' not in st.session_state: # QA 系统初始化
        try:
            st.session_state.system = QASystem() # 直接初始化
            logger.info("QA System 初始化成功.")
        except Exception as e:
            logger.error(f"QA System 初始化失败: {e}", exc_info=True)
            st.error(f"系统核心初始化失败: {e}")
            st.stop() # 初始化失败则停止应用

def display_chat_messages(messages_key="messages"): # 新增通用聊天显示函数
    """显示聊天消息"""
    for message in st.session_state.get(messages_key, []):
        role = message["role"]
        content = message["content"]
        with st.chat_message(role):
            if role == "assistant":
                response_text, rag_context_md, msg_type, error_msg = "", None, None, None
                if isinstance(content, dict):
                    response_text = content.get("response", str(content))
                    rag_context_md = content.get("rag_context")
                    msg_type = content.get("type")
                    error_msg = content.get("error")
                    if msg_type == "error":
                        st.error(f"**❌ 抱歉:** {error_msg or '未知错误'}")
                        if response_text != str(content): st.markdown(response_text)
                        continue
                elif isinstance(content, str): response_text = content
                if rag_context_md:
                    with st.expander("📚 查看检索内容", expanded=False): st.markdown(rag_context_md)
                st.markdown(response_text)
            else: st.markdown(content)

def handle_chat_input(use_rag=False, messages_key="messages"): # 新增通用聊天输入处理函数
    """处理用户输入并生成回复 (包含历史记录)"""
    user_input = st.chat_input("请输入您的问题...")
    if user_input:
        # 1. 添加用户消息到状态
        current_messages = st.session_state[messages_key] # 获取当前消息列表引用
        user_message = {"role": "user", "content": user_input}
        current_messages.append(user_message)
        
        # 立即显示用户消息
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # 准备传递给后端的历史记录 (例如最近4条, 即用户本次输入之前的2轮对话)
        history_to_pass = current_messages[-5:-1] 
        # logger.debug(f"传递的历史记录: {history_to_pass}") # 可选的调试日志
        
        # 2. 获取助手回复 (传递历史)
        final_response_content = None
        with st.chat_message("assistant"): 
            with st.spinner("🤔 思考中..."): 
                if 'system' not in st.session_state or st.session_state.system is None:
                    st.error("系统未初始化，请刷新页面。")
                    st.stop()
                # --- 修改：传递 history 参数 ---    
                response = st.session_state.system.process_query(
                    user_input, 
                    history=history_to_pass, # 传递历史记录
                    use_rag=use_rag
                )
                # --- 修改结束 ---

                # 3. 处理并显示回复 (在助手气泡内)
                display_text = ""
                if isinstance(response, dict):
                    if "response" in response:
                        final_response_content = response
                        display_text = response["response"]
                    elif "function" in response and response["function"] == "need_rag":
                        final_response_content = response
                        display_text = response["message"]
                    elif "type" in response and response["type"] == "error":
                        final_response_content = response
                        st.error(f"**❌ 抱歉:** {response.get('error', '未知错误')}")
                        display_text = response.get("response", "")
                    elif "type" in response and response["type"] == "fixed_answer": # 处理固定答案
                         final_response_content = response
                         display_text = response["response"]
                    else:
                        final_response_content = {"response": str(response)}
                        display_text = str(response)
                elif isinstance(response, str):
                     final_response_content = {"response": response}
                     display_text = response
                else:
                     final_response_content = {"response": str(response)}
                     display_text = str(response)
                st.markdown(display_text)

        # 4. 添加助手消息到状态 (包含完整信息)
        if final_response_content:
            assistant_message = {"role": "assistant", "content": final_response_content}
            current_messages.append(assistant_message) # 使用更新后的 current_messages

        # 5. Rerun 更新界面 (清除输入框等)
        st.rerun()

def create_sidebar(): # 简化侧边栏函数
    """创建侧边栏 (简化版，只显示关于信息)"""
    # st.sidebar.markdown("### 🔧 系统设置") # 可选，如果需要标题
    # st.sidebar.markdown("当前页面: " + st.session_state.get('st_page_name', '主页')) # 可选
    # st.sidebar.divider() # 可选
    
    # 移除会话管理和简历管理逻辑，这些移到页面内部

    # 保留关于信息
    st.sidebar.markdown("""
    <div class="sidebar-about">
        <p>基于Qwen2.5-0.5B-Instruct</p>
        <p>v1.1.0 | 多页面</p>
    </div>
    """, unsafe_allow_html=True) 