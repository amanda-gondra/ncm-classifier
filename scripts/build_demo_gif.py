"""Assemble the demo GIF from the frames captured by web/scripts/capture-media.mjs.

Usage:
    python scripts/build_demo_gif.py [--frames docs/media/frames] [--out docs/media/demo.gif]

The frames are screenshots of the real site calling the real API; this script only puts
them in sequence, with the duration recorded for each one, and scales them to a width
that keeps the file small enough for social networks. The frames folder is deleted
afterwards unless --keep-frames is given.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Final

from PIL import Image

WIDTH: Final = 960
COLORS: Final = 128


def load_frames(frames_dir: Path) -> tuple[list[Image.Image], list[int]]:
    manifest = json.loads((frames_dir / "frames.json").read_text(encoding="utf-8"))
    images: list[Image.Image] = []
    durations: list[int] = []
    for entry in manifest:
        with Image.open(frames_dir / entry["file"]) as source:
            frame = source.convert("RGB")
        height = round(frame.height * WIDTH / frame.width)
        frame = frame.resize((WIDTH, height), Image.Resampling.LANCZOS)
        images.append(frame.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT))
        durations.append(int(entry["durationMs"]))
    return images, durations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=Path, default=Path("docs/media/frames"))
    parser.add_argument("--out", type=Path, default=Path("docs/media/demo.gif"))
    parser.add_argument("--keep-frames", action="store_true")
    args = parser.parse_args()

    images, durations = load_frames(args.frames)
    if not images:
        raise SystemExit(f"No frames listed in {args.frames / 'frames.json'}")
    images[0].save(
        args.out,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"{args.out}: {len(images)} frames, {args.out.stat().st_size / 1024:.0f} KB")
    if not args.keep_frames:
        shutil.rmtree(args.frames)


if __name__ == "__main__":
    main()
