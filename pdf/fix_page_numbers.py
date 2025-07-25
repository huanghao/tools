#!/usr/bin/env python3
"""
PDF Page Number Fix Tool
修复PDF页码显示问题，特别是右下角的页码格式

使用方法:
    python fix_page_numbers.py input.pdf output.pdf [--format "1/1"]
"""

import argparse
import os
import sys

import fitz  # PyMuPDF
from tqdm import tqdm


def fix_page_numbers(input_path, output_path, page_format="1/1"):
    """
    修复PDF页码显示问题，确保页码格式正确

    Args:
        input_path (str): 输入PDF文件路径
        output_path (str): 输出PDF文件路径
        page_format (str): 页码格式，如"1/1"、"1"等（默认"1/1"）
    """
    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"❌ 错误: 找不到输入文件 {input_path}")
        sys.exit(1)

    try:
        # 读取输入PDF
        print(f"正在读取PDF文件: {input_path}")
        doc = fitz.open(input_path)

        total_pages = len(doc)
        print(f"PDF共有 {total_pages} 页")

        # 获取输入文件的页面尺寸
        first_page = doc[0]
        input_width = first_page.rect.width
        input_height = first_page.rect.height
        print(f"输入文件页面尺寸: {input_width} x {input_height} points")

        # 创建新文档
        new_doc = fitz.open()

        # 处理每一页
        for page_num in tqdm(range(total_pages), desc="处理页面", unit="页"):
            page = doc[page_num]

            # 获取页面尺寸
            page_width = page.rect.width
            page_height = page.rect.height

            # 在新文档中创建相同尺寸的页面
            new_page = new_doc.new_page(width=page_width, height=page_height)

            # 将原页面内容复制到新页面，但移除右下角的原有页码
            copy_page_without_page_numbers(page, new_page, page_width, page_height)

            # 添加新的页码
            add_page_number(
                new_page,
                page_num + 1,
                total_pages,
                page_format,
                page_width,
                page_height,
            )

        # 关闭原文档
        doc.close()

        # 保存输出PDF
        print(f"正在保存处理后的PDF: {output_path}")
        new_doc.save(output_path)
        new_doc.close()

        # 验证输出文件的页面尺寸
        output_doc = fitz.open(output_path)
        output_first_page = output_doc[0]
        output_width = output_first_page.rect.width
        output_height = output_first_page.rect.height
        output_doc.close()

        print("✅ PDF处理完成！")
        print(f"页码格式: {page_format}")
        print(f"输入文件页面尺寸: {input_width} x {input_height} points")
        print(f"输出文件页面尺寸: {output_width} x {output_height} points")

        if input_width == output_width and input_height == output_height:
            print("✅ 页面尺寸保持不变")
        else:
            print("❌ 页面尺寸发生了变化！")
    except Exception as e:
        print(f"❌ 处理PDF时发生错误: {str(e)}")
        sys.exit(1)


def copy_page_without_page_numbers(source_page, target_page, page_width, page_height):
    """
    复制页面内容，但排除右下角区域的页码

    Args:
        source_page: 源页面对象
        target_page: 目标页面对象
        page_width (float): 页面宽度
        page_height (float): 页面高度
    """
    # 定义右下角页码区域（通常页码在这个区域）
    page_number_region = fitz.Rect(
        page_width - 100,  # 右侧100px
        page_height - 50,  # 底部50px
        page_width,  # 到右边缘
        page_height,  # 到底部边缘
    )

    # 创建裁剪区域：排除右下角页码区域
    # 将页面分为四个区域，排除右下角
    regions = [
        # 左上区域
        fitz.Rect(0, 0, page_width - 100, page_height - 50),
        # 右上区域（排除页码区域）
        fitz.Rect(page_width - 100, 0, page_width, page_height - 50),
        # 左下区域
        fitz.Rect(0, page_height - 50, page_width - 100, page_height),
    ]

    # 逐个复制非页码区域
    for region in regions:
        if region.width > 0 and region.height > 0:
            # 将源页面的指定区域复制到目标页面
            target_page.show_pdf_page(
                region,  # 目标区域
                source_page.parent,  # 源文档
                source_page.number,  # 源页面
                clip=region,  # 裁剪区域
            )


def add_page_number(
    page, current_page, total_pages, format_str, page_width, page_height
):
    """
    在页面右下角添加页码

    Args:
        page: PDF页面对象
        current_page (int): 当前页码
        total_pages (int): 总页数
        format_str (str): 页码格式
        page_width (float): 页面宽度
        page_height (float): 页面高度
    """
    # 根据格式生成页码文本
    if format_str == "1/1":
        page_text = f"{current_page}/{total_pages}"
    elif format_str == "1":
        page_text = str(current_page)
    else:
        # 支持自定义格式，如"{page}/{total}"
        page_text = format_str.replace("{page}", str(current_page)).replace(
            "{total}", str(total_pages)
        )

    # 设置字体和大小
    font_size = 12
    font_name = "helv"  # 使用Helvetica字体

    # 计算文本位置（右下角）
    text_width = len(page_text) * font_size * 0.6  # 估算文本宽度
    text_height = font_size

    # 右下角位置，留出一些边距
    margin = 20
    x = page_width - text_width - margin
    y = page_height - margin

    # 插入文本
    page.insert_text(
        point=(x, y - 5),  # 稍微向上调整以对齐基线
        text=page_text,
        fontsize=font_size,
        fontname=font_name,
        color=(0, 0, 0),  # 黑色
    )


def main():
    parser = argparse.ArgumentParser(
        description="修复PDF页码显示问题，确保页码格式正确",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用默认格式（1/1）
  python fix_page_numbers.py input.pdf output.pdf

  # 自定义页码格式
  python fix_page_numbers.py input.pdf output.pdf --format "1"
  python fix_page_numbers.py input.pdf output.pdf --format "{page}/{total}"
        """,
    )

    parser.add_argument("input", help="输入PDF文件路径")
    parser.add_argument("output", help="输出PDF文件路径")
    parser.add_argument(
        "--format",
        type=str,
        default="1/1",
        help="页码格式 (默认: 1/1, 支持: 1, 1/1, {page}/{total})",
    )

    args = parser.parse_args()
    fix_page_numbers(args.input, args.output, args.format)


if __name__ == "__main__":
    main()
