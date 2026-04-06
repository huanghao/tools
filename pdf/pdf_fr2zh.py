#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_fr2zh.py
-------------
Read a PDF and translate French text to Chinese while preserving layout.
• Uses PyMuPDF (fitz) to read pages and text spans with bounding boxes.
• Overlays translated text back into the original bounding boxes.
• Skips musical notation / tablature regions via heuristics (regex + Unicode ranges).
• Language detection is optional; by default only French segments are translated.
• Translation is pluggable: implement translate_text() with your preferred API or model.
  (e.g., DeepL, OpenAI, Google Cloud Translate, or a local model).

Usage:
  python pdf_fr2zh.py input.pdf output.pdf --font NotoSansCJKsc-Regular --scale 0.95 --detect-lang

Tips:
  • If some Chinese glyphs don't render, install a CJK font and pass its PostScript name with --font.
  • If layout looks crowded, try --scale 0.85 to use smaller font size for overlays.
  • If non-French text is also being translated, drop --detect-lang or use --force-all.

Author: ChatGPT Atlas
"""

import argparse
import os
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set

import fitz  # PyMuPDF
from langdetect import detect, DetectorFactory
from openai import OpenAI
from tqdm import tqdm

DetectorFactory.seed = 0  # make langdetect deterministic


BASE_URL = "https://aigc.sankuai.com/v1/openai/native"
API_KEY = os.environ["FRIDAY_API_ID"]
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ---------------------------- Translation Backend --------------------------------
def translate_text(text: str) -> str:
    """
    Translate a chunk of French text into Chinese.
    Uses the same Friday OpenAI gateway as query_friday_model.py.
    """
    cleaned = text.strip()
    if not cleaned:
        return text

    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {
                    "role": "system",
                    "content": "Translate the user's French text into Simplified Chinese. "
                               "Keep the meaning faithful, preserve formatting cues, and avoid adding explanations.",
                },
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=1500,
        )
        translated = response.choices[0].message.content or ""
        translated = translated.strip()
        return translated if translated else text
    except Exception as exc:
        print(f"[translate_text] Error requesting translation: {exc}")
        return text


# ---------------------------- Heuristics & Utilities ------------------------------
MUSIC_UNICODE_RANGES = [
    (0x2669, 0x266F),        # ♩ ♪ ♫ ♬ ♭ ♮ ♯
    (0x1D100, 0x1D1FF),      # Musical Symbols block
]

def contains_music_symbols(s: str) -> bool:
    for ch in s:
        cp = ord(ch)
        for a, b in MUSIC_UNICODE_RANGES:
            if a <= cp <= b:
                return True
    return False

NUMERIC_HEAVY_RE = re.compile(r"^[\s\-\|\(\)<>/=·\.,;:'\"~\^\*\+_*0-9]+$")

def likely_tablature_or_notation(text: str) -> bool:
    """
    Decide whether a text block looks like tablature/notation we should skip.
    Heuristics:
      • Only digits/punctuation (NUMERIC_HEAVY_RE)  -> skip
      • Contains music symbols (Unicode)            -> skip
      • Very short tokens like isolated A/S with many digits around (harmonica tabs) -> skip
    """
    if not text.strip():
        return True
    if contains_music_symbols(text):
        return True
    if NUMERIC_HEAVY_RE.fullmatch(text):
        return True
    # If more than 60% of characters are digits or separators, treat as tab
    digits = sum(ch.isdigit() for ch in text)
    seps = sum(ch in "-|/ " for ch in text)
    ratio = (digits + seps) / max(len(text), 1)
    if ratio > 0.6:
        return True
    # Isolated capital letters (A, B, C, S) mostly used as markers
    tokens = re.findall(r"[A-ZÀÂÄÆÇÉÈÊËÎÏÔŒÙÛÜŸ]+", text)
    if tokens and all(len(t) <= 2 for t in tokens) and (digits > 0):
        return True
    return False


@dataclass
class OverlaySpan:
    bbox: Tuple[float, float, float, float]
    text: str
    font_size: float
    font_name: Optional[str]


# ---------------------------- CLI Utilities --------------------------------------
def parse_page_spec(spec: str) -> List[int]:
    """
    Parse a page specification string like '1-3,6,9-12' into a sorted list of unique 1-based page numbers.
    Invalid tokens raise ValueError so callers can surface the error to users.
    """
    pages = set()
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start = int(start_str)
                end = int(end_str)
            except ValueError as exc:
                raise ValueError(f"Invalid page range '{part}'") from exc
            if start <= 0 or end <= 0:
                raise ValueError(f"Page numbers must be positive: '{part}'")
            if start > end:
                start, end = end, start
            pages.update(range(start, end + 1))
        else:
            try:
                single = int(part)
            except ValueError as exc:
                raise ValueError(f"Invalid page number '{part}'") from exc
            if single <= 0:
                raise ValueError(f"Page numbers must be positive: '{part}'")
            pages.add(single)
    return sorted(pages)


# ---------------------------- Core Processing ------------------------------------
def extract_text_spans(page: fitz.Page) -> List[OverlaySpan]:
    """Extract text spans and their bounding boxes from a page."""
    spans: List[OverlaySpan] = []
    raw = page.get_text("rawdict")  # preserves blocks/lines/spans
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue  # skip images etc.
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                txt = span.get("text", "")
                if not txt.strip():
                    continue
                bbox = tuple(span["bbox"])  # x0, y0, x1, y1
                font_size = float(span.get("size", 10))
                font_name = span.get("font", None)
                spans.append(OverlaySpan(bbox=bbox, text=txt, font_size=font_size, font_name=font_name))
    return spans


def process_pdf(
    input_pdf: str,
    output_pdf: str,
    font_name: Optional[str] = None,
    scale: float = 0.95,
    detect_lang: bool = True,
    whiten: bool = True,
    verbose: bool = False,
    pages: Optional[List[int]] = None,
):
    doc = fitz.open(input_pdf)
    allowed_pages: Optional[Set[int]] = None
    if pages:
        allowed_pages = {p for p in pages if 1 <= p <= doc.page_count}
        ignored = sorted(set(pages) - allowed_pages)
        if ignored:
            print(f"[process_pdf] Ignoring out-of-range pages: {ignored}")
        if verbose and allowed_pages:
            print(f"[process_pdf] Restricting processing to pages: {sorted(allowed_pages)}")
        if allowed_pages is not None and not allowed_pages:
            print("[process_pdf] --pages resolved to no valid page numbers; skipping processing.")

    for page_index, page in enumerate(tqdm(doc, desc="Processing pages"), start=1):
        if allowed_pages is not None and page_index not in allowed_pages:
            continue
        spans = extract_text_spans(page)

        for sp in spans:
            # Skip music / tablature content
            if likely_tablature_or_notation(sp.text):
                continue

            txt = sp.text

            # Optionally detect language (translate only French)
            if detect_lang:
                try:
                    lang = detect(txt)
                except Exception:
                    lang = "unknown"
                if lang != "fr":
                    continue

            zh = translate_text(txt)
            if not zh or zh.strip() == txt.strip():
                # No translation or backend not configured; skip overlay to avoid hiding original
                if verbose:
                    print("Skipped (no translation change):", txt[:80])
                continue

            # Draw white rectangle to cover original text (optional)
            if whiten:
                rect = fitz.Rect(sp.bbox)
                page.draw_rect(rect, color=(1,1,1), fill=(1,1,1))

            # Insert translated text into the same bounding box
            rect = fitz.Rect(sp.bbox)
            # Adjust font size to avoid overflow (Chinese characters pack more information)
            size = max(sp.font_size * scale, 5)
            page.insert_textbox(
                rect,
                zh,
                fontname=font_name or "helv",
                fontsize=size,
                align=0,  # left align; you can switch to 1=center, 2=right, 3=justify
                encoding=0,
            )

    doc.save(output_pdf)
    doc.close()


def build_argparser():
    ap = argparse.ArgumentParser(description="Translate French text in a PDF to Chinese while preserving layout.")
    ap.add_argument("input", help="Input PDF path")
    ap.add_argument("output", help="Output PDF path")
    ap.add_argument("--font", dest="font", default=None, help="Font name to render Chinese (e.g., 'NotoSansCJKsc-Regular')")
    ap.add_argument("--scale", dest="scale", type=float, default=0.95, help="Scale factor for fontsize (default 0.95)")
    ap.add_argument("--detect-lang", dest="detect_lang", action="store_true", help="Detect language and translate French only")
    ap.add_argument("--no-whiten", dest="whiten", action="store_false", help="Do NOT cover original text before writing translation")
    ap.add_argument(
        "--pages",
        dest="pages",
        default=None,
        help="Page selection in 1-based ranges, e.g. '1-3,6,9-12'. Defaults to all pages.",
    )
    ap.add_argument("--verbose", action="store_true", help="Verbose logs")
    return ap


def main():
    parser = build_argparser()
    args = parser.parse_args()
    pages = None
    if args.pages:
        try:
            pages = parse_page_spec(args.pages)
        except ValueError as exc:
            parser.error(str(exc))

    process_pdf(
        input_pdf=args.input,
        output_pdf=args.output,
        font_name=args.font,
        scale=args.scale,
        detect_lang=args.detect_lang,
        whiten=args.whiten,
        verbose=args.verbose,
        pages=pages,
    )


if __name__ == "__main__":
    main()
