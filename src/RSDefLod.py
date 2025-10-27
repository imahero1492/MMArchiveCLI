"""
RSDefLod - Palette and Bitmap Utilities
Direct Python conversion from RSDefLod.pas

Copyright (c) Rozhenko Sergey
http://sites.google.com/site/sergroj/
sergroj@mail.ru
"""

from typing import Tuple, Optional
from PIL import Image


class THeroesPalEntry:
    """Heroes palette entry (RGB triplet)"""
    def __init__(self, red: int = 0, green: int = 0, blue: int = 0):
        self.red = red
        self.green = green
        self.blue = blue


def rs_make_palette(heroes_pal: bytes) -> bytes:
    """Create PIL palette from Heroes palette data (768 bytes)"""
    if len(heroes_pal) != 768:
        raise ValueError("Heroes palette must be 768 bytes")
    
    # Return as bytes for PIL Image.putpalette()
    return heroes_pal


def rs_make_log_palette(heroes_pal: bytes) -> list:
    """Create log palette from Heroes palette data"""
    if len(heroes_pal) != 768:
        raise ValueError("Heroes palette must be 768 bytes")
    
    log_palette = []
    for i in range(0, 768, 3):
        entry = {
            'peRed': heroes_pal[i],
            'peGreen': heroes_pal[i+1],
            'peBlue': heroes_pal[i+2],
            'peFlags': 0
        }
        log_palette.append(entry)
    
    return log_palette


def rs_write_palette(heroes_pal: bytearray, pal: list):
    """Write palette list to Heroes palette format"""
    if len(heroes_pal) != 768:
        raise ValueError("Heroes palette must be 768 bytes")
    
    if len(pal) != 256:
        raise ValueError("Palette must have 256 entries")
    
    for i in range(256):
        heroes_pal[i*3] = pal[i]['peRed']
        heroes_pal[i*3+1] = pal[i]['peGreen']
        heroes_pal[i*3+2] = pal[i]['peBlue']


def rs_get_non_zero_color_rect(b: Image.Image) -> Tuple[int, int, int, int]:
    """Get frame outside which there are only 0 pixels (for 8-bit images)"""
    w, h = b.size
    
    if w == 0 or h == 0:
        return (0, 0, 0, 0)
    
    if b.mode != 'P':
        return (0, 0, w, h)
    
    # Get pixel data
    pixels = b.load()
    
    left = w
    top = h
    right = -1
    bottom = -1
    
    for j in range(h):
        for i in range(w):
            if pixels[i, j] != 0:
                if left > i:
                    left = i
                if top > j:
                    top = j
                if right < i:
                    right = i
                if bottom < j:
                    bottom = j
    
    right += 1
    bottom += 1
    
    if right == 0:
        left = 0
        top = 0
    
    return (left, top, right, bottom)


__all__ = [
    'THeroesPalEntry',
    'rs_make_palette',
    'rs_make_log_palette',
    'rs_write_palette',
    'rs_get_non_zero_color_rect',
]
