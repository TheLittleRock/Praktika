import os
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import pymupdf

FONT_DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def _clean_unicode_str(s: Optional[str]) -> str:
    """Prepends UTF-16BE BOM to force Chrome/Brave and PDF readers to render Czech and Slovak diacritics correctly."""
    if not s:
        return ""
    text = str(s).strip()
    if not text:
        return ""
    if not text.startswith("\ufeff"):
        return "\ufeff" + text
    return text

def _draw_acrobat_speech_bubble(page, px: float, py: float, color_rgb: tuple):
    """Draws an Adobe Acrobat style speech bubble vector icon."""
    bubble_w = 18.0
    bubble_h = 14.0
    bx0, by0 = px, py - bubble_h
    bx1, by1 = px + bubble_w, py
    
    shape = page.new_shape()
    rect = pymupdf.Rect(bx0, by0, bx1, by1)
    shape.draw_rect(rect, radius=0.15)
    shape.finish(color=color_rgb, fill=color_rgb, width=0.6)
    
    # Bottom pointer
    pointer = [
        pymupdf.Point(bx0 + 2.5, by1),
        pymupdf.Point(bx0, by1 + 4.5),
        pymupdf.Point(bx0 + 7.0, by1),
        pymupdf.Point(bx0 + 2.5, by1)
    ]
    shape.draw_polyline(pointer)
    shape.finish(color=color_rgb, fill=color_rgb, width=0.6)
    
    # Internal white note lines
    shape.draw_line(pymupdf.Point(bx0 + 3.5, by0 + 4.5), pymupdf.Point(bx1 - 3.5, by0 + 4.5))
    shape.finish(color=(1.0, 1.0, 1.0), width=1.1)
    shape.draw_line(pymupdf.Point(bx0 + 3.5, by0 + 7.5), pymupdf.Point(bx1 - 3.5, by0 + 7.5))
    shape.finish(color=(1.0, 1.0, 1.0), width=1.1)
    shape.draw_line(pymupdf.Point(bx0 + 3.5, by0 + 10.5), pymupdf.Point(bx1 - 6.5, by0 + 10.5))
    shape.finish(color=(1.0, 1.0, 1.0), width=1.1)
    shape.commit()

def calculate_grade_letter(points: float, manual_override: Optional[str] = None) -> str:
    if manual_override and str(manual_override).strip().upper() in ["A", "B", "C", "D", "E", "F"]:
        return str(manual_override).strip().upper()
    if points >= 9.00 - 1e-6:
        return "A"
    if points >= 8.00 - 1e-6:
        return "B"
    if points >= 6.00 - 1e-6:
        return "C"
    if points >= 4.00 - 1e-6:
        return "D"
    if points >= 2.00 - 1e-6:
        return "E"
    return "F"

def _ensure_font(page) -> str:
    """Ensures TrueType DejaVuSans is registered on the page for perfect Czech and Slovak diacritics."""
    if os.path.exists(FONT_DEJAVU):
        try:
            page.insert_font(fontname="dejavu", fontfile=FONT_DEJAVU)
            if os.path.exists(FONT_DEJAVU_BOLD):
                page.insert_font(fontname="dejavu-bold", fontfile=FONT_DEJAVU_BOLD)
            return "dejavu"
        except Exception:
            pass
    return "helv"

def format_points(num) -> str:
    if num is None:
        return "0"
    try:
        val = float(num)
        rounded = round(val * 1000) / 1000
        if rounded.is_integer():
            return str(int(rounded))
        return f"{rounded:.3f}".rstrip("0").rstrip(".")
    except Exception:
        return str(num)

def extract_pdf_annotations(pdf_source) -> List[Dict[str, Any]]:
    """Extract all comments and annotations from an existing PDF file."""
    if isinstance(pdf_source, (str, Path)):
        doc = pymupdf.open(str(pdf_source))
    else:
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")

    extracted = []
    for page_idx, page in enumerate(doc):
        for annot in page.annots():
            info = annot.info or {}
            rect = annot.rect
            raw_type = annot.type[1].lower() if annot.type and len(annot.type) > 1 else "highlight"
            
            # Map PDF annotation type to app tool type
            if raw_type in ["text"]:
                type_str = "note"
            elif raw_type in ["highlight"]:
                type_str = "highlight"
            elif raw_type in ["strikeout"]:
                type_str = "strikeout"
            elif raw_type in ["freetext"]:
                type_str = "text_direct"
            elif raw_type in ["square"]:
                type_str = "rect"
            elif raw_type in ["line"]:
                type_str = "arrow"
            elif raw_type in ["ink"]:
                type_str = "ink"
            else:
                type_str = "highlight"

            content = (info.get("content") or "").strip()
            author = info.get("title") or info.get("author") or "Asistent"

            # Parse quads / multi-line vertices if present
            rects = []
            if getattr(annot, "vertices", None):
                v = annot.vertices
                for i in range(0, len(v), 4):
                    chunk = v[i:i+4]
                    if len(chunk) == 4:
                        xs = [p[0] for p in chunk]
                        ys = [p[1] for p in chunk]
                        rects.append([
                            round(min(xs), 2),
                            round(min(ys), 2),
                            round(max(xs), 2),
                            round(max(ys), 2)
                        ])

            # Color extraction
            colors = annot.colors or {}
            stroke = colors.get("stroke") or []
            if len(stroke) == 3:
                color_hex = f"#{int(stroke[0]*255):02x}{int(stroke[1]*255):02x}{int(stroke[2]*255):02x}"
                color_rgb = [stroke[0], stroke[1], stroke[2]]
            else:
                color_hex = "#db3425"
                color_rgb = [0.858, 0.203, 0.145]

            extracted.append({
                "id": info.get("id") or f"annot_{page_idx+1}_{len(extracted)+1}",
                "page": page_idx + 1,
                "type": type_str,
                "content": content,
                "comment": content,
                "author": author,
                "rect": [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)],
                "rects": rects,
                "point": [round(rect.x0, 2), round(rect.y0, 2)],
                "color": color_hex,
                "color_rgb": color_rgb
            })

    doc.close()
    return extracted

def _parse_to_fitz_rect(r):
    if not r:
        return None
    if isinstance(r, (list, tuple)) and len(r) >= 4:
        return pymupdf.Rect(float(r[0]), float(r[1]), float(r[2]), float(r[3]))
    elif isinstance(r, dict):
        x = float(r.get("x", r.get("x0", 0)))
        y = float(r.get("y", r.get("y0", 0)))
        if "width" in r:
            w = float(r["width"])
            h = float(r.get("height", 0))
            return pymupdf.Rect(x, y, x + w, y + h)
        elif "x1" in r:
            x1 = float(r["x1"])
            y1 = float(r.get("y1", y))
            return pymupdf.Rect(x, y, x1, y1)
    return None

def burn_annotations_to_pdf(
    source_pdf_path: Path,
    annotations_list: List[Dict[str, Any]],
    evaluation: Optional[Dict[str, Any]] = None,
    evaluator_name: str = ""
) -> bytes:
    if isinstance(source_pdf_path, (bytes, bytearray)):
        doc = pymupdf.open(stream=source_pdf_path, filetype="pdf")
    else:
        doc = pymupdf.open(str(source_pdf_path))

    for item in annotations_list:
        page_num = item.get("page", 1) - 1
        if page_num < 0 or page_num >= len(doc):
            continue
        page = doc[page_num]
        item_type = item.get("type", "")
        author = item.get("author") or evaluator_name or "Asistent"
        content = item.get("content") or item.get("comment") or ""
        font_id = _ensure_font(page)

        # Color parsing
        color_rgb = item.get("color_rgb")
        if not color_rgb:
            color_val = item.get("color", "#db3425")
            if isinstance(color_val, (list, tuple)) and len(color_val) >= 3:
                color_rgb = (float(color_val[0]), float(color_val[1]), float(color_val[2]))
            elif isinstance(color_val, str) and color_val.startswith("#") and len(color_val) == 7:
                color_rgb = (
                    int(color_val[1:3], 16) / 255.0,
                    int(color_val[3:5], 16) / 255.0,
                    int(color_val[5:7], 16) / 255.0
                )
            else:
                color_rgb = (0.858, 0.203, 0.145)
        elif isinstance(color_rgb, (list, tuple)) and len(color_rgb) >= 3:
            color_rgb = (float(color_rgb[0]), float(color_rgb[1]), float(color_rgb[2]))

        # 1. Direct text typed onto page (Typewriter in red/chosen color)
        if item_type == "text_direct":
            point = item.get("point", [])
            fontsize = item.get("fontsize", 12)
            if len(point) == 2 and content:
                try:
                    page.insert_text(
                        pymupdf.Point(point[0], point[1]),
                        content,
                        fontsize=fontsize,
                        color=color_rgb,
                        fontname=font_id
                    )
                except Exception as e:
                    print("Error inserting direct text:", e)

        # 2. Freehand Ink Drawing (Fix: pass seq of float tuples, not Points)
        elif item_type == "ink":
            strokes = item.get("strokes", [])
            width = float(item.get("width", 2.0))
            if strokes and len(strokes) > 0:
                try:
                    formatted_strokes = []
                    for s in strokes:
                        pt_list = [(float(p[0]), float(p[1])) for p in s if len(p) >= 2]
                        if len(pt_list) == 1:
                            pt_list.append((pt_list[0][0] + 0.5, pt_list[0][1] + 0.5))
                        if len(pt_list) >= 2:
                            formatted_strokes.append(pt_list)
                    if formatted_strokes:
                        ink = page.add_ink_annot(formatted_strokes)
                        ink.set_colors(stroke=color_rgb)
                        ink.set_border(width=width)
                        ink.update()
                except Exception as e:
                    print("Error adding ink annot:", e)

        # 3. Text Highlight (sharp vector highlight + baseline underline + native highlight annot)
        elif item_type == "highlight":
            rects_data = item.get("rects", [])
            rect_coords = item.get("rect", [])
            try:
                target_rects = []
                if rects_data and len(rects_data) > 0:
                    for r in rects_data:
                        fr = _parse_to_fitz_rect(r)
                        if fr and fr.width > 1 and fr.height > 1:
                            target_rects.append(fr)
                if not target_rects and rect_coords:
                    fr = _parse_to_fitz_rect(rect_coords)
                    if fr and fr.width > 1 and fr.height > 1:
                        target_rects.append(fr)

                # Draw beautiful in-app style highlight boxes with baseline underline
                for fr in target_rects:
                    page.draw_rect(fr, color=color_rgb, fill=color_rgb, fill_opacity=0.30, width=0.5)
                    page.draw_line(pymupdf.Point(fr.x0, fr.y1), pymupdf.Point(fr.x1, fr.y1), color=color_rgb, width=1.5)

                # Register standard PDF highlight annotation for reader sidebars/comments
                if target_rects:
                    quads = [fr.quad for fr in target_rects]
                    hl = page.add_highlight_annot(quads)
                    if hl:
                        hl.set_colors(stroke=color_rgb)
                        if content or author:
                            hl.set_info(content=_clean_unicode_str(content), title=_clean_unicode_str(author))
                        hl.update()
            except Exception as e:
                print("Error adding highlight:", e)

        # 3b. Text Strikeout
        elif item_type == "strikeout":
            rects_data = item.get("rects", [])
            rect_coords = item.get("rect", [])
            try:
                target_rects = []
                if rects_data and len(rects_data) > 0:
                    for r in rects_data:
                        fr = _parse_to_fitz_rect(r)
                        if fr and fr.width > 1 and fr.height > 1:
                            target_rects.append(fr)
                if not target_rects and rect_coords:
                    fr = _parse_to_fitz_rect(rect_coords)
                    if fr and fr.width > 1 and fr.height > 1:
                        target_rects.append(fr)

                for fr in target_rects:
                    mid_y = (fr.y0 + fr.y1) / 2.0
                    page.draw_line(pymupdf.Point(fr.x0, mid_y), pymupdf.Point(fr.x1, mid_y), color=color_rgb, width=1.4)

                if target_rects:
                    quads = [fr.quad for fr in target_rects]
                    so = page.add_strikeout_annot(quads)
                    if so:
                        so.set_colors(stroke=color_rgb)
                        if content or author:
                            so.set_info(content=_clean_unicode_str(content), title=_clean_unicode_str(author))
                        so.update()
            except Exception as e:
                print("Error adding strikeout:", e)

        # 4. Sticky Comment Note (Acrobat-style speech bubble vector icon + native popup)
        elif item_type == "note":
            point = item.get("point", [])
            if len(point) == 2:
                try:
                    px, py = float(point[0]), float(point[1])
                    _draw_acrobat_speech_bubble(page, px, py, color_rgb)
                    note = page.add_text_annot(pymupdf.Point(px, py), _clean_unicode_str(content), icon="Comment")
                    note.set_colors(stroke=color_rgb)
                    note.set_info(title=_clean_unicode_str(author), content=_clean_unicode_str(content))
                    note.update()
                except Exception as e:
                    print("Error adding note annot:", e)

        # 5. Rectangles (Solid border + matching semi-transparent fill)
        elif item_type == "rect":
            rect_coords = item.get("rect", [])
            if len(rect_coords) == 4:
                try:
                    r = pymupdf.Rect(*rect_coords)
                    page.draw_rect(r, color=color_rgb, fill=color_rgb, fill_opacity=0.18, width=2.0)
                    ra = page.add_rect_annot(r)
                    ra.set_colors(stroke=color_rgb)
                    if content or author:
                        ra.set_info(content=_clean_unicode_str(content), title=_clean_unicode_str(author))
                    ra.update()
                except Exception as e:
                    print("Error adding rect:", e)

        # 5b. Arrows & Lines (Crisp line with solid filled arrowhead)
        elif item_type == "arrow" or item_type == "line":
            p1 = item.get("p1", [])
            p2 = item.get("p2", [])
            if len(p1) == 2 and len(p2) == 2:
                try:
                    pt1 = pymupdf.Point(p1[0], p1[1])
                    pt2 = pymupdf.Point(p2[0], p2[1])
                    shape = page.new_shape()
                    shape.draw_line(pt1, pt2)
                    shape.finish(color=color_rgb, width=2.0)
                    if item_type == "arrow":
                        dx = pt2.x - pt1.x
                        dy = pt2.y - pt1.y
                        dist = math.hypot(dx, dy)
                        if dist > 3:
                            theta = math.atan2(dy, dx)
                            head_len = min(14.0, max(9.0, dist * 0.22))
                            h1_x = pt2.x - head_len * math.cos(theta - 0.42)
                            h1_y = pt2.y - head_len * math.sin(theta - 0.42)
                            h2_x = pt2.x - head_len * math.cos(theta + 0.42)
                            h2_y = pt2.y - head_len * math.sin(theta + 0.42)
                            arrowhead = [
                                pymupdf.Point(h1_x, h1_y),
                                pt2,
                                pymupdf.Point(h2_x, h2_y),
                                pymupdf.Point(h1_x, h1_y)
                            ]
                            shape.draw_polyline(arrowhead)
                            shape.finish(color=color_rgb, fill=color_rgb, width=1.0)
                    shape.commit()
                except Exception as e:
                    print("Error adding line/arrow:", e)

    # 6. Insert Modern Evaluation Card on Page 1
    if evaluation and len(doc) > 0:
        page0 = doc[0]
        font_id = _ensure_font(page0)
        font_bold_id = "dejavu-bold" if font_id == "dejavu" and os.path.exists(FONT_DEJAVU_BOLD) else font_id

        pts = float(evaluation.get("total_points", 0.0) or 0.0)
        grade = evaluation.get("grade")
        if not grade or str(grade).strip() not in ["A", "B", "C", "D", "E", "F"]:
            grade = calculate_grade_letter(pts)

        v = evaluation.get("vysledky_score", 0.0)
        d = evaluation.get("diskuze_score", 0.0)
        f = evaluation.get("format_score", 0.0)
        c = evaluation.get("chyby_score", 0.0)

        date_str = datetime.now().strftime("%d.%m.%Y")

        raw_deds = evaluation.get("deductions") or []
        deductions = [item for item in raw_deds if isinstance(item, dict) and item.get("reason")]

        p_rect = page0.rect
        banner_w = min(p_rect.width - 36, 520)
        banner_x = (p_rect.width - banner_w) / 2
        banner_y = 14
        card_h = 56

        card_rect = pymupdf.Rect(banner_x, banner_y, banner_x + banner_w, banner_y + card_h)
        page0.draw_rect(card_rect, color=(0.18, 0.32, 0.85), fill=(0.98, 0.985, 1.0), width=1.2, radius=0.03)

        accent_rect = pymupdf.Rect(banner_x, banner_y, banner_x + 5, banner_y + card_h)
        page0.draw_rect(accent_rect, color=(0.18, 0.32, 0.85), fill=(0.18, 0.32, 0.85), radius=0.08)

        grade_color = (0.08, 0.60, 0.32) if grade in ['A', 'B'] else ((0.85, 0.45, 0.08) if grade in ['C', 'D'] else (0.85, 0.12, 0.12))
        total_text = f"Celkem: {format_points(pts)} / 10 b  |  Známka: {grade}"
        page0.insert_text(
            pymupdf.Point(banner_x + 16, banner_y + 18),
            total_text,
            fontsize=11.5,
            color=grade_color,
            fontname=font_bold_id
        )

        cat_text = f"Výsledky: {format_points(v)}/3  •  Diskuze: {format_points(d)}/3  •  Formát: {format_points(f)}/2  •  Chyby: {format_points(c)}/2"
        page0.insert_text(
            pymupdf.Point(banner_x + 16, banner_y + 34),
            cat_text,
            fontsize=9.0,
            color=(0.18, 0.22, 0.32),
            fontname=font_id
        )

        footer_line = f"Hodnotil: {evaluator_name or 'Cvičící'}  |  Datum exportu: {date_str}"
        page0.insert_text(
            pymupdf.Point(banner_x + 16, banner_y + 48),
            footer_line,
            fontsize=8.0,
            color=(0.42, 0.46, 0.54),
            fontname=font_id
        )

        # Moodle note comment in top-right of banner
        moodle_lines = [
            f"HODNOCENÍ PROTOKOLU (MOODLE):",
            f"Celkem: {format_points(pts)} / 10 b (Známka: {grade})",
            f"Dílčí body: Výsledky: {format_points(v)}/3 | Diskuze: {format_points(d)}/3 | Formát: {format_points(f)}/2 | Chyby: {format_points(c)}/2",
            "",
            "Bodové srážky:"
        ]
        if deductions:
            cat_map = {"vysledky": "Výsledky", "diskuze": "Diskuze", "format": "Formát", "chyby": "Chyby"}
            for d_item in deductions:
                c_name = cat_map.get(d_item.get("category", ""), str(d_item.get("category", "")).capitalize())
                p_val = format_points(d_item.get("pts", 0.25))
                reason = (d_item.get("reason") or "").strip()
                moodle_lines.append(f"• [{c_name}] -{p_val} b: {reason}")
        else:
            moodle_lines.append("• Bez bodových srážek (plný počet bodů).")

        if evaluator_name:
            moodle_lines.append("")
            moodle_lines.append(f"Hodnotil: {evaluator_name}")
        moodle_lines.append(f"Datum exportu: {date_str}")
        moodle_comment_text = "\n".join(moodle_lines)

        moodle_note_x = banner_x + banner_w - 28
        moodle_note_y = banner_y + 20
        _draw_acrobat_speech_bubble(page0, moodle_note_x, moodle_note_y, (0.18, 0.32, 0.85))
        m_note = page0.add_text_annot(pymupdf.Point(moodle_note_x, moodle_note_y), _clean_unicode_str(moodle_comment_text), icon="Comment")
        m_note.set_colors(stroke=(0.18, 0.32, 0.85))
        m_note.set_info(title=_clean_unicode_str("Moodle komentář"), content=_clean_unicode_str(moodle_comment_text))
        m_note.update()

    output_bytes = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return output_bytes
