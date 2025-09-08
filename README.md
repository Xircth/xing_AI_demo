# ✨ 兴之助 - 本地大模型问答系统

一个基于轻量级微调大模型（Qwen2.5-0.5B-Instruct）和 RAG (Retrieval-Augmented Generation) 技术构建的本地化智能问答系统。旨在探索和实践本地部署 LLM、结合外部知识库（如个人简历）和工具（如天气查询）的应用。

---

## 🚀 主要功能

*   **🤖 本地 LLM 推理**: 使用轻量级 Qwen2.5-0.5B 模型，支持本地 CPU/GPU (包括 AMD ROCm) 进行推理。
*   **📚 简历 RAG 问答**: 支持上传个人简历（TXT, PDF, DOCX, 图片），构建向量知识库，并针对简历内容进行智能问答。
*   **☀️ 天气查询工具**: 集成天气查询功能，可通过自然语言查询指定城市和日期的天气。
*   **💬 多功能对话**: 支持上述 RAG 和langchain中间件调用。
*   **🖥️ 现代 Web 界面**: 使用 Streamlit 构建，提供简洁易用的多页面交互界面。
*   **📄 文件处理**: 集成 OCR 功能（依赖 Tesseract），可处理 PDF 和图片格式的简历。
*   **🐳 Docker 支持**: 提供 Dockerfile，方便快速部署和环境隔离。

---
## 🛠️ 技术栈

*   **核心框架**: Streamlit, Langchain (Core, Community)
*   **LLM 与推理**: Transformers, Accelerate, PyTorch, PEFT (用于微调脚本)
*   **向量数据库与检索**: FAISS (CPU), Langchain HuggingFace Embeddings (BAAI/bge-small-zh-v1.5)
*   **工具与数据处理**: Requests, BeautifulSoup4, Pillow, python-docx, docx2txt, pdfplumber, pytesseract, pdf2image
*   **部署**: Docker

---

## 🏗️ 系统架构

系统采用模块化设计，主要组件协同工作：

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│  Streamlit UI   │───▶│   QA System     │───▶│ Middleware      │
│ (app.py, pages/)│    │ (qa_system.py)  │    │ (middleware.py) │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                             │         \      /
                             │          `----´
                             │            │
                             ▼            ▼
                     ┌─────────────┐┌─────────────┐┌─────────────────┐
                     │ LLM Service ││ RAG Module  ││     Tools       │
                     │(llm_service)││(resume_rag) ││   (tools.py)    │
                     └─────────────┘└─────────────┘└─────────────────┘
```

*   **Streamlit UI (`app.py`, `pages/`)**: 用户交互界面，负责展示对话、接收输入、文件上传等。通过 `session_state` 管理会话。
*   **QA System (`qa_system.py`)**: **核心控制器** (单例)。接收前端请求，初始化并管理其他后端模块。它负责处理查询的主流程：优先进行 RAG 检索（如果开启），然后检查是否匹配**固定问答** (`fixed_qa.json`)，最后调用 **Middleware** 进行进一步处理。同时管理简历上传和知识库构建流程。
*   **Middleware (`middleware.py`)**: **业务逻辑处理层**。接收来自 QA System 的查询（可能包含 RAG 上下文或无上下文）。如果带有 RAG 上下文，直接调用 **LLM Service** 生成基于上下文的回复。否则，调用 **LLM Service** 判断查询意图（通用、天气、需 RAG），并协调调用 **Tools** (天气查询) 或将结果/状态返回给 QA System。
*   **LLM Service (`llm_service.py`)**: 封装**大模型**的加载（使用 `device_map='auto'`）和推理。提供 `generate_response` 接口，能根据不同 `prompt_type` (通用、RAG、天气提示) 格式化 Prompt 并获取模型输出。
*   **RAG Module (`resume_rag.py`)**: 负责**简历知识库**的构建、加载 (FAISS) 和检索。包含文本和图片 (OCR) 的处理逻辑，以及文本分割和向量化。
*   **Tools (`tools.py`)**: 实现具体的**外部功能**，目前主要是 `get_weather` 工具，支持多种天气 API。
*   **Utils (`utils.py`, `config.json`)**: 提供**配置管理** (`Config` 类) 和 **日志设置** (`setup_logger`) 等公共服务。
*   **Models (`models.py`)**: 包含**模型微调**相关的类 (`ModelFineTuner`)，主要由 `scripts/finetune.py` 使用。

---
##页面图例：

![image](https://github.com/user-attachments/assets/f98dba0f-6b84-4940-b4b9-6eda278a8d52)
![image](https://github.com/user-attachments/assets/4416dde7-3a14-491b-b2c4-364bde0818fa)
![image](https://github.com/user-attachments/assets/ed20229b-c3ec-4036-ac71-42f9252da5aa)
以上图例仅供参考

## 🚀 部署与运行

### 方式一：本地运行

**1. 环境要求:**
   - Python 3.8+
   - Git
   - (可选) 支持 ROCm 的 AMD GPU 或 支持 CUDA 的 Nvidia GPU
   - (可选, 若需处理PDF/图片简历) Tesseract OCR 和 Poppler

**2. 安装步骤:**
   ```bash
   # 克隆仓库
   git clone https://github.com/Xircth/weather_QA_system.git
   cd weather_QA_system

   # (推荐) 创建并激活虚拟环境
   # python -m venv .venv
   # source .venv/bin/activate  # Linux/macOS
   # .\.venv\Scripts\activate  # Windows

   # 安装依赖
   pip install -r requirements.txt
   ```

**3. (可选) 安装 OCR 依赖:**
   - **Windows**: 
     - 安装 Tesseract: [UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
     - 安装 Poppler: [oschwartz10612/poppler-windows/releases](https://github.com/oschwartz10612/poppler-windows/releases)
     - 将 Tesseract 和 Poppler 的 `bin` 目录添加到系统环境变量 `PATH`。
   - **Linux (Debian/Ubuntu)**:
     ```bash
     sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim poppler-utils libtesseract-dev
     ```

**4. 运行应用:**
   ```bash
   streamlit run app.py
   ```
   系统会自动在浏览器中打开 `http://localhost:8501`。

### 方式二：Docker 部署

**1. 环境要求:**
   - Docker Desktop 或 Docker Engine 已安装并运行。

**2. 构建镜像:**
   ```bash
   # 在项目根目录下执行
   docker build -t xing_langchain_chat .
   ```
   *   **注意**: 如果需要在容器内使用，请确保 `Dockerfile` 中安装 Tesseract 和 Poppler 的命令有效。

**3. 运行容器:**
   ```bash
   docker run -p 8501:8501 xing_langchain_chat
   ```
   访问 `http://localhost:8501`。

**4. (可选) 数据持久化与配置挂载:**
   ```bash
   # 持久化日志和向量数据库
   docker volume create weather_qa_logs
   docker volume create weather_qa_vector_store
   docker run -p 8501:8501 \
     -v weather_qa_logs:/app/logs \
     -v weather_qa_vector_store:/app/data/vector_store \
     xing_langchain_chat

   # 挂载本地配置文件 (方便修改)
   # 确保本地存在 config.json
   docker run -p 8501:8501 -v ./config.json:/app/config.json xing_langchain_chat
   ```

---

## 📖 使用说明

1.  **选择模式**: 在侧边栏选择 **普通问答** 或 **简历问答** 模式。
2.  **简历问答**: 
    *   在 **简历问答** 页面上传简历文件（TXT, PDF, DOCX）或图片。
    *   点击"处理简历"按钮，等待知识库构建完成。
    *   在下方的聊天框中针对简历内容提问。
3.  **普通问答**: 
    *   直接在聊天框中输入您的问题。
    *   支持通用知识问答和天气查询（例如："成都明天天气怎么样？"）。

---

## ⚙️ 配置说明

主要配置文件为 `config.json`，可调整以下内容：

*   `model`: 大模型路径、推理设备偏好、生成参数等。
*   `embedding`: 嵌入模型名称、设备、分块设置等。
*   `vector_db`: 向量数据库存储路径。
*   `weather_api`: 天气查询 API 配置（支持心知天气、和风天气、WeatherAPI.com，默认使用模拟数据）。请参考注释或 `tools.py` 配置真实的 API Key 以获取实时天气。
*   `app`: 应用界面相关配置（如标题）。
*   `logging`: 日志级别和文件路径。

---

## 🧰 辅助脚本

`scripts/` 目录下包含用于模型微调和知识库构建的辅助脚本：

*   **`build_resume_kb.py`**: 手动构建简历知识库（基于 `data/文本简历/RAG.md`）。
*   **`finetune.py`**: 使用 LoRA 对基础模型进行微调（需要准备训练数据）。

```bash
# 手动构建知识库
python scripts/build_resume_kb.py

# 运行微调 (示例)
python scripts/finetune.py --data your_dataset.json --output models/my_finetuned_model --tag my_tag
```

---

## 🤔 常见问题

1.  **PDF/DOCX/图片处理失败**: 确保 OCR 依赖已正确安装并配置环境变量（参考本地部署步骤）。
2.  **模块导入错误**: 尝试使用 `streamlit run app.py` 启动，或确保虚拟环境已激活且依赖安装正确。
3.  **CUDA/ROCm 错误**: 检查驱动是否正确安装，或在 `config.json` 中将 `model.device` 设置为 `"cpu"`。
4.  **固定问答不生效**: 检查 `src/fixed_qa.json` 文件是否存在且格式正确。

---

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证。 
