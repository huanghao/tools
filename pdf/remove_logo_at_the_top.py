#!/usr/bin/env python3
"""
PDF Logo Removal Tool
去除PDF每页顶部的logo区域，保持原始页面大小

使用方法:
    python remove_logo_at_the_top.py input.pdf output.pdf [--crop-height 50]
"""

import argparse
import sys

import fitz  # PyMuPDF
from tqdm import tqdm


def remove_logo_from_pdf(input_path, output_path, crop_height=50):
    """
    去除PDF每页顶部的logo区域，保持原始页面大小

    Args:
        input_path (str): 输入PDF文件路径
        output_path (str): 输出PDF文件路径
        crop_height (int): 从顶部去除的高度（默认50）
    """
    try:
        # 读取输入PDF
        print(f"正在读取PDF文件: {input_path}")
        doc = fitz.open(input_path)

        total_pages = len(doc)
        print(f"PDF共有 {total_pages} 页")

        # 处理每一页
        for page_num in tqdm(range(total_pages), desc="处理页面", unit="页"):
            page = doc[page_num]

            # 获取页面尺寸
            page_width = page.rect.width
            page_height = page.rect.height

            # 创建裁剪区域：从crop_height开始到页面底部
            # PyMuPDF坐标系原点在左上角
            crop_rect = fitz.Rect(0, crop_height, page_width, page_height)

            # 裁剪页面内容
            page.set_cropbox(crop_rect)

        # 保存输出PDF
        print(f"正在保存处理后的PDF: {output_path}")
        doc.save(output_path)
        doc.close()

        print("✅ PDF处理完成！")
        print(f"去除顶部高度: {crop_height}px")
        print(f"原始页面尺寸: {page_width} x {page_height}")
    except FileNotFoundError:
        print(f"❌ 错误: 找不到输入文件 {input_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 处理PDF时发生错误: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="去除PDF每页顶部的logo区域，保持原始页面大小",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用默认参数（去除顶部50px）
  python remove_logo_at_the_top.py input.pdf output.pdf

  # 自定义去除高度
  python remove_logo_at_the_top.py input.pdf output.pdf --crop-height 120
        """
    )

    parser.add_argument("input", help="输入PDF文件路径")
    parser.add_argument("output", help="输出PDF文件路径")
    parser.add_argument("--crop-height", type=int, default=50,
                       help="从顶部去除的高度 (默认: 50)")

    args = parser.parse_args()
    remove_logo_from_pdf(args.input, args.output, args.crop_height)


if __name__ == "__main__":
    main()
