"""앱 아이콘(저울) 생성 스크립트.

    .venv\\Scripts\\python tools/make_icon.py

assets/icon.png (파비콘·앱 내 사용)과 assets/icon.ico (Windows 바로가기용)를
만든다. 색을 바꾸려면 아래 NAVY / PAPER 값만 고치면 된다.
"""

from pathlib import Path

from PIL import Image, ImageDraw

NAVY = "#1B3A6B"   # .streamlit/config.toml 의 primaryColor 와 맞춤
PAPER = "#FBFAF7"

S = 1024          # 최종 크기
SS = 4            # 안티에일리어싱용 배율 (4배로 그린 뒤 축소)
OUT = Path("assets")


def draw_icon() -> Image.Image:
    n = S * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def px(v: float) -> int:
        """1024 기준 좌표를 실제 캔버스 좌표로."""
        return int(v * SS)

    def bar(x0, y0, x1, y1, r):
        d.rounded_rectangle([px(x0), px(y0), px(x1), px(y1)], radius=px(r), fill=PAPER)

    # 배경: 둥근 사각형
    d.rounded_rectangle([0, 0, n, n], radius=px(190), fill=NAVY)

    # 기둥과 받침
    bar(490, 250, 534, 812, 22)          # 세로 기둥
    bar(360, 812, 664, 856, 22)          # 받침대
    d.ellipse([px(482), px(214), px(542), px(274)], fill=PAPER)  # 상단 꼭지

    # 저울대
    bar(214, 300, 810, 340, 20)

    # 양쪽 접시와 매다는 줄
    for cx in (262, 762):
        bar(cx - 7, 340, cx + 7, 452, 7)                         # 줄
        d.chord([px(cx - 138), px(452 - 62), px(cx + 138), px(452 + 62)],
                start=0, end=180, fill=PAPER)                    # 접시(반원)

    return img.resize((S, S), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    icon = draw_icon()

    icon.save(OUT / "icon.png")
    # 바로가기·탭에서 쓰이는 여러 해상도를 한 파일에 담는다
    icon.save(OUT / "icon.ico",
              sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    print(f"wrote {OUT / 'icon.png'} ({icon.size[0]}x{icon.size[1]})")
    print(f"wrote {OUT / 'icon.ico'}")


if __name__ == "__main__":
    main()
