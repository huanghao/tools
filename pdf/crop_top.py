#!/usr/bin/env python3
"""
PDF Logo Removal and Top Margin Tool
去除PDF每页顶部的logo区域并添加顶部边距，保持原始页面大小

使用方法:
    python remove_logo_at_the_top.py input.pdf output.pdf [--crop-height 50] [--top-margin 10]
"""

import argparse
import os
import sys

import fitz  # PyMuPDF
from tqdm import tqdm


def remove_logo_and_add_margin(input_path, output_path, crop_height=50, top_margin=0):
    """
    去除PDF每页顶部的logo区域并添加顶部边距，保持原始页面大小

    Args:
        input_path (str): 输入PDF文件路径
        output_path (str): 输出PDF文件路径
        crop_height (int): 从顶部去除的高度（默认50）
        top_margin (int): 添加的顶部边距（默认0）
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

            # 创建裁剪区域：从crop_height开始到页面底部
            # PyMuPDF坐标系原点在左上角
            crop_rect = fitz.Rect(0, crop_height, page_width, page_height)

            # 计算目标区域：将裁剪后的内容向上移动crop_height距离，并添加top_margin
            # 内容从top_margin开始，到page_height - crop_height + top_margin结束
            target_rect = fitz.Rect(
                0, top_margin, page_width, page_height - crop_height + top_margin
            )

            # 将裁剪后的内容复制到新页面
            new_page.show_pdf_page(
                target_rect,  # 目标区域
                doc,  # 源文档
                page_num,  # 源页面
                clip=crop_rect,  # 裁剪区域
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
        print(f"去除顶部高度: {crop_height}px")
        print(f"添加顶部边距: {top_margin}px")
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
        description="去除PDF每页顶部的logo区域并添加顶部边距，保持原始页面大小",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 只去除logo，不添加边距
  python remove_logo_at_the_top.py input.pdf output.pdf --crop-height 50

  # 去除logo并添加顶部边距
  python remove_logo_at_the_top.py input.pdf output.pdf --crop-height 50 --top-margin 10

  # 只添加顶部边距，不去除logo
  python remove_logo_at_the_top.py input.pdf output.pdf --crop-height 0 --top-margin 15

  # 自定义参数
  python remove_logo_at_the_top.py input.pdf output.pdf --crop-height 120 --top-margin 20
        """,
    )

    parser.add_argument("input", help="输入PDF文件路径")
    parser.add_argument("output", help="输出PDF文件路径")
    parser.add_argument(
        "--crop-height", type=int, default=50, help="从顶部去除的高度 (默认: 50)"
    )
    parser.add_argument(
        "--top-margin", type=int, default=0, help="添加的顶部边距 (默认: 0)"
    )

    args = parser.parse_args()
    remove_logo_and_add_margin(
        args.input, args.output, args.crop_height, args.top_margin
    )


if __name__ == "__main__":
    main()
