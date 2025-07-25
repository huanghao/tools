#!/usr/bin/env python3
"""
PDF Cover Creator
将图片转换为PDF封面，支持图片预处理优化

使用方法:
    python create_cover.py image.jpg output.pdf [--size A4] [--scale 0.8] [--enhance]
"""

import argparse
import os
import sys
import tempfile

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageEnhance


def enhance_image(
    image_path, enhance_quality=True, remove_background=True, lighten_dark_areas=True
):
    """
    增强图片质量，去除背景等处理

    Args:
        image_path (str): 输入图片路径
        enhance_quality (bool): 是否增强图片质量
        remove_background (bool): 是否去除背景
        lighten_dark_areas (bool): 是否将深色区域变淡

    Returns:
        str: 处理后的图片临时文件路径
    """
    print("正在处理图片...")

    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("无法读取图片文件")

    # 转换为RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if remove_background:
        print("  - 去除背景...")
        # 使用GrabCut算法去除背景
        mask = np.zeros(img.shape[:2], np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        # 定义前景区域（假设前景在中心区域）
        height, width = img.shape[:2]
        rect = (width // 8, height // 8, width * 3 // 4, height * 3 // 4)

        cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

        # 创建掩码
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")

        # 应用掩码
        img_rgb = img_rgb * mask2[:, :, np.newaxis]

        # 创建透明背景
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        rgba[:, :, :3] = img_rgb
        rgba[:, :, 3] = mask2 * 255  # Alpha通道

    if lighten_dark_areas:
        print("  - 将深色区域变淡...")
        # 转换为PIL图像进行处理
        if remove_background:
            pil_img = Image.fromarray(rgba, "RGBA")
        else:
            pil_img = Image.fromarray(img_rgb, "RGB")

        # 转换为HSV色彩空间
        if pil_img.mode == "RGBA":
            # 分离RGB和Alpha通道
            rgb_img = Image.new("RGB", pil_img.size, (255, 255, 255))
            rgb_img.paste(pil_img, mask=pil_img.split()[-1])  # 使用alpha通道作为mask
            hsv_img = rgb_img.convert("HSV")
        else:
            hsv_img = pil_img.convert("HSV")

        # 分离HSV通道
        h, s, v = hsv_img.split()

        # 将深色区域（低亮度）变淡
        v_array = np.array(v)
        # 找到深色区域（亮度值小于10的像素）
        dark_mask = v_array < 10

        # 将深色区域变淡：将亮度值提升到10-50之间
        v_array[dark_mask] = np.clip(v_array[dark_mask] * 1.5 + 50, 10, 50)

        # 重新组合HSV图像
        v_new = Image.fromarray(v_array.astype(np.uint8))
        hsv_new = Image.merge("HSV", (h, s, v_new))

        # 转换回RGB
        rgb_new = hsv_new.convert("RGB")

        if remove_background:
            # 重新组合RGBA图像
            rgba_array = np.array(rgba)
            rgba_array[:, :, :3] = np.array(rgb_new)
            pil_img = Image.fromarray(rgba_array, "RGBA")
        else:
            pil_img = rgb_new

    if enhance_quality:
        print("  - 增强图片质量...")
        # 转换为PIL图像进行处理
        if remove_background and not lighten_dark_areas:
            pil_img = Image.fromarray(rgba, "RGBA")
        elif not remove_background and not lighten_dark_areas:
            pil_img = Image.fromarray(img_rgb, "RGB")

        # 增强对比度
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(1.2)  # 降低对比度增强，避免过暗

        # 增强锐度
        enhancer = ImageEnhance.Sharpness(pil_img)
        pil_img = enhancer.enhance(1.1)  # 降低锐度增强

        # 增强亮度
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(1.05)  # 轻微提升亮度

        # 转换回numpy数组
        if remove_background:
            rgba = np.array(pil_img)
            img_rgb = rgba[:, :, :3]
        else:
            img_rgb = np.array(pil_img)

    # 保存处理后的图片到临时文件
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp_path = temp_file.name
    temp_file.close()

    if remove_background:
        # 保存为PNG以支持透明度
        cv2.imwrite(temp_path, cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
    else:
        cv2.imwrite(temp_path, cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))

    print("  - 处理后的图片已保存到临时文件")
    return temp_path


def create_pdf_cover(
    image_path,
    output_path,
    page_size="A4",
    scale_factor=0.5,
    enhance=True,
    remove_bg=True,
    lighten_dark=True,
):
    """
    将图片转换为PDF封面

    Args:
        image_path (str): 输入图片文件路径
        output_path (str): 输出PDF文件路径
        page_size (str): 页面尺寸，如"A4"、"Letter"等（默认"A4"）
        scale_factor (float): 图片缩放因子，0.1-1.0（默认0.5）
        enhance (bool): 是否增强图片质量
        remove_bg (bool): 是否去除背景
        lighten_dark (bool): 是否将深色区域变淡
    """
    # 检查输入文件是否存在
    if not os.path.exists(image_path):
        print(f"❌ 错误: 找不到输入文件 {image_path}")
        sys.exit(1)

    temp_image_path = None
    try:
        # 图片预处理
        if enhance or remove_bg or lighten_dark:
            temp_image_path = enhance_image(
                image_path, enhance, remove_bg, lighten_dark
            )
            processed_image_path = temp_image_path
        else:
            processed_image_path = image_path

        # 打开图片
        print(f"正在读取图片文件: {image_path}")
        with Image.open(processed_image_path) as img:
            # 获取图片信息
            img_width, img_height = img.size
            print(f"图片尺寸: {img_width} x {img_height} 像素")
            print(f"图片格式: {img.format}")
            print(f"图片模式: {img.mode}")

        # 定义页面尺寸（以点为单位，1点 = 1/72英寸）
        page_sizes = {
            "A4": (595, 842),  # 210mm x 297mm
            "A3": (842, 1191),  # 297mm x 420mm
            "Letter": (612, 792),  # 8.5" x 11"
            "Legal": (612, 1008),  # 8.5" x 14"
        }

        if page_size not in page_sizes:
            print(f"❌ 错误: 不支持的页面尺寸 {page_size}")
            print(f"支持的尺寸: {', '.join(page_sizes.keys())}")
            sys.exit(1)

        page_width, page_height = page_sizes[page_size]
        print(f"PDF页面尺寸: {page_width} x {page_height} points ({page_size})")

        # 创建PDF文档
        doc = fitz.open()

        # 创建页面
        page = doc.new_page(width=page_width, height=page_height)

        # 计算图片在页面中的位置和尺寸
        # 使用scale_factor控制图片大小，不占满页面
        scale_x = (page_width * scale_factor) / img_width
        scale_y = (page_height * scale_factor) / img_height
        scale = min(scale_x, scale_y)  # 使用较小的缩放比例以保持比例

        # 计算缩放后的图片尺寸
        scaled_width = img_width * scale
        scaled_height = img_height * scale

        # 计算居中位置
        x_offset = (page_width - scaled_width) / 2
        y_offset = (page_height - scaled_height) / 2

        # 创建图片矩形
        img_rect = fitz.Rect(
            x_offset, y_offset, x_offset + scaled_width, y_offset + scaled_height
        )

        # 将图片插入PDF
        print("正在将图片插入PDF...")
        page.insert_image(img_rect, filename=processed_image_path)

        # 保存PDF
        print(f"正在保存PDF封面: {output_path}")
        doc.save(output_path)
        doc.close()

        print("✅ PDF封面创建完成！")
        print(f"页面尺寸: {page_size} ({page_width} x {page_height} points)")
        print(f"图片缩放比例: {scale:.2f}")
        print(f"图片在页面中的位置: ({x_offset:.1f}, {y_offset:.1f})")
        print(f"图片在页面中的尺寸: {scaled_width:.1f} x {scaled_height:.1f} points")
        print(
            f"图片占页面比例: {scaled_width/page_width*100:.1f}% x {scaled_height/page_height*100:.1f}%"
        )

    except Exception as e:
        print(f"❌ 创建PDF封面时发生错误: {str(e)}")
        sys.exit(1)
    finally:
        # 清理临时文件
        if temp_image_path and os.path.exists(temp_image_path):
            os.unlink(temp_image_path)


def main():
    parser = argparse.ArgumentParser(
        description="将图片转换为PDF封面，支持图片预处理优化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用默认设置（50%大小，增强质量，去除背景，深色区域变淡）
  python create_cover.py cover.jpg cover.pdf

  # 自定义图片大小（40%）
  python create_cover.py cover.jpg cover.pdf --scale 0.4

  # 不增强图片质量
  python create_cover.py cover.jpg cover.pdf --no-enhance

  # 不去除背景
  python create_cover.py cover.jpg cover.pdf --no-remove-bg

  # 不将深色区域变淡
  python create_cover.py cover.jpg cover.pdf --no-lighten

  # 使用Letter尺寸
  python create_cover.py cover.jpg cover.pdf --size Letter --scale 0.6
        """,
    )

    parser.add_argument("image", help="输入图片文件路径")
    parser.add_argument("output", help="输出PDF文件路径")
    parser.add_argument(
        "--size",
        type=str,
        default="A4",
        help="页面尺寸 (默认: A4, 支持: A4, A3, Letter, Legal)",
    )
    parser.add_argument(
        "--scale", type=float, default=0.5, help="图片缩放因子，0.1-1.0 (默认: 0.5)"
    )
    parser.add_argument("--no-enhance", action="store_true", help="不增强图片质量")
    parser.add_argument("--no-remove-bg", action="store_true", help="不去除背景")
    parser.add_argument("--no-lighten", action="store_true", help="不将深色区域变淡")

    args = parser.parse_args()

    # 验证缩放因子
    if args.scale < 0.1 or args.scale > 1.0:
        print("❌ 错误: 缩放因子必须在0.1到1.0之间")
        sys.exit(1)

    create_pdf_cover(
        args.image,
        args.output,
        args.size,
        args.scale,
        not args.no_enhance,
        not args.no_remove_bg,
        not args.no_lighten,
    )


if __name__ == "__main__":
    main()
