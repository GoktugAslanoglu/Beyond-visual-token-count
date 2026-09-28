"""Coverage-preserving CPU renderer. Processor counts must come from an adapter."""
import hashlib
import json
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont


def sha(data):
    return hashlib.sha256(data).hexdigest()


def layout(text, font_path, font_size, width, height, margin=24, spacing=2, pages=1):
    if not text or type(pages) is not int or pages < 1:
        raise ValueError("Nonempty memory and positive page count required")
    if min(width, height) <= 2 * margin or margin < 0 or spacing < 0:
        raise ValueError("Invalid page geometry")
    with TTFont(str(font_path), lazy=True) as metadata:
        cmap = metadata.getBestCmap() or {}
    missing = sorted({ord(c) for c in text if c != "\n" and (ord(c) not in cmap or unicodedata.category(c).startswith("C"))})
    if missing:
        raise ValueError(f"Unsupported glyphs, no silent substitution: {missing}")
    font = ImageFont.truetype(str(font_path), font_size)
    ascent, descent = font.getmetrics()
    line_height = ascent + descent + spacing
    usable = width - 2 * margin
    lines = []
    start = 0
    current = ""
    for index, character in enumerate(text):
        if character == "\n":
            lines.append({"start": start, "end": index + 1, "text": current})
            start, current = index + 1, ""
            continue
        trial = current + character
        bbox = font.getbbox(trial, anchor="ls")
        extent = max(float(font.getlength(trial)), float(bbox[2])) - min(0, bbox[0])
        if extent > usable:
            if not current:
                raise ValueError("Single glyph cannot fit page width")
            lines.append({"start": start, "end": index, "text": current})
            start, current = index, character
            bbox = font.getbbox(current, anchor="ls")
            if max(float(font.getlength(current)), float(bbox[2])) - min(0, bbox[0]) > usable:
                raise ValueError("Single glyph cannot fit page width")
        else:
            current = trial
    if start < len(text):
        lines.append({"start": start, "end": len(text), "text": current})
    if len(lines) < pages:
        raise ValueError("Requested page count would create empty pages")
    q, remainder = divmod(len(lines), pages)
    result, cursor = [], 0
    for page_index in range(pages):
        count = q + int(page_index < remainder)
        page_lines = []
        for i, line in enumerate(lines[cursor:cursor + count]):
            bbox = font.getbbox(line["text"], anchor="ls")
            x = margin - min(0, bbox[0])
            y = margin + ascent + i * line_height
            positioned = [x + bbox[0], y + bbox[1], x + bbox[2], y + bbox[3]]
            if positioned[0] < margin or positioned[1] < margin or positioned[2] > width - margin or positioned[3] > height - margin:
                raise ValueError("Content cannot fit requested page height/width without clipping")
            page_lines.append({**line, "x": x, "baseline_y": y, "bbox": positioned})
        result.append({"page_index": page_index, "source_start": page_lines[0]["start"],
                       "source_end": page_lines[-1]["end"], "lines": page_lines,
                       "width": width, "height": height, "glyph_em_px": font_size})
        cursor += count
    assert "".join(text[p["source_start"]:p["source_end"]] for p in result) == text
    return font, result


def render(text, output_dir, font_path, font_size, width, height, margin=24, spacing=2, pages=1):
    """Create new PNGs/text segments; never overwrite an existing output directory."""
    font, plan = layout(text, font_path, font_size, width, height, margin, spacing, pages)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    outputs = []
    for page in plan:
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        for line in page["lines"]:
            draw.text((line["x"], line["baseline_y"]), line["text"], fill="black", font=font, anchor="ls")
        png = directory / f"page_{page['page_index']:03d}.png"
        segment = directory / f"page_{page['page_index']:03d}.txt"
        image.save(png, format="PNG")
        segment.write_bytes(text[page["source_start"]:page["source_end"]].encode("utf-8"))
        outputs.append({**page, "image": png.name, "image_sha256": sha(png.read_bytes()),
                        "segment": segment.name, "segment_sha256": sha(segment.read_bytes())})
    metadata = {"status": "planned", "coverage_verified": True, "processor_measured": False,
                "source_sha256": sha(text.encode("utf-8")), "source_characters": len(text),
                "font_sha256": sha(Path(font_path).read_bytes()), "font_size_px": font_size,
                "margin_px": margin, "spacing_px": spacing, "pages": outputs}
    (directory / "render.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def search_budget(text, output_dir, candidates, measure_processed_chat, source_tokens, c_target, tolerance=0.1):
    """Deterministic label-blind search, retaining all candidate render/count records.

    Candidates are predeclared geometry/font dictionaries. The callback receives
    image paths and must invoke the real pinned processor; no proxy counter is
    supplied by this module. Output remains processor calibration, not inference.
    """
    if source_tokens < 1 or c_target <= 0 or not 0 <= tolerance < 1 or not candidates:
        raise ValueError("Invalid budget search contract")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    trials = []
    for i, config in enumerate(candidates):
        folder = directory / f"candidate_{i:04d}"
        try:
            metadata = render(text, folder, **config)
        except ValueError as error:
            trials.append({"index": i, "feasible": False, "reason": str(error)})
            continue
        measured = measure_processed_chat([folder / p["image"] for p in metadata["pages"]])
        vision = measured["vision_tokens"]
        if type(vision) is not int or vision < 1 or not measured.get("processor_identity"):
            raise ValueError("Real processor counts and identity are required")
        ratio = source_tokens / vision
        trials.append({"index": i, "feasible": abs(ratio / c_target - 1) <= tolerance,
                       "source_to_vision_ratio": ratio, "relative_error": abs(ratio / c_target - 1),
                       "measurement": measured, "render_manifest": str(folder / "render.json")})
    valid = [t for t in trials if t["feasible"]]
    chosen = min(valid, key=lambda t: (t["relative_error"], t["index"]))["index"] if valid else None
    result = {"status": "planned", "c_target": c_target, "tolerance": tolerance,
              "selected_candidate": chosen, "trials": trials}
    (directory / "search.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
