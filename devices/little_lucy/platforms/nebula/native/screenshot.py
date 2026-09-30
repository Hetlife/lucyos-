"""Capture what is actually on the Nebula panel as a PNG.

LucyOS uses this to learn what the nest is showing and where things are,
without asking the UI layer and without trusting a cached render.

The panel framebuffer (jzfb, /dev/fb0) is 32bpp and stores pixels as BGRX,
not RGBX. Reading it as RGBX yields a channel-swapped image (the red home
field comes out blue), so the byte order is corrected here.

Usage:
    python3 screenshot.py /tmp/shot.png
"""
import sys

FB = '/dev/fb0'
WIDTH = 480
HEIGHT = 272


def read_framebuffer(path=FB, width=WIDTH, height=HEIGHT):
    """Return the framebuffer contents as a Pillow RGB image.

    Pillow 7.0.0 on the Nebula has no 'BGRX' mode, so the buffer is read as
    RGBA and the red and blue channels are swapped to undo the panel's BGRX
    storage order.
    """
    from PIL import Image

    size = width * height * 4
    with open(path, 'rb') as fb:
        fb.seek(0)
        raw = fb.read(size)
    if len(raw) != size:
        raise RuntimeError('short framebuffer read: %d of %d bytes' % (len(raw), size))

    image = Image.frombytes('RGBA', (width, height), raw)
    red, green, blue, alpha = image.split()
    return Image.merge('RGB', (blue, green, red))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/lucy-screenshot.png'
    image = read_framebuffer()
    image.save(out)
    print(out)


if __name__ == '__main__':
    main()
