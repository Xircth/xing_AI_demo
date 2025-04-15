# --- 集成自 main.py 和 run.py 的启动逻辑 ---
import os, sys # 导入 os 和 sys
import streamlit as st # 导入 streamlit
from src.utils import Config, setup_logger # 从 src.utils 导入 Config, setup_logger

# 2. 添加项目根目录和 src 目录到Python路径 (来自 run.py)
project_root = os.path.dirname(os.path.abspath(__file__)) # 获取项目根目录
src_path = os.path.join(project_root, 'src') # 定义 src 路径
if src_path not in sys.path: sys.path.insert(0, src_path) # 添加 src 路径
if project_root not in sys.path: sys.path.append(project_root) # 添加项目根路径

# 3. 确保目录存在 (来自 main.py)
logs_dir = os.path.join(project_root, 'logs') # 定义日志目录
data_dir = os.path.join(project_root, 'data') # 定义数据目录
os.makedirs(logs_dir, exist_ok=True) # 创建日志目录
os.makedirs(data_dir, exist_ok=True) # 创建数据目录

# 4. 设置日志 (来自 main.py)
logger = setup_logger('log') # 设置日志记录器
logger.info('启动问答系统 (通过 app.py - 多页面)') # 记录启动信息

# --- 页面设置 --- 
def init_page(): # 定义页面初始化函数
    cfg = Config().get('app') # 获取应用配置
    st.set_page_config( # 设置页面配置
        page_title=cfg.get('title', '问答系统'), # 页面标题
        page_icon="🤖", # 页面图标
        layout="wide", # 页面布局
        initial_sidebar_state="auto", # 侧边栏初始状态
        menu_items=None # 禁用菜单
    )
    # 隐藏 Streamlit 默认样式 (可选，如果 common_elements.py 中的 CSS 不包含这些)
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True) # 应用隐藏样式

# --- CSS for Enhanced Loading Animation --- # 修改：更新CSS变量名和内容
loading_animation_css = """
<style>
@keyframes pulse-glow {
    0% { box-shadow: 0 0 10px rgba(110, 70, 230, 0.4), 0 0 20px rgba(140, 210, 200, 0.3), inset 0 0 5px rgba(200, 180, 255, 0.2); opacity: 0.8; }
    50% { box-shadow: 0 0 20px rgba(110, 70, 230, 0.7), 0 0 40px rgba(140, 210, 200, 0.5), inset 0 0 10px rgba(200, 180, 255, 0.4); opacity: 1; }
    100% { box-shadow: 0 0 10px rgba(110, 70, 230, 0.4), 0 0 20px rgba(140, 210, 200, 0.3), inset 0 0 5px rgba(200, 180, 255, 0.2); opacity: 0.8; }
}
@keyframes subtle-rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
.nebula-loader-enhanced {
    position: relative; width: 100px; height: 100px; /* Slightly larger */
    margin: 50px auto; border-radius: 50%;
    background: radial-gradient(circle at center, rgba(200, 180, 255, 0.1) 0%, rgba(140, 211, 206, 0.3) 40%, rgba(110, 69, 226, 0.6) 80%, rgba(30, 30, 50, 0) 100%);
    animation: pulse-glow 3s ease-in-out infinite; /* Slower, smoother glow */
    border: 1px solid rgba(140, 211, 206, 0.2); /* Subtle border */
}
.nebula-loader-enhanced::before { /* Inner rotating element */
    content: ''; position: absolute; top: 10%; left: 10%;
    width: 80%; height: 80%; border-radius: 50%;
    border-top: 2px solid rgba(140, 211, 206, 0.8);
    border-left: 2px solid transparent;
    border-right: 2px solid rgba(176, 137, 255, 0.7);
    border-bottom: 2px solid transparent;
    animation: subtle-rotate 2.5s linear infinite; /* Slower rotation */
    filter: blur(1px); /* Slight blur for softness */
}
.loader-text-enhanced {
    text-align: center; color: #c0c0c0; /* Lighter grey */
    margin-top: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; /* Nicer font */
    font-size: 1.5em; /* Slightly larger text - Increased size */
    text-shadow: 0 0 5px rgba(176, 137, 255, 0.3); /* Subtle text shadow */
}
.loading-container-enhanced { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 350px; background-color: #1E1E2E; /* Darker, slightly purple background */ border-radius: 10px; }
</style>
"""
# 修改：更新HTML变量名和内容
loading_html_enhanced = """
<div class="loading-container-enhanced">
    <div class="nebula-loader-enhanced"></div>
    <div class="loader-text-enhanced">🚀 兴之助 启动中... 请稍候</div>
</div>
"""
# --- End of CSS ---

# --- 主应用逻辑 --- 
if __name__ == "__main__": # 主程序入口
    init_page() # 初始化页面设置

    # --- 修改：使用自定义 HTML/CSS 加载动画 --- 
    main_content_placeholder = st.empty() # 创建一个占位符
    with main_content_placeholder.container(): # 在占位符内部显示 spinner
        st.markdown(loading_animation_css, unsafe_allow_html=True) # Inject Enhanced CSS
        st.markdown(loading_html_enhanced, unsafe_allow_html=True)      # Display Enhanced HTML loader
        
        initialization_success = False # Default to false
        try:
            from pages._common_elements import init_session_state # 导入会话状态初始化函数
            if 'system' not in st.session_state: # 检查系统是否已初始化
                logger.info("开始初始化 session state...")
                init_session_state() # 初始化会话状态（包括QA系统）
                logger.info("Session state 初始化完成。")
            else:
                logger.info("Session state 已存在，跳过初始化。")
            initialization_success = True
        except ImportError as e:
            st.error(f"无法加载共享组件: {e} - 请确保 'pages/common_elements.py' 文件存在且无误。") # 导入错误提示
            logger.error(f"无法导入 pages.common_elements: {e}", exc_info=True) # 记录导入错误
            st.stop() # 停止执行
        except Exception as e:
            st.error(f"初始化会话状态时出错: {e}") # 其他初始化错误提示
            logger.error(f"调用 init_session_state 时出错: {e}", exc_info=True) # 记录其他初始化错误
            st.stop() # 停止执行
    # --- 修改结束 ---
    
    # 如果初始化成功，则显示主页面内容
    if initialization_success:
        main_content_placeholder.empty() # 清除加载动画和提示
        # --- 修改：更改标题 --- 
        st.title("✨ 兴之助") # 显示主标题
        # --- 修改结束 ---
        st.markdown("请从左侧边栏选择您需要使用的功能：") # 显示导航提示
        st.markdown("- **💬 普通问答:** 进行通用知识或天气等查询。") # 普通问答说明
        st.markdown("- **📄 简历问答:** 上传简历文件，并针对简历内容进行提问。") # 简历问答说明

    # 主 app.py 不再包含具体的聊天界面逻辑，这些逻辑在 pages/ 目录下