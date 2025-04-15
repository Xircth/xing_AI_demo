import streamlit as st
from pages._common_elements import load_css, init_session_state, display_chat_messages, handle_chat_input, create_sidebar

# -- 页面配置 (可能不需要，因为主 app.py 已设置) --
# st.set_page_config(page_title="普通问答", page_icon="💬", layout="wide")

# -- 初始化会话状态 (如果尚未初始化) --
if 'system' not in st.session_state:
    init_session_state() # 确保 QA 系统等已初始化

# -- 加载 CSS --
st.markdown(load_css(), unsafe_allow_html=True)

# -- 页面标题 (使用原生组件) --
st.header("💬 普通问答模式", divider='rainbow') # 使用原生标题和分隔线

# -- 清空聊天记录按钮 (移到主页面) --
if st.button("🗑️ 清空聊天记录", key="clear_normal_chat"):
    if 'messages' in st.session_state: st.session_state.messages = [] # 清空普通问答的消息
    st.success("聊天记录已清空！") # 显示成功信息
    st.rerun() # 刷新页面

# -- 聊天界面 --
if 'messages' not in st.session_state: # 初始化普通问答消息列表
    st.session_state.messages = [
        {"role": "assistant", "content": "您好！我可以回答各种问题，包括查询天气等。"}
    ]
display_chat_messages(messages_key="messages") # 显示聊天消息
handle_chat_input(use_rag=False, messages_key="messages") # 处理聊天输入 (非 RAG 模式)

# -- 侧边栏 (只显示通用信息) --
create_sidebar() # 调用简化的侧边栏 