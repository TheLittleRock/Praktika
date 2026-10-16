import os
import io
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import pymupdf
import qrcode

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

def _smooth_stroke_chaikin(points: list, iterations: int = 2) -> list:
    """Chaikin's corner-cutting subdivision algorithm to produce smooth, organic curves from raw stroke points."""
    if not points or len(points) <= 2:
        return [(float(p[0]), float(p[1])) for p in points] if points else []
    pts = [(float(p[0]), float(p[1])) for p in points]
    for _ in range(iterations):
        smoothed = [pts[0]]
        for i in range(len(pts) - 1):
            p0 = pts[i]
            p1 = pts[i + 1]
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            smoothed.extend([q, r])
        smoothed.append(pts[-1])
        pts = smoothed
    return pts

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
    evaluator_name: str = "",
    share_token: Optional[str] = None,
    base_url: Optional[str] = None,
    student_name: Optional[str] = None,
    task_code: Optional[str] = None,
    general_comment: Optional[str] = None
) -> bytes:
    """
    Renders high-quality annotations into PDF:
    - Sharp rectangular highlights with baseline underlines (exact match with in-app appearance).
    - Elimination of double icons for free-flying notes (only native PDF annotation is used).
    - Chaikin smoothing for hand-drawn pen ink lines.
    - Interactive index badges [1], [2], ... on all comments linking to Appendix.
    - Dedicated Page 1 Evaluation Card with QR code & hyperlink to the public student web view.
    - Generated Appendix Summary Pages ('Přehled hodnocení a poznámek') with bidirectional links.
    """
    if isinstance(source_pdf_path, (bytes, bytearray)):
        doc = pymupdf.open(stream=source_pdf_path, filetype="pdf")
    else:
        doc = pymupdf.open(str(source_pdf_path))

    # Pre-index all annotations containing notes/comments for sequential numbering & appendix
    indexed_notes = []
    for item in annotations_list:
        content = (item.get("content") or item.get("comment") or "").strip()
        p_num = int(item.get("page", 1))
        item_type = item.get("type", "")
        
        # Approximate location for sorting top-to-bottom, page-by-page
        rect_c = item.get("rect") or (item.get("rects")[0] if item.get("rects") else None)
        pt_c = item.get("point")
        p1_c = item.get("p1")
        y_pos = 0.0
        x_pos = 0.0
        if rect_c and len(rect_c) >= 2:
            x_pos = float(rect_c[0])
            y_pos = float(rect_c[1])
        elif pt_c and len(pt_c) >= 2:
            x_pos = float(pt_c[0])
            y_pos = float(pt_c[1])
        elif p1_c and len(p1_c) >= 2:
            x_pos = float(p1_c[0])
            y_pos = float(p1_c[1])

        if content:
            indexed_notes.append({
                "annot": item,
                "page_num": p_num,
                "page_idx": p_num - 1,
                "x": x_pos,
                "y": y_pos,
                "content": content,
                "author": item.get("author") or evaluator_name or "Asistent",
                "type": item_type,
                "color": item.get("color", "#db3425"),
                "context_snippet": "",
                "badge_rect_on_page": None
            })

    # Sort sequentially across the document
    indexed_notes.sort(key=lambda n: (n["page_num"], n["y"], n["x"]))
    for idx, n in enumerate(indexed_notes):
        n["index"] = idx + 1
        n["annot"]["_badge_index"] = idx + 1

    # Render annotations across original pages
    for item in annotations_list:
        page_num = item.get("page", 1) - 1
        if page_num < 0 or page_num >= len(doc):
            continue
        page = doc[page_num]
        item_type = item.get("type", "")
        author = item.get("author") or evaluator_name or "Asistent"
        content = (item.get("content") or item.get("comment") or "").strip()
        badge_idx = item.get("_badge_index")
        font_id = _ensure_font(page)
        font_bold_id = "dejavu-bold" if font_id == "dejavu" and os.path.exists(FONT_DEJAVU_BOLD) else font_id

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

        # Helper to draw a crisp [1] badge on page
        def _draw_badge(bx, by, b_num):
            w = 16.0 if b_num < 10 else (22.0 if b_num < 100 else 28.0)
            h = 11.5
            brect = pymupdf.Rect(bx, by, bx + w, by + h)
            # Background white box with clean colored border
            page.draw_rect(brect, color=color_rgb, fill=(1.0, 1.0, 1.0), width=0.8, radius=0.15)
            # Center text inside badge
            page.insert_text(
                pymupdf.Point(bx + 2.5, by + h - 2.8),
                f"[{b_num}]",
                fontsize=7.5,
                color=color_rgb,
                fontname=font_bold_id
            )
            return brect

        # 1. Direct text typed onto page (Typewriter)
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

        # 2. Freehand Ink Drawing (with Chaikin curve smoothing)
        elif item_type == "ink":
            strokes = item.get("strokes", [])
            width = float(item.get("width", 2.0))
            if strokes and len(strokes) > 0:
                try:
                    formatted_strokes = []
                    for s in strokes:
                        if len(s) >= 2:
                            smoothed = _smooth_stroke_chaikin(s, iterations=2)
                            formatted_strokes.append(smoothed)
                        elif len(s) == 1:
                            formatted_strokes.append([
                                (float(s[0][0]), float(s[0][1])),
                                (float(s[0][0]) + 0.5, float(s[0][1]) + 0.5)
                            ])
                    if formatted_strokes:
                        ink = page.add_ink_annot(formatted_strokes)
                        ink.set_colors(stroke=color_rgb)
                        ink.set_border(width=width)
                        ink.update()
                except Exception as e:
                    print("Error adding ink annot:", e)

        # 3. Text Highlight (Sharp vector boxes + baseline underline + badge; no rounded PDFium pill overlay)
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

                # Draw sharp in-app style highlight boxes with baseline underline
                extracted_words = []
                for fr in target_rects:
                    page.draw_rect(fr, color=None, fill=color_rgb, fill_opacity=0.35)
                    page.draw_line(pymupdf.Point(fr.x0, fr.y1), pymupdf.Point(fr.x1, fr.y1), color=color_rgb, width=1.4)
                    if content:
                        try:
                            ra = page.add_rect_annot(fr)
                            ra.set_border(width=0)
                            ra.set_colors(stroke=None, fill=None)
                            ra.set_info(content=_clean_unicode_str(content), title=_clean_unicode_str(author))
                            ra.set_opacity(0)
                            ra.update()
                        except Exception:
                            pass
                    w_text = page.get_text("text", clip=fr).strip()
                    if w_text:
                        extracted_words.append(w_text)

                snippet = " ".join(extracted_words).strip()
                if len(snippet) > 110:
                    snippet = snippet[:107] + "..."

                # Draw numbered badge next to highlight
                if target_rects and badge_idx:
                    fr0 = target_rects[0]
                    # Position badge at top-left of the highlighted area
                    b_x = max(6.0, fr0.x0 - 20.0) if fr0.x0 >= 26.0 else fr0.x0
                    b_y = max(6.0, fr0.y0 - 12.0)
                    brect = _draw_badge(b_x, b_y, badge_idx)
                    for n in indexed_notes:
                        if n.get("annot") is item:
                            n["badge_rect_on_page"] = brect
                            n["context_snippet"] = snippet
                            break
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
                    page.draw_line(pymupdf.Point(fr.x0, mid_y), pymupdf.Point(fr.x1, mid_y), color=color_rgb, width=1.5)
                    if content:
                        try:
                            ra = page.add_rect_annot(fr)
                            ra.set_border(width=0)
                            ra.set_colors(stroke=None, fill=None)
                            ra.set_info(content=_clean_unicode_str(content), title=_clean_unicode_str(author))
                            ra.set_opacity(0)
                            ra.update()
                        except Exception:
                            pass

                if target_rects and badge_idx:
                    fr0 = target_rects[0]
                    brect = _draw_badge(max(6.0, fr0.x0 - 20.0), max(6.0, fr0.y0 - 12.0), badge_idx)
                    for n in indexed_notes:
                        if n.get("annot") is item:
                            n["badge_rect_on_page"] = brect
                            break
            except Exception as e:
                print("Error adding strikeout:", e)

        # 4. Sticky Comment Note (Native Acrobat icon only - no duplicate vector bubble)
        elif item_type == "note":
            point = item.get("point", [])
            if len(point) == 2:
                try:
                    px, py = float(point[0]), float(point[1])
                    note = page.add_text_annot(pymupdf.Point(px, py), _clean_unicode_str(content), icon="Comment")
                    note.set_colors(stroke=color_rgb)
                    note.set_info(title=_clean_unicode_str(author), content=_clean_unicode_str(content))
                    note.update()

                    if badge_idx:
                        brect = _draw_badge(px + 16.0, py - 6.0, badge_idx)
                        for n in indexed_notes:
                            if n.get("annot") is item:
                                n["badge_rect_on_page"] = brect
                                break
                except Exception as e:
                    print("Error adding note annot:", e)

        # 5. Rectangles (Solid border + matching semi-transparent fill)
        elif item_type == "rect":
            rect_coords = item.get("rect", [])
            if len(rect_coords) == 4:
                try:
                    r = pymupdf.Rect(*rect_coords)
                    page.draw_rect(r, color=color_rgb, fill=color_rgb, fill_opacity=0.18, width=2.0)
                    if content or author:
                        ra = page.add_rect_annot(r)
                        ra.set_colors(stroke=color_rgb)
                        ra.set_info(content=_clean_unicode_str(content), title=_clean_unicode_str(author))
                        ra.update()
                    if badge_idx:
                        brect = _draw_badge(r.x0, max(6.0, r.y0 - 13.0), badge_idx)
                        for n in indexed_notes:
                            if n.get("annot") is item:
                                n["badge_rect_on_page"] = brect
                                break
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

    # 6. Evaluation Card with QR Code and Moodle Note on Page 1
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
        banner_w = min(p_rect.width - 36, 530)
        banner_x = (p_rect.width - banner_w) / 2
        banner_y = 12
        card_h = 58

        card_rect = pymupdf.Rect(banner_x, banner_y, banner_x + banner_w, banner_y + card_h)
        page0.draw_rect(card_rect, color=(0.18, 0.32, 0.85), fill=(0.98, 0.985, 1.0), width=1.2, radius=0.03)

        accent_rect = pymupdf.Rect(banner_x, banner_y, banner_x + 5, banner_y + card_h)
        page0.draw_rect(accent_rect, color=(0.18, 0.32, 0.85), fill=(0.18, 0.32, 0.85), radius=0.08)

        grade_color = (0.08, 0.60, 0.32) if grade in ['A', 'B'] else ((0.85, 0.45, 0.08) if grade in ['C', 'D'] else (0.85, 0.12, 0.12))
        total_text = f"Celkem: {format_points(pts)} / 10 b  |  Známka: {grade}"
        page0.insert_text(
            pymupdf.Point(banner_x + 14, banner_y + 17),
            total_text,
            fontsize=11.5,
            color=grade_color,
            fontname=font_bold_id
        )

        cat_text = f"Výsledky: {format_points(v)}/3  •  Diskuze: {format_points(d)}/3  •  Formát: {format_points(f)}/2  •  Chyby: {format_points(c)}/2"
        page0.insert_text(
            pymupdf.Point(banner_x + 14, banner_y + 33),
            cat_text,
            fontsize=8.5,
            color=(0.18, 0.22, 0.32),
            fontname=font_id
        )

        footer_line = f"Hodnotil: {evaluator_name or 'Cvičící'}  |  Datum exportu: {date_str}"
        page0.insert_text(
            pymupdf.Point(banner_x + 14, banner_y + 47),
            footer_line,
            fontsize=7.8,
            color=(0.42, 0.46, 0.54),
            fontname=font_id
        )

        # Standalone native Moodle sticky note icon
        moodle_lines = [
            "HODNOCENÍ PROTOKOLU (MOODLE):",
            f"Celkem: {format_points(pts)} / 10 b (Známka: {grade})",
            f"Dílčí body: Výsledky: {format_points(v)}/3 | Diskuze: {format_points(d)}/3 | Formát: {format_points(f)}/2 | Chyby: {format_points(c)}/2",
            "",
            "Bodové srážky:"
        ]
        cat_map = {"vysledky": "Výsledky", "diskuze": "Diskuze", "format": "Formát", "chyby": "Chyby"}
        if deductions:
            for d_item in deductions:
                c_name = cat_map.get(d_item.get("category", ""), str(d_item.get("category", "")).capitalize())
                p_val = format_points(d_item.get("pts", 0.25))
                reason = (d_item.get("reason") or "").strip()
                moodle_lines.append(f"• [{c_name}] -{p_val} b: {reason}")
        else:
            moodle_lines.append("• Bez bodových srážek (plný počet bodů).")

        gen_comm = (general_comment or (evaluation.get("general_comment") if evaluation else "") or "").strip()
        if gen_comm:
            moodle_lines.append("")
            moodle_lines.append("Slovní hodnocení protokolu:")
            moodle_lines.append(gen_comm)

        if evaluator_name:
            moodle_lines.append("")
            moodle_lines.append(f"Hodnotil: {evaluator_name}")
        moodle_lines.append(f"Datum exportu: {date_str}")
        moodle_comment_text = "\n".join(moodle_lines)

        moodle_note_x = banner_x + banner_w - 76
        moodle_note_y = banner_y + 16
        m_note = page0.add_text_annot(pymupdf.Point(moodle_note_x, moodle_note_y), _clean_unicode_str(moodle_comment_text), icon="Comment")
        m_note.set_colors(stroke=(0.18, 0.32, 0.85))
        m_note.set_info(title=_clean_unicode_str("Moodle komentář"), content=_clean_unicode_str(moodle_comment_text))
        m_note.update()

        # QR Code for student web view
        if share_token:
            web_url = f"{base_url.rstrip('/')}/v/{share_token}" if base_url else f"https://praktika.physics.muni.cz/v/{share_token}"
            try:
                qr = qrcode.QRCode(box_size=2, border=1)
                qr.add_data(web_url)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                qr_buf = io.BytesIO()
                qr_img.save(qr_buf, format="PNG")
                
                qr_x = banner_x + banner_w - 50
                qr_y = banner_y + 7
                qr_rect = pymupdf.Rect(qr_x, qr_y, qr_x + 44, qr_y + 44)
                page0.insert_image(qr_rect, stream=qr_buf.getvalue())
                
                # Clickable link over the QR code
                page0.insert_link({
                    "kind": pymupdf.LINK_URI,
                    "uri": web_url,
                    "from": qr_rect
                })
                
                # Small text below QR
                page0.insert_text(
                    pymupdf.Point(qr_x - 1, qr_y + 49),
                    "Web náhled ↗",
                    fontsize=6.5,
                    color=(0.18, 0.32, 0.85),
                    fontname=font_bold_id
                )
            except Exception as e:
                print("QR code generation error:", e)

    # 7. Generate Appendix Summary Pages ("PŘEHLED HODNOCENÍ A POZNÁMEK")
    if indexed_notes or (evaluation and evaluation.get("deductions")) or gen_comm:
        first_page_rect = doc[0].rect if len(doc) > 0 else pymupdf.Rect(0, 0, 595, 842)
        app_page = doc.new_page(width=first_page_rect.width, height=first_page_rect.height)
        font_id = _ensure_font(app_page)
        font_bold_id = "dejavu-bold" if font_id == "dejavu" and os.path.exists(FONT_DEJAVU_BOLD) else font_id

        margin_x = 36.0
        content_w = first_page_rect.width - (2 * margin_x)
        cur_y = 36.0

        def _draw_appendix_header(pg, cur_page_idx, total_app_pages_hint=1):
            nonlocal cur_y
            pg.draw_rect(
                pymupdf.Rect(margin_x, cur_y, margin_x + content_w, cur_y + 36),
                color=None,
                fill=(0.95, 0.965, 0.99),
                radius=0.04
            )
            pg.draw_line(
                pymupdf.Point(margin_x, cur_y + 36),
                pymupdf.Point(margin_x + content_w, cur_y + 36),
                color=(0.18, 0.32, 0.85),
                width=1.5
            )
            pg.insert_text(
                pymupdf.Point(margin_x + 12, cur_y + 18),
                "PŘEHLED HODNOCENÍ A POZNÁMEK K PROTOKOLU",
                fontsize=11.0,
                color=(0.12, 0.22, 0.65),
                fontname=font_bold_id
            )
            sub_title = f"Student: {student_name or 'Student'}  •  Úloha: {task_code or 'Měření'}  •  Hodnotil: {evaluator_name or 'Cvičící'}"
            pg.insert_text(
                pymupdf.Point(margin_x + 12, cur_y + 30),
                sub_title,
                fontsize=7.8,
                color=(0.38, 0.42, 0.50),
                fontname=font_id
            )
            cur_y += 46.0

        _draw_appendix_header(app_page, 0)

        # Overview of deductions if any exist
        cat_map = {"vysledky": "Výsledky", "diskuze": "Diskuze", "format": "Formát", "chyby": "Chyby"}
        raw_deds = evaluation.get("deductions") or [] if evaluation else []
        deductions_list = [item for item in raw_deds if isinstance(item, dict) and item.get("reason")]
        if deductions_list:
            ded_h = 22.0 + (len(deductions_list) * 13.5)
            ded_rect = pymupdf.Rect(margin_x, cur_y, margin_x + content_w, cur_y + ded_h)
            app_page.draw_rect(ded_rect, color=(0.85, 0.40, 0.15), fill=(1.0, 0.985, 0.97), width=0.8, radius=0.03)
            app_page.insert_text(
                pymupdf.Point(margin_x + 10, cur_y + 13),
                "PŘEHLED BODOVÝCH SRÁŽEK (MOODLE)",
                fontsize=8.5,
                color=(0.75, 0.25, 0.05),
                fontname=font_bold_id
            )
            d_y = cur_y + 25.0
            for d_item in deductions_list:
                c_name = cat_map.get(d_item.get("category", ""), str(d_item.get("category", "")).capitalize())
                p_val = format_points(d_item.get("pts", 0.25))
                reason = (d_item.get("reason") or "").strip()
                app_page.insert_text(
                    pymupdf.Point(margin_x + 14, d_y),
                    f"• [{c_name}] -{p_val} b: {reason}",
                    fontsize=8.0,
                    color=(0.20, 0.22, 0.26),
                    fontname=font_id
                )
                d_y += 13.5
            cur_y += ded_h + 12.0

        # Overall protocol comment card
        if gen_comm:
            lines_est = max(1, math.ceil(len(gen_comm) / 78))
            gen_h = 26.0 + (lines_est * 13.0)
            gen_h = max(40.0, min(180.0, gen_h))
            if cur_y + gen_h > first_page_rect.height - 40.0:
                app_page = doc.new_page(width=first_page_rect.width, height=first_page_rect.height)
                font_id = _ensure_font(app_page)
                font_bold_id = "dejavu-bold" if font_id == "dejavu" and os.path.exists(FONT_DEJAVU_BOLD) else font_id
                cur_y = 36.0
                _draw_appendix_header(app_page, 1)

            gen_rect = pymupdf.Rect(margin_x, cur_y, margin_x + content_w, cur_y + gen_h)
            app_page.draw_rect(gen_rect, color=(0.18, 0.45, 0.85), fill=(0.96, 0.98, 1.0), width=0.8, radius=0.03)
            app_page.draw_rect(pymupdf.Rect(margin_x, cur_y, margin_x + 4, cur_y + gen_h), color=(0.18, 0.45, 0.85), fill=(0.18, 0.45, 0.85), radius=0.05)
            app_page.insert_text(
                pymupdf.Point(margin_x + 12, cur_y + 13),
                "SLOVNÍ HODNOCENÍ CELÉHO PROTOKOLU",
                fontsize=8.5,
                color=(0.12, 0.28, 0.70),
                fontname=font_bold_id
            )
            app_page.insert_textbox(
                pymupdf.Rect(margin_x + 12, cur_y + 18, margin_x + content_w - 12, cur_y + gen_h - 4),
                _clean_unicode_str(gen_comm),
                fontsize=8.2,
                color=(0.15, 0.18, 0.25),
                fontname=font_id
            )
            cur_y += gen_h + 12.0

        # Render structured cards for each indexed note
        for n in indexed_notes:
            comment_text = n["content"]
            lines_est = max(1, math.ceil(len(comment_text) / 78))
            has_snippet = bool(n.get("context_snippet"))
            
            card_h = 36.0 + (lines_est * 12.0) + (14.0 if has_snippet else 0.0)
            card_h = max(42.0, min(140.0, card_h))

            # Page overflow check
            if cur_y + card_h > first_page_rect.height - 40.0:
                app_page = doc.new_page(width=first_page_rect.width, height=first_page_rect.height)
                font_id = _ensure_font(app_page)
                font_bold_id = "dejavu-bold" if font_id == "dejavu" and os.path.exists(FONT_DEJAVU_BOLD) else font_id
                cur_y = 36.0
                _draw_appendix_header(app_page, 1)

            card_rect = pymupdf.Rect(margin_x, cur_y, margin_x + content_w, cur_y + card_h)
            
            # Card background & border
            app_page.draw_rect(card_rect, color=(0.82, 0.85, 0.90), fill=(0.985, 0.99, 1.0), width=0.8, radius=0.03)
            
            # Left accent strip matching annotation color
            c_rgb = (0.858, 0.203, 0.145)
            if isinstance(n.get("color"), str) and n["color"].startswith("#") and len(n["color"]) == 7:
                c_rgb = (
                    int(n["color"][1:3], 16) / 255.0,
                    int(n["color"][3:5], 16) / 255.0,
                    int(n["color"][5:7], 16) / 255.0
                )
            app_page.draw_rect(pymupdf.Rect(margin_x, cur_y, margin_x + 4, cur_y + card_h), color=c_rgb, fill=c_rgb, radius=0.05)

            # Card Header: Badge [X] and Page reference
            app_page.insert_text(
                pymupdf.Point(margin_x + 12, cur_y + 14),
                f"[{n['index']}]",
                fontsize=9.5,
                color=c_rgb,
                fontname=font_bold_id
            )
            type_label = "Zvýrazněný text" if n["type"] == "highlight" else ("Volná poznámka" if n["type"] == "note" else "Anotace v textu")
            app_page.insert_text(
                pymupdf.Point(margin_x + 36, cur_y + 14),
                f"Strana {n['page_num']}  •  {type_label}",
                fontsize=8.5,
                color=(0.15, 0.20, 0.28),
                fontname=font_bold_id
            )

            # Back link button on card
            back_btn_rect = pymupdf.Rect(margin_x + content_w - 95, cur_y + 3, margin_x + content_w - 8, cur_y + 17)
            app_page.draw_rect(back_btn_rect, color=(0.18, 0.32, 0.85), fill=(0.93, 0.95, 1.0), width=0.6, radius=0.15)
            app_page.insert_text(
                pymupdf.Point(back_btn_rect.x0 + 6, back_btn_rect.y1 - 3.5),
                f"Zpět na str. {n['page_num']} ↗",
                fontsize=7.2,
                color=(0.18, 0.32, 0.85),
                fontname=font_bold_id
            )
            
            # Bidirectional link: Appendix card -> Original Page
            app_page.insert_link({
                "kind": pymupdf.LINK_GOTO,
                "page": n["page_idx"],
                "to": pymupdf.Point(n["x"], max(0, n["y"] - 30)),
                "from": back_btn_rect
            })

            # Bidirectional link: Original Page Badge -> Appendix card
            if n.get("badge_rect_on_page"):
                orig_page = doc[n["page_idx"]]
                orig_page.insert_link({
                    "kind": pymupdf.LINK_GOTO,
                    "page": app_page.number,
                    "to": pymupdf.Point(margin_x, max(0, cur_y - 20)),
                    "from": n["badge_rect_on_page"]
                })

            inner_y = cur_y + 25.0

            # Optional Context snippet
            if has_snippet:
                app_page.insert_text(
                    pymupdf.Point(margin_x + 12, inner_y),
                    f"Kontext: „{n['context_snippet']}“",
                    fontsize=7.6,
                    color=(0.40, 0.45, 0.52),
                    fontname=font_id
                )
                inner_y += 12.0

            # Full comment text wrapped cleanly
            text_rect = pymupdf.Rect(margin_x + 12, inner_y - 2, margin_x + content_w - 12, cur_y + card_h - 4)
            app_page.insert_textbox(
                text_rect,
                comment_text,
                fontsize=8.5,
                color=(0.12, 0.15, 0.20),
                fontname=font_id
            )

            cur_y += card_h + 8.0

    output_bytes = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return output_bytes
