# -*- coding: utf-8 -*-
"""
文档展示路由 - 实时显示联调文档，防扯皮利器

访问:
- /docs/api - API接口文档
- /docs/contract - 前后端联调协议

安全说明:
- 生产环境建议关闭此路由（ENABLE_DOCS_CENTER=false）
- FastAPI自动生成的Swagger文档（/docs）不受影响
"""

import os
import markdown
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

# 文档中心开关（生产环境建议关闭）
ENABLE_DOCS_CENTER = os.getenv("ENABLE_DOCS_CENTER", "true").lower() == "true"

router = APIRouter()

# 文档目录
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"

# 文档映射 - 只保留核心文档
DOCS_MAP = {
    "api": "BACKEND_API.md",
    "contract": "FRONTEND_CONTRACT.md",
}

# HTML模板
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 会议管理后端文档</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            line-height: 1.6;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 20px;
            margin-bottom: 10px;
        }}
        .nav {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            font-size: 14px;
        }}
        .nav a {{
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            padding: 5px 10px;
            border-radius: 4px;
            transition: all 0.3s;
        }}
        .nav a:hover, .nav a.active {{
            background: rgba(255,255,255,0.2);
            color: white;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px 20px;
        }}
        .content {{
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .content h1 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}
        .content h2 {{
            color: #764ba2;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-left: 15px;
            border-left: 4px solid #764ba2;
        }}
        .content h3 {{
            color: #333;
            margin-top: 25px;
            margin-bottom: 10px;
        }}
        .content p {{
            margin-bottom: 15px;
        }}
        .content code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }}
        .content pre {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 20px 0;
        }}
        .content pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
        }}
        .content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .content th, .content td {{
            padding: 12px;
            border: 1px solid #e0e0e0;
            text-align: left;
        }}
        .content th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #667eea;
        }}
        .content tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        .content ul, .content ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        .content li {{
            margin: 8px 0;
        }}
        .content blockquote {{
            border-left: 4px solid #667eea;
            padding-left: 20px;
            margin: 20px 0;
            color: #666;
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 0 8px 8px 0;
        }}
        .content input[type="checkbox"] {{
            margin-right: 8px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        .badge-error {{
            background: #f8d7da;
            color: #721c24;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #999;
            font-size: 14px;
        }}
        .update-time {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #667eea;
            color: white;
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}
        @media (max-width: 768px) {{
            .content {{
                padding: 20px;
            }}
            .nav {{
                font-size: 12px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📚 会议管理后端文档中心</h1>
        <nav class="nav">
            <a href="/docs/api" class="{active_api}">API文档</a>
            <a href="/docs/contract" class="{active_contract}">联调协议</a>
        </nav>
    </div>
    <div class="container">
        <div class="content">
            {content}
        </div>
    </div>
    <div class="footer">
        <p>会议管理后端 v1.2.0 | 文档实时更新，以实际代码为准</p>
    </div>
    <div class="update-time">
        更新时间: {update_time}
    </div>
</body>
</html>"""

# 文档列表页
INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文档中心 - 会议管理后端</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 16px;
        }}
        .docs-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .doc-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            text-decoration: none;
            color: inherit;
        }}
        .doc-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }}
        .doc-icon {{
            font-size: 40px;
            margin-bottom: 15px;
        }}
        .doc-title {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }}
        .doc-desc {{
            color: #666;
            font-size: 14px;
            line-height: 1.5;
        }}
        .doc-badge {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            margin-top: 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: rgba(255,255,255,0.8);
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 文档中心</h1>
            <p>前后端联调必备文档，实时更新，防扯皮利器</p>
        </div>
        <div class="docs-grid">
            <a href="/docs/api" class="doc-card">
                <div class="doc-icon">📋</div>
                <div class="doc-title">API 文档</div>
                <div class="doc-desc">REST API 和 WebSocket 接口规范，包含请求参数和响应格式。</div>
                <span class="doc-badge">后端提供</span>
            </a>
            <a href="/docs/contract" class="doc-card">
                <div class="doc-icon">📜</div>
                <div class="doc-title">联调协议</div>
                <div class="doc-desc">前后端消息协议约定，出错时按此文档定位责任方。</div>
                <span class="doc-badge">双方确认</span>
            </a>
        </div>
        <div class="footer">
            <p>会议管理后端 v1.2.0 | 文档最后更新: {update_time}</p>
        </div>
    </div>
</body>
</html>"""


def get_file_mtime(filepath: Path) -> str:
    """获取文件修改时间"""
    if filepath.exists():
        mtime = os.path.getmtime(filepath)
        from datetime import datetime
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    return "未知"


@router.get("/", response_class=HTMLResponse)
async def docs_index():
    """文档首页 - 列出所有文档"""
    update_time = get_file_mtime(DOCS_DIR / "FRONTEND_CONTRACT.md")
    return HTMLResponse(content=INDEX_TEMPLATE.format(update_time=update_time))


@router.get("/{doc_name}", response_class=HTMLResponse)
async def show_doc(doc_name: str):
    """
    显示指定文档
    
    - api: API接口文档
    - contract: 前后端联调协议
    """
    if doc_name not in DOCS_MAP:
        raise HTTPException(status_code=404, detail=f"文档不存在: {doc_name}")
    
    doc_file = DOCS_DIR / DOCS_MAP[doc_name]
    
    if not doc_file.exists():
        raise HTTPException(status_code=404, detail=f"文档文件不存在: {doc_file}")
    
    # 读取并渲染 markdown
    with open(doc_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 转换为 HTML
    md = markdown.Markdown(extensions=['tables', 'fenced_code'])
    html_content = md.convert(md_content)
    
    # 生成标题
    title_map = {
        "api": "API 文档",
        "contract": "联调协议",
    }
    title = title_map.get(doc_name, doc_name)
    
    # 高亮当前导航
    active_map = {f"active_{k}": "active" if k == doc_name else "" for k in DOCS_MAP.keys()}
    
    # 获取更新时间
    update_time = get_file_mtime(doc_file)
    
    # 渲染模板
    html = HTML_TEMPLATE.format(
        title=title,
        content=html_content,
        update_time=update_time,
        **active_map
    )
    
    return HTMLResponse(content=html)
