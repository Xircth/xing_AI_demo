import streamlit as st
import os # 导入os以处理文件
from pages._common_elements import (
    load_css, init_session_state, display_chat_messages, 
    handle_chat_input, create_sidebar, process_uploaded_file, logger # 导入所需函数，包括 process_uploaded_file 和 logger
)

# -- 页面配置 --
# st.set_page_config(page_title="简历问答", page_icon="📄", layout="wide")

# -- 初始化会话状态 (如果尚未初始化) --
if 'system' not in st.session_state: init_session_state() # 确保 QA 系统等已初始化

# -- 加载 CSS --
st.markdown(load_css(), unsafe_allow_html=True) # 加载自定义 CSS

# -- 页面标题 (使用原生组件) --
st.header("📄 简历问答模式", divider='rainbow') # 使用原生标题和分隔线

# -- 清空聊天记录按钮 (保持在主页面) --
if st.button("🗑️ 清空简历问答记录", key="clear_resume_chat"):
    if 'resume_messages' in st.session_state: st.session_state.resume_messages = [] # 清空简历问答的消息
    st.success("简历问答记录已清空！") # 显示成功信息
    st.rerun() # 刷新页面

# -- 聊天界面 (保持在主页面) --
if 'resume_messages' not in st.session_state: # 初始化简历问答消息列表
    st.session_state.resume_messages = [
        {"role": "assistant", "content": "请先在侧边栏上传简历文件，然后在此提问。"} # 更新提示
    ]
display_chat_messages(messages_key="resume_messages") # 显示聊天消息
handle_chat_input(use_rag=True, messages_key="resume_messages") # 处理聊天输入 (RAG 模式)

# -- 侧边栏 --
st.sidebar.markdown("### 📊 简历管理") # 添加侧边栏标题
if 'system' not in st.session_state or st.session_state.system is None:
    st.sidebar.error("系统未初始化，请刷新页面")
else:
    if st.session_state.get('knowledge_base'): # 检查是否已加载知识库
        st.sidebar.success(f"✨ 当前使用: {st.session_state.knowledge_base}")
        if st.sidebar.button("🔄 移除简历", key="remove_resume_sidebar"):
            st.session_state.knowledge_base = None # 清除知识库状态
            if hasattr(st.session_state.system, 'reset_rag'):
                st.sidebar.info("知识库已移除。")
                st.session_state.system.reset_rag() # 重置 RAG (如果方法存在)
            else:
                st.sidebar.warning("无法完全重置 RAG 状态，但知识库引用已移除。")
            st.rerun() # 刷新页面
    else:
        st.sidebar.info("请上传简历文件")
        uploaded_file = st.sidebar.file_uploader(
            "上传简历", 
            type=["txt", "pdf", "docx", "md"], 
            key="resume_uploader_sidebar",
            label_visibility="collapsed" # 隐藏默认标签
        )
        if uploaded_file:
            if st.sidebar.button("✅ 处理简历", type="primary", key="process_resume_sidebar"):
                try:
                    with st.spinner("处理中..."):
                        content = process_uploaded_file(uploaded_file) # 调用通用处理函数
                        if isinstance(content, str) and not content.startswith("不支持") and not content.startswith("处理失败"):
                            st.sidebar.info(f"提取 {len(content)} 字符")
                            result = st.session_state.system.upload_resume(content) # 调用上传简历方法
                            if result["success"]:
                                st.session_state.knowledge_base = uploaded_file.name # 记录知识库名称
                                st.sidebar.success(result["message"]) # 显示成功消息
                                st.rerun() # 成功后刷新
                            else: st.sidebar.error(result["message"]) # 显示失败消息
                        else:
                            st.sidebar.error(f"处理失败: {content}") # 显示处理失败信息
                except Exception as e:
                    logger.error(f"侧边栏处理简历错误: {e}", exc_info=True)
                    st.sidebar.error(f"处理出错: {e}")

st.sidebar.divider() # 在简历管理下方添加分隔线
create_sidebar() # 调用通用的侧边栏（现在只包含关于信息） 