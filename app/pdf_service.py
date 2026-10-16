import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import pymupdf

FONT_DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

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

        # 3. Text Highlight (with quads if multiple lines)
        elif item_type == "highlight":
            rects_data = item.get("rects", [])
            rect_coords = item.get("rect", [])
            try:
                hl = None
                if rects_data and len(rects_data) > 0:
                    quads = []
                    for r in rects_data:
                        fr = _parse_to_fitz_rect(r)
                        if fr:
                            quads.append(fr.quad)
                    if quads:
                        hl = page.add_highlight_annot(quads)
                
                if not hl:
                    fr = _parse_to_fitz_rect(rect_coords)
                    if fr:
                        hl = page.add_highlight_annot(fr)
                
                if hl:
                    hl.set_colors(stroke=color_rgb)
                    if content or author:
                        hl.set_info(content=content, title=author)
                    hl.update()
            except Exception as e:
                print("Error adding highlight:", e)

        # 3b. Text Strikeout
        elif item_type == "strikeout":
            rects_data = item.get("rects", [])
            rect_coords = item.get("rect", [])
            try:
                so = None
                if rects_data and len(rects_data) > 0:
                    quads = []
                    for r in rects_data:
                        fr = _parse_to_fitz_rect(r)
                        if fr:
                            quads.append(fr.quad)
                    if quads:
                        so = page.add_strikeout_annot(quads)
                
                if not so:
                    fr = _parse_to_fitz_rect(rect_coords)
                    if fr:
                        so = page.add_strikeout_annot(fr)

                if so:
                    so.set_colors(stroke=color_rgb)
                    if content or author:
                        so.set_info(content=content, title=author)
                    so.update()
            except Exception as e:
                print("Error adding strikeout:", e)

        # 4. Sticky Comment Note (visible badge + popup)
        elif item_type == "note":
            point = item.get("point", [])
            if len(point) == 2:
                try:
                    px, py = float(point[0]), float(point[1])
                    # Draw a crisp visible badge pill on the page so it is visible in all PDF readers
                    page.draw_circle(pymupdf.Point(px, py), radius=6.5, color=color_rgb, fill=color_rgb)
                    page.draw_line(pymupdf.Point(px - 3.5, py), pymupdf.Point(px + 3.5, py), color=(1.0, 1.0, 1.0), width=1.5)
                    # Add standard PDF text popup note
                    note = page.add_text_annot(pymupdf.Point(px, py), content, icon="Comment")
                    note.set_colors(stroke=color_rgb)
                    note.set_info(title=author, content=content)
                    note.update()
                except Exception as e:
                    print("Error adding note annot:", e)

        # 5. Shapes (Rectangle with semi-transparent fill / Solid Arrow)
        elif item_type == "rect":
            rect_coords = item.get("rect", [])
            if len(rect_coords) == 4:
                try:
                    r = pymupdf.Rect(*rect_coords)
                    ra = page.add_rect_annot(r)
                    ra.set_colors(stroke=color_rgb, fill=color_rgb)
                    ra.set_opacity(0.18)
                    ra.set_border(width=1.5)
                    ra.update()
                except Exception as e:
                    print("Error adding rect:", e)

        elif item_type == "arrow" or item_type == "line":
            p1 = item.get("p1", [])
            p2 = item.get("p2", [])
            if len(p1) == 2 and len(p2) == 2:
                try:
                    la = page.add_line_annot(pymupdf.Point(p1[0], p1[1]), pymupdf.Point(p2[0], p2[1]))
                    la.set_colors(stroke=color_rgb, fill=color_rgb)
                    la.set_border(width=2.0)
                    if item_type == "arrow":
                        la.set_line_ends(pymupdf.PDF_ANNOT_LE_NONE, pymupdf.PDF_ANNOT_LE_CLOSED_ARROW)
                    la.update()
                except Exception as e:
                    print("Error adding line/arrow:", e)

    # 6. Insert Evaluation Header / Stamp on Page 1
    if evaluation and len(doc) > 0:
        page0 = doc[0]
        font_id = _ensure_font(page0)
        font_bold_id = "dejavu-bold" if font_id == "dejavu" and os.path.exists(FONT_DEJAVU_BOLD) else font_id

        pts = float(evaluation.get("total_points", 0.0) or 0.0)
        grade = evaluation.get("grade")
        if not grade or str(grade) not in ["A", "B", "C", "D", "E", "F"]:
            grade = calculate_grade_letter(pts)

        v = evaluation.get("vysledky_score", 0.0)
        d = evaluation.get("diskuze_score", 0.0)
        f = evaluation.get("format_score", 0.0)
        c = evaluation.get("chyby_score", 0.0)

        date_str = datetime.now().strftime("%d.%m.%Y")
        summary_line = f"Výsledky: {format_points(v)}/3, Diskuze: {format_points(d)}/3, Formát: {format_points(f)}/2, Chyby: {format_points(c)}/2"
        total_line = f"Celkem bodů: {format_points(pts)} / 10 | Známka: {grade}"
        footer_line = f"Opravil: {evaluator_name or 'Asistent'} | Datum: {date_str}"

        # Deductions list
        raw_deds = evaluation.get("deductions") or []
        deductions = [item for item in raw_deds if isinstance(item, dict) and item.get("reason")]
        display_deds = deductions[:7]

        p_rect = page0.rect
        banner_w = min(p_rect.width - 40, 500)
        banner_x = (p_rect.width - banner_w) / 2
        banner_y = 18

        # Calculate dynamic height
        base_h = 52
        ded_h = 0
        if deductions:
            ded_h = 16 + (len(display_deds) * 11) + (11 if len(deductions) > 7 else 0)
        card_h = base_h + ded_h

        # Background box
        card_rect = pymupdf.Rect(banner_x, banner_y, banner_x + banner_w, banner_y + card_h)
        page0.draw_rect(card_rect, color=(0.14, 0.38, 0.92), fill=(0.97, 0.98, 1.0), width=1.2)

        page0.insert_text(
            pymupdf.Point(banner_x + 12, banner_y + 16),
            summary_line,
            fontsize=9.5,
            color=(0.1, 0.15, 0.25),
            fontname=font_id
        )
        page0.insert_text(
            pymupdf.Point(banner_x + 12, banner_y + 31),
            total_line,
            fontsize=10.5,
            color=(0.85, 0.1, 0.2),
            fontname=font_bold_id
        )
        page0.insert_text(
            pymupdf.Point(banner_x + 12, banner_y + 44),
            footer_line,
            fontsize=7.5,
            color=(0.4, 0.45, 0.5),
            fontname=font_id
        )

        # Draw deduction details if present
        if deductions:
            div_y = banner_y + 51
            page0.draw_line(
                pymupdf.Point(banner_x + 12, div_y),
                pymupdf.Point(banner_x + banner_w - 12, div_y),
                color=(0.8, 0.85, 0.95),
                width=0.8
            )
            page0.insert_text(
                pymupdf.Point(banner_x + 12, div_y + 11),
                "Přehled bodových srážek:",
                fontsize=8.0,
                color=(0.15, 0.2, 0.3),
                fontname=font_bold_id
            )
            cat_map = {
                "vysledky": "Výsledky",
                "diskuze": "Diskuze",
                "format": "Formát",
                "chyby": "Chyby"
            }
            curr_y = div_y + 22
            for d_item in display_deds:
                cat_label = cat_map.get(d_item.get("category", ""), d_item.get("category", "").capitalize())
                pts_label = format_points(d_item.get("pts", 0.25))
                reason_clean = (d_item.get("reason") or "").strip()
                if len(reason_clean) > 65:
                    reason_clean = reason_clean[:62] + "..."
                d_line = f"• [{cat_label}] -{pts_label} b: {reason_clean}"
                page0.insert_text(
                    pymupdf.Point(banner_x + 14, curr_y),
                    d_line,
                    fontsize=7.2,
                    color=(0.65, 0.1, 0.1),
                    fontname=font_id
                )
                curr_y += 11
            
            if len(deductions) > 7:
                more_line = f"... a {len(deductions) - 7} dalších srážek (viz detailní komentáře v protokolu)"
                page0.insert_text(
                    pymupdf.Point(banner_x + 14, curr_y),
                    more_line,
                    fontsize=7.0,
                    color=(0.5, 0.5, 0.5),
                    fontname=font_id
                )

    output_bytes = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return output_bytes
