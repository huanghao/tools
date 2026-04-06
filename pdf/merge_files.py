#!/usr/bin/env python3
"""
PDF文件合并工具

功能：
- 合并多个PDF文件为一个输出文件
- 支持为每个文件指定要提取的页码范围
- 自动处理文件路径、错误并支持命令行和 stdin

使用示例：
  python merge_files.py file1.pdf file2.pdf -o merged.pdf
  python merge_files.py file1.pdf:1-5 file2.pdf:3-7:2 -o output.pdf
  echo "file1.pdf:range(1,9,2)" | python merge_files.py -o filtered.pdf
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PyPDF2 import PdfReader, PdfWriter

try:
    # 复用 select_pages.py 里丰富的页码解析逻辑
    from select_pages import parse_pages as _parse_pages  # type: ignore
except Exception:  # pragma: no cover - 如果不可用则退回简单解析
    _parse_pages = None


def _split_file_and_pages(token: str) -> Tuple[str, Optional[str]]:
    """拆分形如 path.pdf:1-5 的参数为 (path, pages_expr)。"""
    token = token.strip()
    if not token:
        raise ValueError("空的文件参数")

    if "::" in token:
        path, pages = token.split("::", 1)
        return path.strip(), pages.strip() or None

    for idx, ch in enumerate(token):
        if ch != ":":
            continue
        # 跳过 Windows 盘符，如 C:\path
        if idx == 1 and idx + 1 < len(token) and token[idx + 1] in ("\\", "/"):
            continue
        path = token[:idx].strip()
        pages = token[idx + 1 :].strip()
        if not path:
            continue
        return path, pages or None

    return token, None


def _fallback_parse_pages(pages_expr: str, total_pages: int) -> List[int]:
    """简单兜底解析，支持逗号、区间、带步长。"""
    indices: List[int] = []
    parts = [p.strip() for p in pages_expr.split(",") if p.strip()]
    if not parts:
        raise ValueError("页码表达式为空")

    for part in parts:
        if "-" in part and ":" in part:
            range_part, step_part = part.split(":", 1)
            start_str, end_str = range_part.split("-", 1)
            start = int(start_str)
            end = int(end_str)
            step = int(step_part)
            if step == 0:
                raise ValueError("步长不能为 0")
            current = start
            if step > 0:
                cmp = lambda a, b: a <= b
            else:
                cmp = lambda a, b: a >= b
            while cmp(current, end):
                if current <= 0 or current > total_pages:
                    raise ValueError(f"页码超出范围: {current}")
                indices.append(current - 1)
                current += step
            continue
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = int(start_str)
            end = int(end_str)
            if start <= 0 or end <= 0:
                raise ValueError("页码必须为正整数")
            step = 1 if start <= end else -1
            current = start
            while True:
                if current <= 0 or current > total_pages:
                    raise ValueError(f"页码超出范围: {current}")
                indices.append(current - 1)
                if current == end:
                    break
                current += step
            continue
        value = int(part)
        if value <= 0 or value > total_pages:
            raise ValueError(f"页码超出范围: {value}")
        indices.append(value - 1)

    if not indices:
        raise ValueError("未解析出有效页码")
    return indices


def _parse_page_indices(pages_expr: Optional[str], total_pages: int) -> List[int]:
    if pages_expr is None:
        return list(range(total_pages))
    if _parse_pages is not None:
        return _parse_pages(pages_expr, total_pages)
    return _fallback_parse_pages(pages_expr, total_pages)


class PDFMerger:
    """PDF文件合并器"""

    def __init__(self):
        self.writer = PdfWriter()
        self.merged_files = []

    def add_pdf(self, pdf_path: str, pages_expr: Optional[str] = None) -> bool:
        """
        添加PDF文件到合并列表

        Args:
            pdf_path: PDF文件路径
            pages_expr: 页码表达式（1-based），为空则合并全部页面

        Returns:
            bool: 是否成功添加
        """
        try:
            pdf_path = Path(pdf_path).resolve()
            if not pdf_path.exists():
                print(f"错误：文件不存在 - {pdf_path}")
                return False

            if not pdf_path.suffix.lower() == ".pdf":
                print(f"错误：不是PDF文件 - {pdf_path}")
                return False

            # 读取PDF文件
            reader = PdfReader(str(pdf_path))
            total_pages = len(reader.pages)
            if total_pages == 0:
                print(f"警告：PDF文件为空 - {pdf_path}")
                return False
            try:
                page_indices = _parse_page_indices(pages_expr, total_pages)
            except ValueError as exc:
                print(f"错误：解析页码失败 - {pdf_path.name}: {exc}")
                return False
            if not page_indices:
                print(f"警告：未选择任何页码 - {pdf_path}")
                return False

            for idx in page_indices:
                self.writer.add_page(reader.pages[idx])

            label = str(pdf_path)
            if pages_expr:
                label = f"{label} [{pages_expr}]"
            self.merged_files.append(label)
            print(
                f"✓ 已添加: {pdf_path.name} "
                f"（选取 {len(page_indices)} 页"
                f"{'，页码: ' + pages_expr if pages_expr else ''}）"
            )
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
            with open(output_path, "wb") as output_file:
                self.writer.write(output_file)

            print("\n✓ 合并完成！")
            print(f"输出文件: {output_path}")
            print(
                f"合并了 {len(self.merged_files)} 个文件，共 {len(self.writer.pages)} 页"
            )
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
  python merge_files.py file1.pdf:1-5 file2.pdf:range(3,11,2) -o output.pdf
  echo "file1.pdf:1,3,5" | python merge_files.py -o selected.pdf
  在 Windows 上可使用 path.pdf::1-5 避免与盘符冲突
        """,
    )

    parser.add_argument(
        "input_files",
        nargs="*",
        help="要合并的PDF文件，可写成 path.pdf 或 path.pdf:页码表达式",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="输出PDF文件路径（默认为 merged.pdf）",
        default="merged.pdf",
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 获取PDF文件列表
    pdf_tokens = args.input_files

    # 如果没有命令行参数，检查是否有stdin输入
    if not pdf_tokens and not sys.stdin.isatty():
        pdf_tokens = read_files_from_stdin()
        if not pdf_tokens:
            print("错误：从标准输入没有读取到任何文件")
            return 1

    if not pdf_tokens:
        print("错误：没有提供PDF文件")
        print("使用方法：")
        print("  python merge_files.py file1.pdf file2.pdf -o output.pdf")
        print("  python merge_files.py file1.pdf:1-5 file2.pdf:3-7:2 -o output.pdf")
        print("  echo 'file1.pdf:1,3,5' | python merge_files.py -o output.pdf")
        return 1

    file_specs: List[Tuple[str, Optional[str]]] = []
    parse_failed = False
    for token in pdf_tokens:
        try:
            path, pages_expr = _split_file_and_pages(token)
            file_specs.append((path, pages_expr))
        except ValueError as exc:
            parse_failed = True
            print(f"错误：{exc}")

    if not file_specs:
        print("错误：没有有效的PDF文件参数")
        return 1
    if parse_failed:
        print("提示：使用 path.pdf:页码表达式 格式指定页码，或 path.pdf::页码 表示 Windows 路径。")

    # 创建PDF合并器
    merger = PDFMerger()

    # 添加PDF文件
    print("开始合并PDF文件...")
    print("-" * 50)

    success_count = 0
    for path, pages_expr in file_specs:
        if merger.add_pdf(path, pages_expr):
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
