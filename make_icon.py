#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 RenameTime 程序图标 app_icon.ico（16/32/48 三尺寸，BMP-in-ICO 格式，无需 PIL）。
图标图案：一张日历，顶部蓝色横带 + 装订环，中间白色日期区写着 "10"。
"""
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))

# 3x5 像素字体（只用到的数字）
FONT = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
}

BAND = (0x2E, 0x7D, 0xD1, 0xFF)      # 日历头 蓝
RING = (0x44, 0x4A, 0x55, 0xFF)      # 装订环 深灰
BODY = (0xFF, 0xFF, 0xFF, 0xFF)      # 日期区 白
EDGE = (0x8A, 0x90, 0x99, 0xFF)      # 边框 灰
DIGIT = (0x33, 0x38, 0x3F, 0xFF)     # 数字 深灰


def draw(size):
    """返回 size x size 的 RGBA 像素矩阵（行为 y，列为 x）。"""
    px = [[(0, 0, 0, 0) for _ in range(size)] for _ in range(size)]

    def rect(x0, y0, w, h, color):
        for y in range(max(0, y0), min(size, y0 + h)):
            for x in range(max(0, x0), min(size, x0 + w)):
                px[y][x] = color

    # 日历主体（带 1px 边框）
    m = max(1, size // 16)            # 边距
    rect(m, m, size - 2 * m, size - 2 * m, EDGE)
    rect(m + 1, m + 1, size - 2 * m - 2, size - 2 * m - 2, BODY)

    # 顶部横带
    band_h = max(2, size // 6)
    rect(m + 1, m + 1, size - 2 * m - 2, band_h, BAND)

    # 两个装订环
    ring_w = max(1, size // 16)
    ring_h = max(2, size // 10)
    ry = m - ring_h // 2
    rect(size // 2 - ring_w * 2 - 1, ry, ring_w, ring_h, RING)
    rect(size // 2 + ring_w + 1, ry, ring_w, ring_h, RING)

    # 日期区写 "10"（像素字体，2 倍缩放）
    scale = max(1, size // 16)
    dw, dh = 3 * scale, 5 * scale
    gap = scale
    text_w = dw * 2 + gap
    x0 = (size - text_w) // 2
    y0 = m + band_h + max(1, size // 12)
    for di, ch in enumerate("10"):
        bits = FONT[ch]
        for r, row in enumerate(bits):
            for c, v in enumerate(row):
                if v == "1":
                    rect(x0 + di * (dw + gap) + c * scale,
                         y0 + r * scale, scale, scale, DIGIT)
    return px


def to_bmp_dib(px, size):
    """RGBA 矩阵 -> 32bpp BGRA DIB（自底向上，行 padded 到 4 字节）。"""
    row_bytes = size * 4
    data = bytearray()
    for y in range(size - 1, -1, -1):
        row = bytearray()
        for x in range(size):
            r, g, b, a = px[y][x]
            row += bytes((b, g, r, a))
        while len(row) % 4:
            row += b"\x00"
        data += row
    and_row = ((size + 31) // 32) * 4
    and_mask = b"\x00" * (and_row * size)      # 32bpp 用 alpha，AND 掩码全 0
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32,
                         0, len(data) + len(and_mask), 0, 0, 0, 0)
    return bytes(header) + bytes(data) + and_mask


def main():
    sizes = (16, 32, 48)
    images = []
    for s in sizes:
        dib = to_bmp_dib(draw(s), s)
        images.append((s, dib))

    out = os.path.join(HERE, "app_icon.ico")
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    blob = b""
    for s, dib in images:
        entries += struct.pack("<BBBBHHII", s, s, 0, 0, 1, 32, len(dib), offset)
        blob += dib
        offset += len(dib)
    with open(out, "wb") as f:
        f.write(header + entries + blob)
    print("已生成 %s（%d 字节，尺寸 %s）" % (out, os.path.getsize(out), "/".join(map(str, sizes))))


if __name__ == "__main__":
    main()
