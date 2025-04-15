# 本地大模型问答系统

基于轻量级大模型的本地化问答系统，支持天气查询、简历知识库问答等功能。

## 功能特性

- 🚀 基于Qwen2.5-0.5B-Instruct轻量级模型，支持本地GPU(包括AMD)推理
- 🔧 集成天气查询等函数调用功能
- 📚 支持简历知识库问答（RAG）
- 💬 多会话管理，支持会话历史保存和切换
- �� Streamlit现代化Web界面
- 📄 支持上传TXT、PDF、DOCX格式的简历文件

## 系统架构

该系统采用模块化三层架构设计：

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│  Streamlit UI   │───▶│ Langchain Agent │───▶│   LLM Service   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │                      │
                               ▼                      ▼
                        ┌─────────────┐      ┌─────────────────┐
                        │   Tools     │      │  Vector Store   │
                        │ (Functions) │      │  (Resume RAG)   │
                        └─────────────┘      └─────────────────┘
```

## 安装方法

### 环境要求

- Python 3.8+
- GPU: AMD显卡 (启用ROCm)或英伟达显卡 (CUDA)
- RAM: 至少8GB

### 依赖安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/weather_QA_system.git
cd weather_QA_system

# 安装依赖
pip install -r requirements.txt

# OCR支持（处理PDF和图片简历）
# Windows系统
# 1. 下载并安装Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
# 2. 将安装路径添加到环境变量，例如：D:\OCR\tesseract.exe所在目录
# 3. 安装poppler (PDF处理所需): https://github.com/oschwartz10612/poppler-windows/releases
# 4. 将poppler的bin目录添加到环境变量

# Linux系统
# apt-get install tesseract-ocr libtesseract-dev tesseract-ocr-chi-sim poppler-utils
```

### 启动系统

为避免模块导入和文件监控问题，建议创建run.py文件：

```python
import os, sys

if __name__ == "__main__":
    # 添加项目目录到Python路径
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    # 禁用文件监控，避免与PyTorch冲突
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    # 启动应用
    os.system(f"{sys.executable} -m streamlit run src/app.py")
```

然后使用以下命令启动：

```bash
python run.py
```

系统会自动打开浏览器窗口，访问 http://localhost:8501

## 使用方法

### 模式切换

- **普通问答模式**: 直接与模型对话，支持天气查询等功能
- **简历问答模式**: 先上传简历文本，然后可以针对简历内容提问

### 简历知识库构建

1. 在侧边栏选择"简历问答"模式
2. 上传简历文件（支持.txt/.pdf/.docx格式）
   - TXT文件直接读取文本
   - PDF文件会通过OCR提取文本（需要安装Tesseract和pdf2image）
   - DOCX文件会提取文本内容
3. 可选择上传简历图片(系统会通过OCR提取图片中的文本)
4. 点击"处理简历"按钮构建知识库
5. 构建完成后即可对简历内容进行提问

### 天气查询示例

直接提问城市天气即可，例如：
- "北京今天天气怎么样？"
- "明天上海的天气如何？"
- "成都今天的气温是多少？"

#### 天气API配置

系统已集成心知天气API(Seniverse)并默认启用，同时支持和风天气API，是中国专业的天气数据服务商，支持全国3000+城市和区县的天气查询。默认使用模拟数据，如需获取真实天气数据，请：

1. 前往[心知天气开发平台](https://www.seniverse.com/)或[和风天气开发平台](https://dev.qweather.com/)注册免费账号
2. 创建应用并获取API密钥(免费版支持每天一定次数调用)
3. 修改`config.json`文件中的`weather_api`部分：
   ```json
   "weather_api": {
     "key": "你的公钥",
     "private_key": "你的私钥",
     "type": "seniverse",  # 心知天气API，或使用"qweather"切换为和风天气
     "timeout": 10
   }
   ```
4. 重启系统即可使用真实天气数据

> 注意：系统同时支持WeatherAPI.com国际版，只需将type设置为"weatherapi"即可切换。

## 配置文件说明

配置文件位于`config.json`，可根据需要修改：

- `model`: 模型配置（路径、推理参数等）
- `embedding`: 嵌入模型配置
- `vector_db`: 向量数据库配置
- `weather_api`: 天气API配置
- `app`: 应用界面配置
- `logging`: 日志配置

## 目录结构

```
weather_QA_system/
├── config.json        # 配置文件
├── main.py            # 程序入口
├── run.py             # 推荐的启动脚本
├── requirements.txt   # 依赖列表
├── README.md          # 说明文档
├── data/              # 数据目录
│   └── vector_store/  # 向量数据库存储
├── logs/              # 日志目录
└── src/               # 源代码
    ├── __init__.py    # 包初始化
    ├── app.py         # Streamlit应用
    ├── llm_service.py # LLM服务
    ├── middleware.py  # Langchain中间件
    ├── qa_system.py   # 问答系统主控
    ├── resume_rag.py  # 简历RAG模块
    ├── tools.py       # 工具函数
    └── utils.py       # 工具类
```

## 辅助脚本

项目中包含一些用于模型微调和知识库构建的辅助脚本，位于 `scripts` 目录下。

### 简历知识库构建脚本

此脚本用于根据 `data/文本简历/RAG.md` 文件构建或更新简历的向量知识库。

```bash
python scripts/build_resume_kb.py
```

### 模型微调脚本

此脚本用于使用指定数据集（默认为 `resume_dataset.json`）对基础模型进行LoRA微调。

```bash
# 默认参数运行
python scripts/finetune.py

# 指定数据集和输出目录
python scripts/finetune.py --data path/to/your_data.json --output path/to/save/model --tag your_model_tag
```

请根据需要调整脚本内的参数或通过命令行参数覆盖。

## 常见问题解决

1. **PDF/DOCX处理失败**
   - 确保已安装所有依赖：`pip install pdf2image pytesseract docx2txt`
   - Windows系统需要安装Tesseract和Poppler，并添加到环境变量
   - Linux系统需要安装相应的系统包

2. **模块导入错误**
   - 使用提供的run.py脚本启动，避免路径问题

3. **CUDA/ROCm错误**
   - 在config.json中将"device"设置为"cpu"可以强制使用CPU推理

4. **中文文件编码问题**
   - 系统会自动尝试多种编码方式，但建议保存为UTF-8格式

5. **模型输出格式不规范问题**
   - 系统已优化模型输出处理逻辑，解决了模型输出中可能带有原始标记或JSON格式信息的问题
   - 如果仍遇到输出格式异常，可尝试调整`src/llm_service.py`中的解析逻辑或联系维护者

## 开发者说明

- 代码采用极致码高尔夫风格，追求最小行数实现功能
- 所有变量由统一配置文件管理，避免重复定义
- 所有注释位于代码右侧，控制在一行内
- 系统对中文高度友好

## 许可证

MIT 

## Docker 支持

项目提供了 Dockerfile，方便您通过 Docker 容器运行本应用。

### 构建 Docker 镜像

在项目根目录下执行以下命令构建镜像：

```bash
# 将 weather_qa_system 替换为您想要的镜像名称
docker build -t weather_qa_system .
```

**注意:** 
- 如果您的应用需要使用简历上传功能中的 OCR（例如处理 PDF 文件），请确保在构建镜像前取消 `Dockerfile` 中安装 Tesseract 和 Poppler 的相关命令的注释。
- 基础镜像 `python:3.9-slim` 是基于 Debian 的。如果您在其他环境（如 Alpine）或需要不同版本的 Python，请相应修改 `Dockerfile`。

### 运行 Docker 容器

使用以下命令运行容器：

```bash
# 将本地 8501 端口映射到容器的 8501 端口
docker run -p 8501:8501 weather_qa_system
```

容器启动后，您可以通过浏览器访问 `http://localhost:8501` 来使用应用。

### 数据持久化 (可选)

如果您希望持久化存储日志或向量数据库，可以使用 Docker 数据卷：

```bash
# 创建数据卷 (如果尚未创建)
docker volume create weather_qa_logs
docker volume create weather_qa_vector_store

# 运行容器并挂载数据卷
docker run -p 8501:8501 \
  -v weather_qa_logs:/app/logs \
  -v weather_qa_vector_store:/app/data/vector_store \
  weather_qa_system
```

如果您希望将 `config.json` 文件挂载到容器中以方便修改，可以使用绑定挂载：

```bash
docker run -p 8501:8501 \
  -v ./config.json:/app/config.json \
  weather_qa_system
```
请确保本地存在 `config.json` 文件。 