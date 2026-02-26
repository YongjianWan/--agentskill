# General Skills 服务器依赖配置清单

**生成时间**: 2026-02-26
**适用**: 28个通用Skill（已删除重复和平台特有版本）

---

## 一、系统级依赖（apt/yum安装）

### Ubuntu/Debian

```bash
sudo apt-get update && sudo apt-get install -y \
    # 文档处理（docx/pdf/pptx/xlsx必需）
    libreoffice \
    poppler-utils \
    pandoc \
    qpdf \
    # 基础工具
    curl \
    git \
    bash
```

### CentOS/RHEL

```bash
sudo yum install -y \
    libreoffice \
    poppler-utils \
    pandoc \
    qpdf \
    curl \
    git \
    bash
```

---

## 二、Python依赖（pip安装）

### 核心依赖（所有Python skill必需）

```bash
pip install --upgrade pip

# 文档处理类（docx/pdf/pptx/xlsx/code-mentor/slack-gif-creator）
pip install \
    pandas \
    openpyxl \
    pypdf \
    pdfplumber \
    reportlab \
    pytesseract \
    pdf2image \
    Pillow \
    python-pptx \
    markitdown[pptx] \
    defusedxml

# code-mentor专用
pip install \
    pylint pytest colorama

# slack-gif-creator专用
pip install \
    pillow imageio imageio-ffmpeg numpy

# article-extractor可选（提升效果）
pip install trafilatura
```

---

## 三、Node.js依赖（npm安装）

### 安装Node.js 18+（如未安装）

```bash
# 使用nvm安装
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18

# 或使用NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### npm全局包（ralph-evolver/web-artifacts-builder/pptx/docx）

```bash
npm install -g \
    # docx/pptx html转换功能
    docx \
    pptxgenjs \
    # web-artifacts-builder必需
    pnpm \
    vite \
    # 可选但推荐
    playwright \
    sharp
```

---

## 四、其他工具依赖

### GitHub CLI（code-review必需）

```bash
# Ubuntu/Debian
type -p curl >/dev/null || sudo apt install curl -y
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh -y

# 登录认证（用户使用时代码-review skill会提示）
# gh auth login
```

### Reader CLI（article-extractor可选，提升效果）

```bash
npm install -g @mozilla/readability-cli
```

---

## 五、环境变量配置

### 可选环境变量（添加至 ~/.bashrc 或 ~/.zshrc）

```bash
# news-summary语音功能（可选）
export OPENAI_API_KEY="your-api-key-here"

# code-review GitHub认证（用户自行配置）
# export GH_TOKEN="your-github-token"

# archive-cleanup（可选，使用默认值即可）
# export ARCHIVE_AGE_DAYS=7
# export WORKSPACE_DIR=/path/to/workspace
```

---

## 六、按Skill分类的依赖

### 完全可用（16个，无需配置）

| Skill               | 说明                               |
| ------------------- | ---------------------------------- |
| archive-cleanup     | 已修复，使用环境变量，默认当前目录 |
| security-guidance   | 已修复，纯静态指导文档             |
| deep-research-agent | 纯AI方法论                         |
| debug-agent         | 纯AI方法论                         |
| code-simplifier     | 纯AI代码简化                       |
| feature-dev         | 纯AI功能开发工作流                 |
| pr-review-toolkit   | 纯AI PR审查                        |
| canvas-design       | 字体资源已内置                     |
| theme-factory       | 主题资源已内置                     |
| playground          | 模板资源已内置                     |
| brainstorming       | 纯AI方法论                         |
| commit-commands     | 纯prompt                           |
| schedule            | 纯prompt                           |
| course-distiller    | 纯AI方法论                         |
| email-composer      | 纯模板                             |
| internal-comms      | 含示例文件                         |
| doc-coauthoring     | 纯AI工作流                         |

### 需环境配置（11个）

#### 文档处理类（docx/pdf/pptx/xlsx）

| 依赖类型 | 具体包                                                                          |
| -------- | ------------------------------------------------------------------------------- |
| 系统     | libreoffice, poppler-utils, pandoc, qpdf                                        |
| Python   | pandas, openpyxl, pypdf, pdfplumber, reportlab, Pillow, python-pptx, defusedxml |
| Node     | docx, pptxgenjs                                                                 |

#### 代码类（code-mentor/code-review）

| 依赖类型 | 具体包                                         |
| -------- | ---------------------------------------------- |
| Python   | pylint, pytest, colorama |
| 系统     | gh (GitHub CLI)                                |

#### 创作类（ralph-evolver/slack-gif-creator/web-artifacts-builder）

| Skill                 | 依赖类型 | 具体包                                                                |
| --------------------- | -------- | --------------------------------------------------------------------- |
| ralph-evolver         | Node     | Node.js >= 18                                                         |
| slack-gif-creator     | Python   | pillow>=10.0.0, imageio>=2.31.0, imageio-ffmpeg>=0.4.9, numpy>=1.24.0 |
| web-artifacts-builder | Node     | Node.js >= 18, pnpm, vite                                             |

#### 工具类（article-extractor/news-summary）

| Skill             | 依赖类型 | 具体包                                                                 |
| ----------------- | -------- | ---------------------------------------------------------------------- |
| article-extractor | 系统     | curl（内置）, 可选: trafilatura (pip) / @mozilla/readability-cli (npm) |
| news-summary      | 系统     | curl（内置）, 可选: OpenAI API Key                                     |

---

## 七、一键安装脚本

```bash
#!/bin/bash
# install-general-skills-deps.sh

echo "=== Installing General Skills Dependencies ==="

# 1. 系统依赖
echo "[1/4] Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y libreoffice poppler-utils pandoc qpdf curl git bash
elif command -v yum &> /dev/null; then
    sudo yum install -y libreoffice poppler-utils pandoc qpdf curl git bash
else
    echo "Unsupported package manager. Please install manually."
    exit 1
fi

# 2. Python依赖
echo "[2/4] Installing Python dependencies..."
pip install --upgrade pip
pip install \
    pandas openpyxl pypdf pdfplumber reportlab pytesseract pdf2image \
    Pillow python-pptx markitdown[pptx] defusedxml \
    pylint pytest colorama \
    imageio imageio-ffmpeg numpy \
    trafilatura

# 3. Node.js
echo "[3/4] Checking Node.js..."
if ! command -v node &> /dev/null || [ "$(node -v | cut -d'v' -f2 | cut -d'.' -f1)" -lt 18 ]; then
    echo "Installing Node.js 18+..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# 4. npm包
echo "[4/4] Installing npm packages..."
npm install -g docx pptxgenjs pnpm vite playwright sharp

# 5. GitHub CLI
echo "[Optional] Installing GitHub CLI..."
if ! command -v gh &> /dev/null; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update
    sudo apt install gh -y
fi

echo "=== Installation Complete ==="
echo ""
echo "Optional manual steps:"
echo "  1. Configure GitHub CLI: gh auth login"
echo "  2. Set OpenAI API key (for news-summary voice): export OPENAI_API_KEY=your-key-here"
```
