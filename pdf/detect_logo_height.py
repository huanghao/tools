#!/usr/bin/env python3
"""
PDF Logo Height Detection Tool
检测PDF中logo区域的高度，帮助确定合适的裁剪参数

使用方法:
    python detect_logo_height.py input.pdf [--page 1] [--show-images]
"""

import argparse
import sys
import os
from pathlib import Path

import fitz  # PyMuPDF
from tqdm import tqdm
import cv2
import numpy as np
from PIL import Image


def detect_logo_height_by_color(pdf_path, page_num=0, show_images=False):
    """
    通过颜色检测logo区域的高度

    Args:
        pdf_path (str): PDF文件路径
        page_num (int): 要分析的页面（默认第1页）
        show_images (bool): 是否显示检测结果图片

    Returns:
        int: 检测到的logo高度
    """
    # 打开PDF
    doc = fitz.open(pdf_path)
    if page_num >= len(doc):
        print(f"❌ 错误: 页面 {page_num + 1} 不存在，PDF只有 {len(doc)} 页")
        return None

    page = doc[page_num]

    # 获取页面尺寸
    page_width = page.rect.width
    page_height = page.rect.height

    # 设置缩放因子以提高处理速度
    scale = 2.0
    mat = fitz.Matrix(scale, scale)

    # 渲染页面为图片
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")

    # 转换为OpenCV格式
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 转换为RGB格式
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 检测橙色/红色区域（TrueFire logo的颜色）
    # 转换到HSV颜色空间
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 定义橙色/红色的HSV范围
    # 橙色范围
    lower_orange = np.array([5, 50, 50])
    upper_orange = np.array([25, 255, 255])

    # 红色范围（包括深红色）
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])

    # 创建掩码
    mask_orange = cv2.inRange(hsv, lower_orange, upper_orange)
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)

    # 合并掩码
    mask = cv2.bitwise_or(mask_orange, cv2.bitwise_or(mask_red1, mask_red2))

    # 形态学操作，去除噪点
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # 查找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 分析轮廓，找到最可能的logo区域
    logo_height = 0
    best_contour = None

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        # 筛选条件：
        # 1. 宽度应该接近页面宽度
        # 2. 高度应该在合理范围内（50-300像素）
        # 3. 位置应该在页面顶部
        width_ratio = w / img.shape[1]
        height_ratio = h / img.shape[0]

        if (width_ratio > 0.7 and  # 宽度占页面大部分
            height_ratio > 0.05 and height_ratio < 0.3 and  # 高度合理
            y < img.shape[0] * 0.2):  # 在页面顶部

            if h > logo_height:
                logo_height = h
                best_contour = contour

    # 如果没有找到合适的轮廓，使用默认值
    if logo_height == 0:
        logo_height = int(img.shape[0] * 0.15)  # 默认15%的页面高度
        print("⚠️  未检测到明显的logo区域，使用默认高度")

    # 显示检测结果
    if show_images:
        # 在原图上绘制检测结果
        debug_img = img_rgb.copy()
        if best_contour is not None:
            cv2.drawContours(debug_img, [best_contour], -1, (0, 255, 0), 2)
            x, y, w, h = cv2.boundingRect(best_contour)
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(debug_img, f"Logo: {h}px", (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        # 绘制建议的裁剪线
        cv2.line(debug_img, (0, logo_height), (img.shape[1], logo_height), (0, 0, 255), 2)
        cv2.putText(debug_img, f"Suggested crop: {logo_height}px (scaled)",
                   (10, logo_height + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(debug_img, f"PDF coordinates: {int(logo_height / scale)}px",
                   (10, logo_height + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

        # 准备三个图片用于并排显示
        # 1. 原图
        original_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

        # 2. 检测结果图
        result_bgr = cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR)

        # 3. 掩码图（转换为3通道以便并排显示）
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        # 确保所有图片具有相同的高度
        height = max(original_bgr.shape[0], result_bgr.shape[0], mask_3ch.shape[0])

        # 调整图片大小到相同高度
        def resize_to_height(img, target_height):
            h, w = img.shape[:2]
            new_w = int(w * target_height / h)
            return cv2.resize(img, (new_w, target_height))

        original_resized = resize_to_height(original_bgr, height)
        result_resized = resize_to_height(result_bgr, height)
        mask_resized = resize_to_height(mask_3ch, height)

        # 并排拼接图片
        combined_img = np.hstack([original_resized, mask_resized, result_resized])

        # 添加标题
        title_height = 30
        title_img = np.zeros((title_height, combined_img.shape[1], 3), dtype=np.uint8)
        title_img.fill(255)  # 白色背景

        # 添加标题文字
        cv2.putText(title_img, "Original", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(title_img, "Detection Result", (original_resized.shape[1] + 10, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(title_img, "Color Mask", (original_resized.shape[1] + result_resized.shape[1] + 10, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        # 合并标题和图片
        final_img = np.vstack([title_img, combined_img])

        # 显示合并后的图片
        cv2.imshow("Logo Detection Analysis", final_img)

        print("📊 显示检测结果图片，按任意键关闭...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # 转换回PDF坐标系统
    pdf_logo_height = int(logo_height / scale)

    print(f"   缩放图像检测高度: {logo_height}px")
    print(f"   PDF坐标系统高度: {pdf_logo_height}px")

    doc.close()
    return pdf_logo_height


def analyze_multiple_pages(pdf_path, max_pages=5, show_images=False):
    """
    分析多个页面，找到最合适的logo高度

    Args:
        pdf_path (str): PDF文件路径
        max_pages (int): 最大分析页数
        show_images (bool): 是否显示检测结果图片

    Returns:
        int: 建议的logo高度
    """
    doc = fitz.open(pdf_path)
    total_pages = min(len(doc), max_pages)

    print(f"📄 分析PDF前 {total_pages} 页...")

    heights = []
    for page_num in tqdm(range(total_pages), desc="分析页面", unit="页"):
        height = detect_logo_height_by_color(pdf_path, page_num, show_images and page_num == 0)
        if height:
            heights.append(height)
            print(f"第 {page_num + 1} 页检测到logo高度: {height}px")

    doc.close()

    if not heights:
        print("❌ 未能检测到任何logo区域")
        return None

    # 计算统计信息
    avg_height = int(np.mean(heights))
    median_height = int(np.median(heights))
    min_height = min(heights)
    max_height = max(heights)

    print(f"\n📊 检测结果统计:")
    print(f"   平均高度: {avg_height}px")
    print(f"   中位数高度: {median_height}px")
    print(f"   最小高度: {min_height}px")
    print(f"   最大高度: {max_height}px")

    # 建议使用中位数高度
    suggested_height = median_height

    print(f"\n💡 建议使用的裁剪高度: {suggested_height}px")
    print(f"   命令: python remove_logo_at_the_top.py {pdf_path} output.pdf --crop-height {suggested_height}")

    return suggested_height


def main():
    parser = argparse.ArgumentParser(
        description="检测PDF中logo区域的高度",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 分析第1页
  python detect_logo_height.py input.pdf

  # 分析指定页面并显示检测结果
  python detect_logo_height.py input.pdf --page 2 --show-images

  # 分析前5页
  python detect_logo_height.py input.pdf --max-pages 5
        """
    )

    parser.add_argument("input", help="输入PDF文件路径")
    parser.add_argument("--page", type=int, default=None,
                       help="要分析的页面编号（从0开始，默认分析多页）")
    parser.add_argument("--max-pages", type=int, default=5,
                       help="最大分析页数（默认5页）")
    parser.add_argument("--show-images", action="store_true",
                       help="显示检测结果图片")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ 错误: 找不到文件 {args.input}")
        sys.exit(1)

    # 如果指定了特定页面，只分析该页面
    if args.page is not None:
        height = detect_logo_height_by_color(args.input, args.page, args.show_images)
        if height:
            print(f"\n💡 建议使用的裁剪高度: {height}px")
            print(f"   命令: python remove_logo_at_the_top.py {args.input} output.pdf --crop-height {height}")
    else:
        # 分析多个页面
        analyze_multiple_pages(args.input, args.max_pages, args.show_images)


if __name__ == "__main__":
    main()