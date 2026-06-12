"""Generate an original Store icon for the Bilibili Data MCP Actor.

Original artwork (no Bilibili trademark): a rounded card with a pink gradient,
a white play triangle, and streaming "danmaku" lines that nod to this tool's
danmaku/comment specialty.
"""
from PIL import Image, ImageDraw

S = 512                      # canvas size
R = 112                      # corner radius
TOP = (251, 114, 153)        # bilibili pink  #FB7299
BOT = (255, 138, 187)        # lighter pink    #FF8ABB


def rounded_mask(size: int, radius: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def vgradient(size: int, top, bot) -> Image.Image:
    base = Image.new("RGB", (size, size), top)
    px = base.load()
    for y in range(size):
        t = y / (size - 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b)
    return base


def main() -> None:
    card = vgradient(S, TOP, BOT)
    icon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    icon.paste(card, (0, 0), rounded_mask(S, R))

    d = ImageDraw.Draw(icon)
    cx, cy = S // 2 + 18, S // 2     # play triangle sits slightly right

    # Streaming "danmaku" lines trailing in from the left, like bullet comments
    # flowing toward the play button. Kept clear of the triangle.
    dan = [(60, 150, 150, 150), (60, 196, 96, 95), (60, 250, 170, 200),
           (60, 304, 110, 120), (60, 358, 140, 150)]
    for x, y, w, a in dan:
        d.rounded_rectangle([x, y, x + w, y + 18], radius=9,
                            fill=(255, 255, 255, a))

    # Central play triangle (bold, solid white) — the clear focal point.
    tri = [(cx - 70, cy - 92), (cx - 70, cy + 92), (cx + 96, cy)]
    d.polygon(tri, fill=(255, 255, 255, 255))

    icon.save(r"D:\mcp\bilibili-mcp\apify-actor\icon.png")
    icon.save(r"D:\qsc\bilibili_mcp_icon.png")
    print("icon written: D:\\qsc\\bilibili_mcp_icon.png (512x512)")


if __name__ == "__main__":
    main()
