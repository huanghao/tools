#!/usr/bin/env python3
"""
PDF Top Margin Addition Tool
在PDF每页上添加顶部边距，保持原始页面大小

使用方法:
    python add_top_margin.py input.pdf output.pdf [--margin 5]
"""

import argparse
import os
import sys

import fitz  # PyMuPDF
from tqdm import tqdm


def add_top_margin_to_pdf(input_path, output_path, margin=5):
    """
    在PDF每页上添加顶部边距，保持原始页面大小

    Args:
        input_path (str): 输入PDF文件路径
        output_path (str): 输出PDF文件路径
        margin (int): 顶部边距大小（默认5）
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

            # 将原页面内容复制到新页面，但向下偏移margin距离
            # 通过调整目标区域来实现内容移动
            target_rect = fitz.Rect(0, margin, page_width, page_height + margin)

            # 将原页面内容插入到新页面，向下偏移margin
            new_page.show_pdf_page(
                target_rect,  # 目标区域，向下偏移margin
                doc,  # 源文档
                page_num,  # 源页面
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
        print(f"添加顶部边距: {margin}px")
        print(f"输入文件页面尺寸: {input_width} x {input_height} points")
        print(f"输出文件页面尺寸: {output_width} x {output_height} points")

        if input_width == output_width and input_height == output_height:
            print("✅ 页面尺寸保持不变")
        else:
            print("❌ 页面尺寸发生了变化！")
    except Exception as e:
        print(f"❌ 处理PDF时发生错误: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="在PDF每页上添加顶部边距，保持原始页面大小",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用默认参数（添加5px顶部边距）
  python add_top_margin.py input.pdf output.pdf

  # 自定义顶部边距
  python add_top_margin.py input.pdf output.pdf --margin 10
        """,
    )

    parser.add_argument("input", help="输入PDF文件路径")
    parser.add_argument("output", help="输出PDF文件路径")
    parser.add_argument("--margin", type=int, default=5, help="顶部边距大小 (默认: 5)")

    args = parser.parse_args()
    add_top_margin_to_pdf(args.input, args.output, args.margin)


if __name__ == "__main__":
    main()
