# 双面打印乐谱的页面顺序

家里打印机是**反序打印**（最后一页先出纸），需要手动安排单双面顺序。

## 目标

把乐谱 PDF 里需要打印的页面挑出来，组合成两个子 PDF：
- `right.pdf`：奇数页（正面），从前往后打印
- `left.pdf`：偶数页（背面），从后往前打印（因为打印机反序出纸）

## 示例：RSL Grade 3

需要打印的页面（原 PDF 页码）：

```
3 cover,        5 toc
59 improv,      56 tech exec 1
57 tech exec 2, 8 song1a
9 song1b,  12 song2a
13 song2b, 16 song3a
...
           52 songna
53 songnb, 64 notation
```

**第一步：挑出所有页面，按打印顺序排列**

```bash
python select_pages.py ~/Downloads/"RSL GRADE 3.pdf" \
  3,5,59,56,57,8,9,12,13,16,17,20,21,24,25,28,29,32,33,36,37,40,41,44,45,48,49,52,53,64 \
  -o grade3.pdf
```

**第二步：分出奇数页（正面）**

```bash
python select_pages.py grade3.pdf 1-29:2 -o right.pdf
```

**第三步：分出偶数页（背面），倒序**

```bash
python select_pages.py grade3.pdf 30-2:-2 -o left.pdf
```

先打印 `right.pdf`（正面），再把纸翻过来打印 `left.pdf`（背面反序，抵消打印机的反序输出）。
