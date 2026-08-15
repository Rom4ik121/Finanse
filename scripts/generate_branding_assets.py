"""Generate FinWise launcher icons and native splash assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "assets"
ICON_SRC = ROOT / "icon.png"

BG = (0, 0, 0)
WHITE = (255, 255, 255)
ACCENT = (255, 255, 255)
MUTED = (160, 160, 160)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("segoeui.ttf", "arial.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _splash_logo(icon: Image.Image) -> Image.Image:
    logo = Image.new("RGBA", (720, 520), (0, 0, 0, 0))
    ic = icon.resize((220, 220), Image.Resampling.LANCZOS)
    logo.paste(ic, ((720 - 220) // 2, 20), ic)
    draw = ImageDraw.Draw(logo)
    title_font = _font(72)
    sub_font = _font(28)
    title = "FinWise"
    subtitle = "Personal finance tracker"
    tw = draw.textlength(title, font=title_font)
    sw = draw.textlength(subtitle, font=sub_font)
    draw.text(((720 - tw) / 2, 270), title, fill=WHITE, font=title_font)
    draw.rounded_rectangle(
        [((720 - 160) // 2, 350), ((720 + 160) // 2, 354)],
        radius=2,
        fill=ACCENT,
    )
    draw.text(((720 - sw) / 2, 360), subtitle, fill=MUTED, font=sub_font)
    return logo


def _padded_android_icon(icon: Image.Image) -> Image.Image:
    """Adaptive icon foreground: logo centered on transparent canvas."""
    size = 1024
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    scale = 0.62
    iw, ih = icon.size
    ni, nj = int(iw * scale), int(ih * scale)
    scaled = icon.resize((ni, nj), Image.Resampling.LANCZOS)
    canvas.paste(scaled, ((size - ni) // 2, (size - nj) // 2), scaled)
    return canvas


def main() -> None:
    icon = Image.open(ICON_SRC).convert("RGBA")
    ROOT.mkdir(parents=True, exist_ok=True)

    logo = _splash_logo(icon)
    for name in (
        "splash.png",
        "splash_android.png",
        "splash_ios.png",
        "splash_dark.png",
        "splash_dark_android.png",
        "splash_dark_ios.png",
    ):
        logo.save(ROOT / name)

    _padded_android_icon(icon).save(ROOT / "icon_android.png")
    print(f"Branding assets written to {ROOT}")


if __name__ == "__main__":
    main()
