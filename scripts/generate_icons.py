from PIL import Image, ImageDraw
try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS  # Pillow >=9.1
except Exception:
    RESAMPLE_LANCZOS = getattr(Image, 'LANCZOS', 1)  # Fallback
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(BASE_DIR, 'static', 'icons', 'logo-user.png')
OUT_DIR = os.path.join(BASE_DIR, 'static', 'icons')

BRAND_A = (13, 110, 253)   # #0d6efd
BRAND_B = (11, 94, 215)    # #0b5ed7

def linear_gradient(size, c1, c2):
    w, h = size
    overlay = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(overlay)
    for i in range(h):
        t = i / max(h - 1, 1)
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        draw.line([(0, i), (w, i)], fill=(r, g, b, 255))
    return overlay

def make_icon(size, filename, rounded=True, scale=0.7):
    dst = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    bg = linear_gradient((size, size), BRAND_A, BRAND_B)
    if rounded:
        # rounded tile
        tile = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(tile)
        draw.rounded_rectangle([0, 0, size, size], radius=int(size * 0.22), fill=(255, 255, 255, 8))
        dst.alpha_composite(bg)
        dst.alpha_composite(tile)
    else:
        dst.alpha_composite(bg)

    logo = Image.open(SRC_PATH).convert('RGBA')
    # fit logo into scale of canvas
    lw = int(size * scale)
    # keep aspect ratio
    ratio = lw / max(logo.width, logo.height)
    new_size = (int(logo.width * ratio), int(logo.height * ratio))
    logo = logo.resize(new_size, RESAMPLE_LANCZOS)
    x = (size - logo.width) // 2
    y = (size - logo.height) // 2
    dst.alpha_composite(logo, (x, y))
    out_path = os.path.join(OUT_DIR, filename)
    dst.save(out_path, format='PNG')
    print('Wrote', out_path)

def make_ico(filename, size=256, rounded=True, scale=0.72):
    dst = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    bg = linear_gradient((size, size), BRAND_A, BRAND_B)
    if rounded:
        tile = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(tile)
        draw.rounded_rectangle([0, 0, size, size], radius=int(size * 0.22), fill=(255, 255, 255, 8))
        dst.alpha_composite(bg)
        dst.alpha_composite(tile)
    else:
        dst.alpha_composite(bg)

    logo = Image.open(SRC_PATH).convert('RGBA')
    lw = int(size * scale)
    ratio = lw / max(logo.width, logo.height)
    new_size = (int(logo.width * ratio), int(logo.height * ratio))
    logo = logo.resize(new_size, RESAMPLE_LANCZOS)
    x = (size - logo.width) // 2
    y = (size - logo.height) // 2
    dst.alpha_composite(logo, (x, y))
    out_path = os.path.join(OUT_DIR, filename)
    dst.save(out_path, format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    print('Wrote', out_path)

def main():
    if not os.path.exists(SRC_PATH):
        raise FileNotFoundError(f'Source logo not found: {SRC_PATH}')
    os.makedirs(OUT_DIR, exist_ok=True)
    # Standard icons
    make_icon(192, 'icon-192.png', rounded=True, scale=0.72)
    make_icon(512, 'icon-512.png', rounded=True, scale=0.7)
    make_icon(180, 'apple-touch-icon-180-v2.png', rounded=True, scale=0.72)
    make_icon(180, 'apple-touch-icon-180.png', rounded=True, scale=0.72)
    # Maskable (full-bleed, no rounded)
    make_icon(192, 'icon-192-maskable.png', rounded=False, scale=0.72)
    make_icon(512, 'icon-512-maskable.png', rounded=False, scale=0.7)
    # Update v2 files too (for existing references)
    make_icon(192, 'icon-192-v2.png', rounded=True, scale=0.72)
    make_icon(512, 'icon-512-v2.png', rounded=True, scale=0.7)
    make_icon(192, 'icon-192-maskable-v2.png', rounded=False, scale=0.72)
    make_icon(512, 'icon-512-maskable-v2.png', rounded=False, scale=0.7)
    make_ico('favicon.ico', rounded=True, scale=0.72)
    make_ico('multimax.ico', rounded=True, scale=0.72)

if __name__ == '__main__':
    main()
