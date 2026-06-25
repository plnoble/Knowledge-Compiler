#!/usr/bin/env python3
"""多格式转换器：将 PDF/DOCX/HTML 等转换为 Markdown 并存入 raw/articles/。

用法: python3 convert_to_md.py <input_file> [--root /path/to/wiki]
支持: PDF (pdftotext), HTML (basic), TXT (direct)
"""
import os, sys, subprocess, re
from datetime import datetime

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]


def convert_pdf(filepath):
    """PDF → Markdown via pdftotext。"""
    try:
        result = subprocess.run(["pdftotext", "-layout", filepath, "-"],
                               capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None, f"pdftotext error: {result.stderr}"
        text = result.stdout.strip()
        if not text:
            return None, "PDF 提取为空（可能是扫描件）"
        return text, None
    except FileNotFoundError:
        return None, "pdftotext 未安装 (apk add poppler-utils)"
    except subprocess.TimeoutExpired:
        return None, "PDF 转换超时"


def convert_html(filepath):
    """HTML → 纯文本（简单提取）。"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        # 移除 script/style
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        # 移除 HTML 标签
        content = re.sub(r'<[^>]+>', '\n', content)
        # 清理空白
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        return content, None
    except Exception as e:
        return None, str(e)


def convert_txt(filepath):
    """TXT → 直接读取。"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip(), None
    except Exception as e:
        return None, str(e)


def title_from_filename(filepath):
    """从文件名提取标题。"""
    name = os.path.basename(filepath)
    # 去除扩展名
    for ext in ['.pdf', '.PDF', '.docx', '.DOCX', '.html', '.HTML', '.htm', '.HTM', '.txt', '.TXT']:
        if name.endswith(ext):
            name = name[:-len(ext)]
            break
    # 清理文件名
    name = re.sub(r'[/\\:*?"<>|]', '', name)
    return name.strip()


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print("用法: python3 convert_to_md.py <input_file> [--root /path/to/wiki]")
        print("支持: PDF, HTML, TXT")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"Error: 文件不存在: {filepath}")
        sys.exit(1)

    # 检测格式
    ext = os.path.splitext(filepath)[1].lower()
    converters = {
        '.pdf': convert_pdf,
        '.html': convert_html,
        '.htm': convert_html,
        '.txt': convert_txt,
    }

    if ext not in converters:
        print(f"Error: 不支持的格式: {ext}")
        print(f"支持的格式: {', '.join(converters.keys())}")
        sys.exit(1)

    print(f"转换: {filepath}")
    print(f"格式: {ext}")

    # 转换
    text, error = converters[ext](filepath)
    if error:
        print(f"Error: {error}")
        sys.exit(1)

    # 生成 markdown
    title = title_from_filename(filepath)
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{title}.md"
    output_path = os.path.join(WIKI, "raw", "articles", filename)

    # 检查是否已存在
    if os.path.exists(output_path):
        print(f"跳过: {filename} 已存在")
        sys.exit(0)

    # 包装为 markdown
    markdown = f"""---
title: "{title}"
created: {today}
source: "{os.path.basename(filepath)}"
type: raw
---

# {title}

{text}
"""

    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"标题: {title}")
    print(f"字数: {len(text)}")
    print(f"保存: raw/articles/{filename}")
    print(f"\n完成! 下一步: 告诉 Minis「加工这篇文章」")


if __name__ == "__main__":
    main()
