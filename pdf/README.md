# PDF Tools

## 本目录的脚本

| 脚本 | 用途 |
|---|---|
| `select_pages.py` | 从 PDF 中选取指定页面输出，支持范围/步进/重复页 |
| `merge_files.py` | 合并多个 PDF，每个文件可单独指定页码范围 |
| `change_layout.py` | N-up 缩印：把多页拼到一张纸上（如 2x2 四合一） |
| `crop_top.py` | 裁掉每页顶部固定高度区域（去水印/页眉）并可加顶部留白 |
| `detect_logo_height.py` | 用颜色检测估算顶部 logo 区域高度，配合 `crop_top.py` 使用 |

## 现成命令行工具（不需要单独写脚本）

**查看 PDF 元信息**（页数、尺寸、作者、加密状态）
```bash
pdfinfo input.pdf          # brew install poppler
```

**图片转 PDF**
```bash
img2pdf image.jpg -o output.pdf    # pip install img2pdf
```

**提取 TOC（目录大纲）**
```bash
mutool show input.pdf outline      # brew install mupdf-tools
# 或
python3 -c "import fitz; doc=fitz.open('input.pdf'); [print(t) for t in doc.get_toc()]"
```

**拆分 / 旋转 / 简单合并**
```bash
pdftk input.pdf cat 1-10 output out.pdf   # brew install pdftk-java
```

## 双面打印乐谱（家里打印机反序出纸）

打印机最后一页先出纸，双面打印需要手动拆成正面/背面两个文件。

```bash
# 第一步：按打印顺序挑出要打印的页
python select_pages.py input.pdf 3,5,59,56,57,8,... -o selected.pdf

# 第二步：奇数页（正面），从前往后打印
python select_pages.py selected.pdf 1-N:2 -o right.pdf

# 第三步：偶数页（背面），倒序打印（抵消打印机反序输出）
python select_pages.py selected.pdf N-2:-2 -o left.pdf
```

先打 `right.pdf`，翻纸后打 `left.pdf`。具体示例见 git 历史中的 `duplex-printing.md`。
