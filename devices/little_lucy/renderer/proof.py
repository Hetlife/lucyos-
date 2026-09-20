"""Offline 480x272 monochrome proof frame; never accesses a device."""
from pathlib import Path
import argparse

W, H = 480, 272
# Five-row glyphs, scaled for a readable stock-free proof.
FONT = {
    'L': ('10000','10000','10000','10000','11111'),
    'U': ('10001','10001','10001','10001','01110'),
    'C': ('01111','10000','10000','10000','01111'),
    'Y': ('10001','10001','01110','00100','00100'),
    'W': ('10001','10001','10101','10101','01010'),
    'O': ('01110','10001','10001','10001','01110'),
    'R': ('11110','10001','11110','10100','10010'),
    'K': ('10001','10010','11100','10010','10001'),
    'I': ('11111','00100','00100','00100','11111'),
    'N': ('10001','11001','10101','10011','10001'),
    'G': ('01111','10000','10111','10001','01111'),
}


def pixels():
    data = bytearray(W * H)
    def rect(x, y, w, h):
        for row in range(y, y + h):
            if 0 <= row < H:
                lo, hi = max(0, x), min(W, x + w)
                data[row*W+lo:row*W+hi] = b'\xff' * max(0, hi-lo)
    # Simple white Lucy face mark on black.
    rect(93, 57, 8, 110); rect(93, 57, 96, 8); rect(181, 57, 8, 110)
    rect(101, 159, 80, 8)
    rect(119, 99, 12, 12); rect(151, 99, 12, 12)
    rect(132, 133, 28, 5)
    def word(label, x0, y0, scale):
      for letter in label:
        for row, bits in enumerate(FONT[letter]):
            for col, bit in enumerate(bits):
                if bit == '1': rect(x0 + col*scale, y0 + row*scale, scale-2, scale-2)
        x0 += 6*scale
    word('LUCY', 226, 82, 8)
    word('WORKING', 226, 156, 5)
    return data


def encode_xrgb8888(data, order='BGRA'):
    """Pack white/black pixels; channel order remains selectable until measured."""
    if sorted(order) != sorted('BGRA'):
        raise ValueError('order must permute BGRA')
    white = bytes(255 if ch != 'A' else 0 for ch in order)
    black = bytes(0 for _ in order)
    return b''.join(white if p else black for p in data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--format', choices=('ppm', 'raw32'), default='ppm')
    parser.add_argument('--order', default='BGRA')
    args = parser.parse_args()
    p = pixels()
    args.output.write_bytes((f'P6\n{W} {H}\n255\n'.encode() + b''.join(bytes((v,)*3) for v in p)) if args.format == 'ppm' else encode_xrgb8888(p, args.order))

if __name__ == '__main__':
    main()
