from PIL import Image, ImageDraw

PRIMARY = (13, 110, 253)
PRIMARY_DARK = (11, 94, 215)
DEEP_BLUE = (13, 71, 161)

def draw_boxes(size, out_path, bg_color=PRIMARY):
    img = Image.new('RGBA', (size, size), bg_color)
    d = ImageDraw.Draw(img)
    box_w = int(size * 0.3125)
    box_h = box_w
    r = int(size * 0.039)
    x1, y1 = int(size * 0.125), int(size * 0.375)
    x2, y2 = int(size * 0.375), int(size * 0.21875)
    x3, y3 = int(size * 0.5625), int(size * 0.4375)
    d.rounded_rectangle([x1, y1, x1 + box_w, y1 + box_h], r, fill=PRIMARY)
    d.rounded_rectangle([x2, y2, x2 + box_w, y2 + box_h], r, fill=PRIMARY_DARK)
    d.rounded_rectangle([x3, y3, x3 + box_w, y3 + box_h], r, fill=DEEP_BLUE)
    img.save(out_path, format='PNG')

def draw_boxes_maskable(size, out_path):
    img = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    box_w = int(size * 0.28)
    box_h = box_w
    r = int(size * 0.036)
    pad = int(size * 0.1)
    x1, y1 = pad, pad + int(size * 0.22)
    x2, y2 = pad + int(size * 0.24), pad + int(size * 0.05)
    x3, y3 = pad + int(size * 0.43), pad + int(size * 0.27)
    d.rounded_rectangle([x1, y1, x1 + box_w, y1 + box_h], r, fill=PRIMARY)
    d.rounded_rectangle([x2, y2, x2 + box_w, y2 + box_h], r, fill=PRIMARY_DARK)
    d.rounded_rectangle([x3, y3, x3 + box_w, y3 + box_h], r, fill=DEEP_BLUE)
    img.save(out_path, format='PNG')

def main():
    draw_boxes(180, 'static/icons/apple-touch-icon-180-v2.png')
    draw_boxes(192, 'static/icons/icon-192-v2.png')
    draw_boxes(512, 'static/icons/icon-512-v2.png')
    draw_boxes_maskable(192, 'static/icons/icon-192-maskable-v2.png')
    draw_boxes_maskable(512, 'static/icons/icon-512-maskable-v2.png')

if __name__ == '__main__':
    main()
