#!/usr/bin/env python3
"""
PDF文件合并工具

功能：
- 合并多个PDF文件为一个输出文件
- 支持命令行参数
- 自动处理文件路径和错误

使用方法：
1. 命令行：python merge_files.py input1.pdf input2.pdf -o output.pdf
2. 从stdin读取：echo "file1.pdf\\nfile2.pdf" | python merge_files.py -o output.pdf
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter


class PDFMerger:
    """PDF文件合并器"""

    def __init__(self):
        self.writer = PdfWriter()
        self.merged_files = []

    def add_pdf(self, pdf_path: str) -> bool:
        """
        添加PDF文件到合并列表

        Args:
            pdf_path: PDF文件路径

        Returns:
            bool: 是否成功添加
        """
        try:
            pdf_path = Path(pdf_path).resolve()
            if not pdf_path.exists():
                print(f"错误：文件不存在 - {pdf_path}")
                return False

            if not pdf_path.suffix.lower() == '.pdf':
                print(f"错误：不是PDF文件 - {pdf_path}")
                return False

            # 读取PDF文件
            reader = PdfReader(str(pdf_path))
            if len(reader.pages) == 0:
                print(f"警告：PDF文件为空 - {pdf_path}")
                return False

            # 添加所有页面
            for page in reader.pages:
                self.writer.add_page(page)

            self.merged_files.append(str(pdf_path))
            print(f"✓ 已添加: {pdf_path.name} ({len(reader.pages)} 页)")
            return True

        except Exception as e:
            print(f"错误：无法读取PDF文件 {pdf_path} - {str(e)}")
            return False

    def merge(self, output_path: str) -> bool:
        """
        合并PDF文件并保存

        Args:
            output_path: 输出文件路径

        Returns:
            bool: 是否成功合并
        """
        if not self.merged_files:
            print("错误：没有可合并的PDF文件")
            return False

        try:
            output_path = Path(output_path).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入合并后的PDF
            with open(output_path, 'wb') as output_file:
                self.writer.write(output_file)

            print(f"\n✓ 合并完成！")
            print(f"输出文件: {output_path}")
            print(f"合并了 {len(self.merged_files)} 个文件，共 {len(self.writer.pages)} 页")
            return True

        except Exception as e:
            print(f"错误：无法保存合并后的PDF文件 - {str(e)}")
            return False

    def get_merged_files(self) -> List[str]:
        """获取已合并的文件列表"""
        return self.merged_files.copy()


def read_files_from_stdin() -> List[str]:
    """从标准输入读取文件名列表"""
    files = []
    try:
        for line in sys.stdin:
            file_path = line.strip()
            if file_path:  # 忽略空行
                files.append(file_path)
    except KeyboardInterrupt:
        print("\n从标准输入读取被中断")
        return []

    return files


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PDF文件合并工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python merge_files.py file1.pdf file2.pdf -o merged.pdf
  python merge_files.py *.pdf -o output.pdf
  echo "file1.pdf\\nfile2.pdf" | python merge_files.py -o merged.pdf
  find . -name "*.pdf" | python merge_files.py -o all.pdf
        """
    )

    parser.add_argument(
        'input_files',
        nargs='*',
        help='要合并的PDF文件路径'
    )

    parser.add_argument(
        '-o', '--output',
        help='输出PDF文件路径（默认为 merged.pdf）',
        default='merged.pdf'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细信息'
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 获取PDF文件列表
    pdf_files = args.input_files

    # 如果没有命令行参数，检查是否有stdin输入
    if not pdf_files and not sys.stdin.isatty():
        pdf_files = read_files_from_stdin()
        if not pdf_files:
            print("错误：从标准输入没有读取到任何文件")
            return 1

    if not pdf_files:
        print("错误：没有提供PDF文件")
        print("使用方法：")
        print("  python merge_files.py file1.pdf file2.pdf -o output.pdf")
        print("  python merge_files.py *.pdf -o output.pdf")
        print("  echo 'file1.pdf\\nfile2.pdf' | python merge_files.py -o output.pdf")
        return 1

    # 创建PDF合并器
    merger = PDFMerger()

    # 添加PDF文件
    print("开始合并PDF文件...")
    print("-" * 50)

    success_count = 0
    for pdf_file in pdf_files:
        if merger.add_pdf(pdf_file):
            success_count += 1

    if success_count == 0:
        print("错误：没有成功添加任何PDF文件")
        return 1

    # 合并并保存
    print("-" * 50)
    if merger.merge(args.output):
        if args.verbose:
            print("\n合并的文件列表：")
            for i, file_path in enumerate(merger.get_merged_files(), 1):
                print(f"  {i}. {file_path}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n程序出现未预期的错误: {str(e)}")
        sys.exit(1)
