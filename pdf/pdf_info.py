#!/usr/bin/env python3
"""
PDF文件元信息查看工具
类似ffprobe的功能，显示PDF文件的详细元数据信息
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
from PyPDF2 import PdfReader


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"


def format_date(date_str):
    """格式化PDF日期字符串"""
    if not date_str:
        return "N/A"
    try:
        # PDF日期格式: D:YYYYMMDDHHmmSSOHH'mm'
        if date_str.startswith("D:"):
            date_str = date_str[2:]
        # 提取年月日时分秒
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        hour = int(date_str[8:10])
        minute = int(date_str[10:12])
        second = int(date_str[12:14])

        dt = datetime(year, month, day, hour, minute, second)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return date_str


def get_pdf_info(pdf_path):
    """获取PDF文件的详细信息"""
    try:
        reader = PdfReader(pdf_path)
        file_stat = os.stat(pdf_path)

        info = {
            "file_path": str(pdf_path),
            "file_size": format_size(file_stat.st_size),
            "pages": len(reader.pages),
            "encrypted": reader.is_encrypted,
            "metadata": reader.metadata,
        }

        # 获取页面尺寸信息
        doc = fitz.open(pdf_path)
        page_sizes = {}
        for i in range(len(doc)):
            page = doc[i]
            width = page.rect.width
            height = page.rect.height
            size_key = f"{width:.1f} x {height:.1f}"

            if size_key not in page_sizes:
                page_sizes[size_key] = {"width": width, "height": height, "pages": []}
            page_sizes[size_key]["pages"].append(i + 1)
        doc.close()

        info["page_sizes"] = page_sizes

        return info

    except Exception as e:
        print(f"错误: 无法读取PDF文件 - {e}")
        return None


def print_pdf_info(info):
    """打印PDF信息"""
    if not info:
        return

    print("=" * 60)
    print("PDF文件信息")
    print("=" * 60)

    # 基本信息
    print(f"文件路径: {info['file_path']}")
    print(f"文件大小: {info['file_size']}")
    print(f"页数: {info['pages']}")
    print(f"是否加密: {'是' if info['encrypted'] else '否'}")

    # 页面尺寸
    page_sizes = info["page_sizes"]
    if len(page_sizes) == 1:
        # 所有页面尺寸相同
        size_key = list(page_sizes.keys())[0]
        size_info = page_sizes[size_key]
        print(f"\n页面尺寸: {size_key} points (所有 {info['pages']} 页)")
    else:
        # 页面尺寸不同
        print("\n页面尺寸:")
        for size_key, size_info in page_sizes.items():
            pages_str = ", ".join(map(str, size_info["pages"]))
            if len(size_info["pages"]) == 1:
                print(f"  {size_key} points: 第 {pages_str} 页")
            else:
                print(f"  {size_key} points: 第 {pages_str} 页")

    # 元数据
    metadata = info["metadata"]
    if metadata:
        print("\n文档元数据:")
        metadata_fields = {
            "/Title": "标题",
            "/Author": "作者",
            "/Subject": "主题",
            "/Creator": "创建程序",
            "/Producer": "生成程序",
            "/CreationDate": "创建日期",
            "/ModDate": "修改日期",
            "/Keywords": "关键词",
            "/Creator": "创建者",
            "/Producer": "生产者",
        }

        for key, display_name in metadata_fields.items():
            if key in metadata:
                value = metadata[key]
                if key in ["/CreationDate", "/ModDate"]:
                    value = format_date(value)
                print(f"  {display_name}: {value}")
    else:
        print("\n文档元数据: 无")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="PDF文件元信息查看工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pdf_info.py document.pdf
  python pdf_info.py /path/to/document.pdf
        """,
    )

    parser.add_argument("pdf_file", help="PDF文件路径")

    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)

    if not pdf_path.exists():
        print(f"错误: 文件不存在 - {pdf_path}")
        sys.exit(1)

    if not pdf_path.suffix.lower() == ".pdf":
        print(f"错误: 不是PDF文件 - {pdf_path}")
        sys.exit(1)

    info = get_pdf_info(pdf_path)
    if info:
        print_pdf_info(info)

        if args.verbose:
            print("\n详细信息:")
            print(f"文件修改时间: {datetime.fromtimestamp(os.path.getmtime(pdf_path))}")
            print(
                f"文件访问时间: {datetime.fromtimestamp(os.path.getaccess(pdf_path))}"
            )


if __name__ == "__main__":
    main()
