#!/usr/bin/env python3
"""Record a synthetic-note CLI walkthrough; optionally render launch assets.

The CLI recording uses only the standard library. --render uses Pillow, an
optional authoring tool, not a dependency of the installed Skill.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def record() -> list[dict]:
    transcript = []
    with tempfile.TemporaryDirectory(prefix="slipbox-demo-") as tmp:
        library = Path(tmp) / "library"
        env = {**os.environ, "SLIPBOX_HOME": str(library), "PYTHONUTF8": "1"}

        def run(title, *args):
            result = subprocess.run([sys.executable, str(ROOT / "scripts/slipbox.py"), *args, "--json"],
                                    cwd=tmp, env=env, capture_output=True, text=True, encoding="utf-8", check=True)
            raw = json.loads(result.stdout)
            # Redact temporary machine paths, never alter the card contents or IDs.
            safe = result.stdout.replace(str(library).replace("\\", "\\\\"), "<temporary-library>")
            safe = safe.replace(str(library), "<temporary-library>")
            transcript.append({"title": title, "argv": ["python", "<installed-script>", *args, "--json"],
                               "exit_code": result.returncode, "output": json.loads(safe), "stderr": result.stderr})
            return raw

        run("01 / Start a private library", "init")
        run("02 / Give a tag a reusable meaning", "tag-add", "decisions", "--alias", "decision", "--description", "Ideas about making decisions")
        card = run("03 / Capture one thought", "add", "A useful meeting note ends with a clear decision.", "--tag", "decision")
        found = run("04 / Find it before the next meeting", "search", "meeting", "--tag", "decisions")
        if found["cards"][0]["id"] != card["id"]:
            raise ValueError("search did not return the captured card")
        run("05 / Review what changed this week", "review", "--days", "7")
        markdown = (library / "cards" / (card["id"] + ".md")).read_text(encoding="utf-8")
        transcript.append({"title": "06 / The note is your Markdown file", "argv": ["read", "<temporary-library>/cards/" + card["id"] + ".md"],
                           "exit_code": 0, "markdown": markdown})
    return transcript


def render(transcript: list[dict], output: Path):
    from PIL import Image, ImageDraw, ImageFont

    def font(size, mono=False):
        names = (["C:/Windows/Fonts/consola.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"] if mono else
                 ["C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
        for name in names:
            if Path(name).is_file():
                return ImageFont.truetype(name, size)
        return ImageFont.load_default()

    for theme in ("day", "night"):
        paper, ink, muted, accent, surface, line = (("#FCFBF7", "#173B49", "#5E746F", "#167E72", "#FFFFFF", "#D5E1DA") if theme == "day" else
                                                    ("#233A64", "#F8F6F0", "#C0D1E5", "#62E2D5", "#2E4B79", "#55749D"))
        image = Image.new("RGB", (1280, 640), paper)
        draw = ImageDraw.Draw(image)
        draw.text((74, 54), "slipbox", fill=ink, font=font(36))
        draw.text((74, 163), "AI-powered card notes", fill=ink, font=font(52))
        draw.text((74, 225), "across agents", fill=ink, font=font(52))
        draw.rounded_rectangle((75, 337, 127, 342), radius=2, fill=accent)
        for y, line_text in zip((369, 402, 435), ("Organize card notes with AI.", "Build your collection over time.", "Reuse it across agents.")):
            draw.text((74, y), line_text, fill=muted, font=font(25))
        draw.text((74, 551), "CARD NOTES FOR AI AGENTS  /  YOUR MARKDOWN, YOUR IDEAS", fill=muted, font=font(15))
        for i, (label, content) in enumerate((("01  CAPTURE", "A useful idea."), ("02  RETRIEVE", "Right when you need it."))):
            x, y = 830 + i * 34, 124 + i * 166
            draw.rounded_rectangle((x + 7, y + 12, x + 302, y + 222), radius=18, fill=line)
            draw.rounded_rectangle((x, y, x + 295, y + 210), radius=18, fill=surface, outline=line, width=1)
            draw.text((x + 24, y + 25), label, fill=accent, font=font(15))
            draw.text((x + 24, y + 76), content, fill=ink, font=font(19))
            for j, width in enumerate((216, 172, 196)):
                draw.line((x + 24, y + 127 + j * 15, x + width, y + 127 + j * 15), fill=line, width=2)
        image.save(output / f"social-{theme}.png", optimize=True)
        # Matching editable vector; the PNG is rendered from the same design.
        cards = "".join(f'<rect x="{830+i*34}" y="{124+i*166}" width="295" height="210" rx="18" fill="{surface}" stroke="{line}"/><text x="{854+i*34}" y="{174+i*166}" fill="{accent}" font-size="15">{label}</text><text x="{854+i*34}" y="{220+i*166}" fill="{ink}" font-size="19">{content}</text>'
                        for i, (label, content) in enumerate((("01 CAPTURE", "A useful idea."), ("02 RETRIEVE", "Right when you need it."))))
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="640" viewBox="0 0 1280 640"><rect width="1280" height="640" fill="{paper}"/><g font-family="Segoe UI,DejaVu Sans,sans-serif"><text x="74" y="98" fill="{ink}" font-size="36">slipbox</text><text x="74" y="219" fill="{ink}" font-size="52">AI-powered card notes</text><text x="74" y="281" fill="{ink}" font-size="52">across agents</text><rect x="75" y="337" width="52" height="5" rx="2" fill="{accent}"/><text x="74" y="400" fill="{muted}" font-size="25">Organize card notes with AI.</text><text x="74" y="433" fill="{muted}" font-size="25">Build your collection over time.</text><text x="74" y="466" fill="{muted}" font-size="25">Reuse it across agents.</text><text x="74" y="578" fill="{muted}" font-size="15">CARD NOTES FOR AI AGENTS / YOUR MARKDOWN, YOUR IDEAS</text>{cards}</g></svg>'
        (output / f"social-{theme}.svg").write_text(svg, encoding="utf-8")

    frames = []
    for step in transcript:
        image = Image.new("RGB", (1160, 710), "#233A64")
        draw = ImageDraw.Draw(image)
        draw.text((44, 24), "slipbox / a real local CLI walkthrough", fill="#F8F6F0", font=font(27))
        draw.text((44, 79), step["title"], fill="#62E2D5", font=font(24))
        draw.rounded_rectangle((34, 135, 1126, 638), radius=14, fill="#1E3154", outline="#55749D")
        command = "$ " + " ".join(step["argv"])
        import textwrap
        command_lines = textwrap.wrap(command, width=88)
        y = 159
        for row in command_lines:
            draw.text((58, y), row, fill="#9AF3E6", font=font(18, True))
            y += 27
        y += 16
        output_text = step.get("markdown") or json.dumps(step["output"], ensure_ascii=False, indent=2)
        rows = output_text.splitlines()
        visible = max(1, (610-y)//24)
        for row in rows[:visible]:
            draw.text((58, y), row[:98], fill="#F8F6F0", font=font(17, True))
            y += 24
        if len(rows) > visible:
            draw.text((58, 613), "... full unabridged output in demo-transcript.json", fill="#C0D1E5", font=font(15))
        draw.text((44, 663), "Synthetic notes. Actual CLI output. No host integration claim.", fill="#C0D1E5", font=font(17))
        frames.append(image)
    frames[3].save(output / "demo-static.png", optimize=True)
    frames[0].save(output / "cli-demo.gif", save_all=True, append_images=frames[1:], duration=8000, loop=0, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    transcript = record()
    (args.output / "demo-transcript.json").write_text(json.dumps({"source": "actual_local_cli", "synthetic_notes": True, "steps": transcript}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.render:
        render(transcript, args.output)
    print(f"Recorded {len(transcript)} real walkthrough steps in {args.output}")


if __name__ == "__main__":
    main()
