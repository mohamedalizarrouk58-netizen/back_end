#!/usr/bin/env python3
"""Extract PlantUML blocks from diagrammes_use_case_raffines.md and render PNGs via Kroki.

Usage: python tools/render_plantuml.py
"""
import os
import re
import sys
import urllib.request
import zlib

ROOT = os.path.dirname(os.path.dirname(__file__))
MD_PATH = os.path.join(ROOT, 'diagrammes_use_case_raffines.md')
OUT_DIR = os.path.join(ROOT, 'diagrammes_images')


def slugify(value: str) -> str:
    return re.sub(r'[^0-9a-zA-Z_-]+', '_', value).strip('_')[:60]


def _encode_plantuml(data: bytes) -> str:
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(data) + compressor.flush()

    def encode6bit(b):
        if b < 10:
            return chr(48 + b)
        b -= 10
        if b < 26:
            return chr(65 + b)
        b -= 26
        if b < 26:
            return chr(97 + b)
        b -= 26
        if b == 0:
            return '-'
        if b == 1:
            return '_'
        return '?'

    def append3bytes(b1, b2, b3):
        c1 = b1 >> 2
        c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
        c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        return encode6bit(c1) + encode6bit(c2) + encode6bit(c3) + encode6bit(c4)

    res = []
    i = 0
    while i < len(compressed):
        b1 = compressed[i]
        b2 = compressed[i + 1] if i + 1 < len(compressed) else 0
        b3 = compressed[i + 2] if i + 2 < len(compressed) else 0
        res.append(append3bytes(b1, b2, b3))
        i += 3
    return ''.join(res)


def main() -> int:
    if not os.path.exists(MD_PATH):
        print('ERROR: markdown file not found:', MD_PATH)
        return 2

    os.makedirs(OUT_DIR, exist_ok=True)
    text = open(MD_PATH, encoding='utf-8').read()

    blocks = list(re.finditer(r'@startuml.*?@enduml', text, re.S | re.M))
    if not blocks:
        print('No PlantUML blocks found in', MD_PATH)
        return 0

    for idx, match in enumerate(blocks, start=1):
        block = match.group(0)
        before = text[:match.start()]
        h = re.search(r'##\s*(.+)$', before, re.M)
        name = h.group(1).strip() if h else f'diagram_{idx}'
        slug = slugify(name)
        filename = f'{idx:02d}_{slug}.png'
        outpath = os.path.join(OUT_DIR, filename)

        print(f'Rendering [{name}] -> {outpath} ...')
        done = False
        try:
            req = urllib.request.Request(
                'https://kroki.io/plantuml/png',
                data=block.encode('utf-8'),
                headers={'Content-Type': 'text/plain', 'User-Agent': 'Mozilla/5.0'},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                img = resp.read()
            with open(outpath, 'wb') as f:
                f.write(img)
            print('WROTE', outpath)
            done = True
        except Exception as exc:
            print('Kroki failed:', exc)

        if not done:
            try:
                encoded = _encode_plantuml(block.encode('utf-8'))
                url = 'https://www.plantuml.com/plantuml/png/' + encoded
                print('Trying plantuml.com URL:', url)
                with urllib.request.urlopen(
                    urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}),
                    timeout=30,
                ) as resp:
                    img = resp.read()
                with open(outpath, 'wb') as f:
                    f.write(img)
                print('WROTE', outpath)
            except Exception as exc:
                print('PlantUML server fallback failed:', exc)

    print('\nDone. Images saved to', OUT_DIR)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
