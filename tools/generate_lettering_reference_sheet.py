from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from webtoon_studio.lettering import _color, _draw_seamless_dialogue_balloon


FONT_DIR = ROOT / "assets" / "fonts"
STANDARD_PATH = ROOT / "assets" / "lettering" / "lettering-standard-v2.json"
DEFAULT_OUTPUT = ROOT / "assets" / "lettering" / "lettering-standard-sheet.png"


def load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / filename), size=size)


def centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font: ImageFont.FreeTypeFont, fill: str) -> None:
    left, top, right, bottom = box
    bounds = draw.multiline_textbbox((0, 0), text, font=font, spacing=7, align="center")
    x = left + (right - left - (bounds[2] - bounds[0])) // 2
    y = top + (bottom - top - (bounds[3] - bounds[1])) // 2 - bounds[1]
    draw.multiline_text((x, y), text, font=font, fill=fill, spacing=7, align="center")


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str = "#ffffff") -> None:
    draw.rounded_rectangle(box, radius=28, fill=fill, outline="#d9d2c7", width=2)


def cubic_points(start: tuple[float, float], control_one: tuple[float, float], control_two: tuple[float, float], end: tuple[float, float]) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for index in range(13):
        t = index / 12
        inverse = 1 - t
        x = inverse**3 * start[0] + 3 * inverse**2 * t * control_one[0] + 3 * inverse * t**2 * control_two[0] + t**3 * end[0]
        y = inverse**3 * start[1] + 3 * inverse**2 * t * control_one[1] + 3 * inverse * t**2 * control_two[1] + t**3 * end[1]
        points.append((round(x), round(y)))
    return points


def bubble(image: Image.Image, box: tuple[int, int, int, int], tail: tuple[int, int] | None = None) -> None:
    """Use the production union-contour renderer in the review reference."""
    _draw_seamless_dialogue_balloon(
        image,
        box,
        tail,
        _color("#fffefd"),
        _color("#24201e"),
        4,
    )


def cloud(image: Image.Image, box: tuple[int, int, int, int]) -> None:
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    left, top, right, bottom = box
    center_x, center_y = (left + right) // 2, (top + bottom) // 2
    draw.ellipse((left + 24, top + 28, right - 24, bottom - 24), fill=255)
    for x, y, radius in ((-105, -25, 43), (-45, -52, 42), (40, -54, 45), (108, -18, 42), (104, 37, 38), (22, 54, 40), (-65, 44, 38), (-115, 12, 37)):
        draw.ellipse((center_x + x - radius, center_y + y - radius, center_x + x + radius, center_y + y + radius), fill=255)
    outline = mask.filter(ImageFilter.MaxFilter(9))
    image.paste("#514a45", mask=outline)
    image.paste("#fffefd", mask=mask)


def dashed_line(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: str, width: int = 3, dash: int = 12) -> None:
    distance = math.dist(start, end)
    if distance == 0:
        return
    unit_x, unit_y = (end[0] - start[0]) / distance, (end[1] - start[1]) / distance
    position = 0.0
    while position < distance:
        next_position = min(distance, position + dash)
        draw.line(
            [
                (round(start[0] + unit_x * position), round(start[1] + unit_y * position)),
                (round(start[0] + unit_x * next_position), round(start[1] + unit_y * next_position)),
            ],
            fill=fill,
            width=width,
        )
        position += dash * 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Korean webtoon lettering reference sheet.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    standard = json.loads(STANDARD_PATH.read_text(encoding="utf-8"))
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGBA", (1080, 2160), "#f3efe7")
    draw = ImageDraw.Draw(image)
    title = load_font("NanumGothic-Bold.ttf", 52)
    section_title = load_font("NanumGothic-Bold.ttf", 40)
    body = load_font("NanumGothic-Regular.ttf", 28)
    dialogue = load_font("NanumGothic-Regular.ttf", 42)
    thought = load_font("NanumGothic-Regular.ttf", 42)
    caption = load_font("NanumGothic-Regular.ttf", 34)

    draw.text((68, 58), "웹툰 레터링 기준 시트", font=title, fill="#1d1b1a")
    draw.text((70, 124), "v2 확정 · 1080px 발행 / 360px 모바일 판독", font=body, fill="#6d635b")
    draw.text((1010, 128), "시각 승인 완료", anchor="ra", font=body, fill="#9d5c37")

    rounded_panel(draw, (56, 190, 1024, 632))
    draw.text((86, 228), "01  글자 → 여백 → 말풍선", font=section_title, fill="#272320")
    bubble(image, (112, 304, 650, 548), tail=(445, 610))
    centered(draw, (170, 336, 592, 516), "내일 훈련이 끝나면\n갈대밭까지 같이\n갈래?", dialogue, "#1d1b1a")
    dashed_line(draw, (166, 332), (596, 332), "#b49068")
    dashed_line(draw, (166, 520), (596, 520), "#b49068")
    draw.multiline_text((704, 320), "• 가운데 줄이 가장 긴\n  다이아몬드형 줄 구성\n\n• 상하좌우: 글자 2칸 기준\n  균일 여백\n\n• 꼬리는 조판 뒤에\n  말풍선 외곽선과 통합", font=body, fill="#3e3833", spacing=9)

    rounded_panel(draw, (56, 666, 1024, 1028))
    draw.text((86, 704), "02  꼬리: 입을 향해, 짧고 넓게", font=section_title, fill="#272320")
    bubble(image, (108, 786, 542, 960), tail=(720, 922))
    centered(draw, (164, 816, 486, 936), "창고부터요.", dialogue, "#1d1b1a")
    draw.ellipse((704, 884, 752, 932), fill="#d8a17a", outline="#7d5140", width=3)
    draw.arc((688, 864, 768, 944), 20, 340, fill="#7d5140", width=3)
    draw.ellipse((721, 906, 731, 914), fill="#241c1a")
    draw.multiline_text((793, 840), "입/발화원\n\n말풍선과 꼬리는\n하나의 외곽선\n접점 내부 선 없음", font=body, fill="#3e3833", spacing=7)
    draw.multiline_text(
        (116, 968),
        "불합격: 꼬리 교차 · 인물 얼굴/손 침범\n작화 선과의 접선",
        font=load_font("NanumGothic-Regular.ttf", 24),
        fill="#9d5c37",
        spacing=4,
    )

    rounded_panel(draw, (56, 1062, 1024, 1508))
    draw.text((86, 1100), "03  의미별 말풍선", font=section_title, fill="#272320")
    bubble(image, (100, 1190, 470, 1360), tail=(288, 1412))
    centered(draw, (142, 1220, 428, 1330), "대사", dialogue, "#1d1b1a")
    cloud(image, (590, 1180, 952, 1360))
    draw = ImageDraw.Draw(image)
    centered(draw, (644, 1215, 898, 1330), "독백", thought, "#2f2622")
    for x, y, radius in ((775, 1385, 12), (794, 1405, 8), (810, 1422, 5)):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#fffefd", outline="#514a45", width=3)
    draw.rounded_rectangle((100, 1430, 430, 1490), radius=14, fill="#20252d")
    centered(draw, (110, 1433, 420, 1486), "내레이션", caption, "#fffdf6")
    draw.multiline_text(
        (500, 1428),
        "일반 대사는 한 종류의\n서체·굵기·여백을 유지",
        font=load_font("NanumGothic-Regular.ttf", 25),
        fill="#3e3833",
        spacing=5,
    )

    rounded_panel(draw, (56, 1542, 1024, 1990), fill="#e9e2d7")
    draw.text((86, 1580), "04  나눔글꼴: 360px에서 판독", font=section_title, fill="#272320")
    draw.rounded_rectangle((112, 1660, 446, 1812), radius=24, fill="#1f1d1a")
    centered(draw, (128, 1685, 430, 1788), "카일, 사람부터\n데려와라.", dialogue, "#ffffff")
    draw.multiline_text((498, 1655), "하우스 서체\n대사  Nanum Gothic Regular\n독백  Nanum Gothic Regular\n내레이션  Nanum Gothic Regular\n효과음  Nanum Gothic Bold\n\n대사는 360px에서 항상 판독", font=body, fill="#3e3833", spacing=8)
    draw.text((86, 2044), "판독 기준: readable · even clearance · no crossings · art remains visible", font=body, fill="#6d635b")

    image.convert("RGB").save(output, format="PNG")
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
