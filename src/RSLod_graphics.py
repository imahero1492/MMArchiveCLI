"""
RSLod Graphics Module - Bitmap, Sprite, PCX, and Palette Operations
Requires: Pillow (PIL)

Copyright (c) Rozhenko Sergey
Python conversion with graphics support
"""

import struct
import io
import zlib
from typing import Optional, Tuple, List, Callable
from PIL import Image

from .RSLod import *


# Bitmap file header structure
class TMMLodFile:
    """LOD bitmap file header"""
    def __init__(self):
        self.bmp_size: int = 0
        self.data_size: int = 0
        self.bmp_width: int = 0
        self.bmp_height: int = 0
        self.bmp_width_ln2: int = 0
        self.bmp_height_ln2: int = 0
        self.bmp_width_minus1: int = 0
        self.bmp_height_minus1: int = 0
        self.palette: int = 0
        self._unk: int = 0
        self.unp_size: int = 0
        self.bits: int = 0
    
    def pack(self) -> bytes:
        """Pack header to bytes"""
        return struct.pack('<IIhhhhhhhhII',
            self.bmp_size, self.data_size,
            self.bmp_width, self.bmp_height,
            self.bmp_width_ln2, self.bmp_height_ln2,
            self.bmp_width_minus1, self.bmp_height_minus1,
            self.palette, self._unk,
            self.unp_size, self.bits)
    
    @staticmethod
    def unpack(data: bytes) -> 'TMMLodFile':
        """Unpack header from bytes"""
        hdr = TMMLodFile()
        values = struct.unpack('<IIhhhhhhhhII', data[:32])
        hdr.bmp_size = values[0]
        hdr.data_size = values[1]
        hdr.bmp_width = values[2]
        hdr.bmp_height = values[3]
        hdr.bmp_width_ln2 = values[4]
        hdr.bmp_height_ln2 = values[5]
        hdr.bmp_width_minus1 = values[6]
        hdr.bmp_height_minus1 = values[7]
        hdr.palette = values[8]
        hdr._unk = values[9]
        hdr.unp_size = values[10]
        hdr.bits = values[11]
        return hdr


class TSprite:
    """Sprite header"""
    def __init__(self):
        self.size: int = 0
        self.w: int = 0
        self.h: int = 0
        self.palette: int = 0
        self.unk_1: int = 0
        self.yskip: int = 0
        self.unk_2: int = 0
        self.unp_size: int = 0
    
    def pack(self) -> bytes:
        """Pack sprite header"""
        return struct.pack('<IhhhhhhI',
            self.size, self.w, self.h,
            self.palette, self.unk_1,
            self.yskip, self.unk_2,
            self.unp_size)
    
    @staticmethod
    def unpack(data: bytes) -> 'TSprite':
        """Unpack sprite header"""
        hdr = TSprite()
        values = struct.unpack('<IhhhhhhI', data[:20])
        hdr.size = values[0]
        hdr.w = values[1]
        hdr.h = values[2]
        hdr.palette = values[3]
        hdr.unk_1 = values[4]
        hdr.yskip = values[5]
        hdr.unk_2 = values[6]
        hdr.unp_size = values[7]
        return hdr


class TPCXFileHeader:
    """PCX file header"""
    def __init__(self):
        self.image_size: int = 0
        self.width: int = 0
        self.height: int = 0
    
    def pack(self) -> bytes:
        """Pack PCX header"""
        return struct.pack('<III', self.image_size, self.width, self.height)
    
    @staticmethod
    def unpack(data: bytes) -> 'TPCXFileHeader':
        """Unpack PCX header"""
        hdr = TPCXFileHeader()
        values = struct.unpack('<III', data[:12])
        hdr.image_size = values[0]
        hdr.width = values[1]
        hdr.height = values[2]
        return hdr


def rs_mm_palette_to_bitmap(palette_data: bytes) -> Image.Image:
    """Convert 768-byte palette to PIL Image"""
    if len(palette_data) != 768:
        raise ERSLodException(S_RS_LOD_ACT_PAL_MUST_768)
    
    # Create 16x16 palette image
    img = Image.new('RGB', (16, 16))
    pixels = []
    for i in range(0, 768, 3):
        r, g, b = palette_data[i:i+3]
        pixels.append((r, g, b))
    
    img.putdata(pixels)
    return img


def mix_cl(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Mix two colors for mipmap generation"""
    return (
        (c1[0] + c2[0]) // 2,
        (c1[1] + c2[1]) // 2,
        (c1[2] + c2[2]) // 2
    )


def mix_cl_tr(c1: Tuple[int, int, int], c2: Tuple[int, int, int], 
              transparent: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Mix two colors with transparency support"""
    if c1 == transparent:
        return c2
    if c2 == transparent:
        return c1
    return mix_cl(c1, c2)


def fill_bitmap_zooms(img: Image.Image, transparent_color: Optional[Tuple[int, int, int]] = None) -> List[Image.Image]:
    """Generate mipmaps (1/2, 1/4, 1/8 scale)"""
    w, h = img.size
    
    # Check power of 2
    if get_ln2(w) == 0 or get_ln2(h) == 0:
        raise ERSLodBitmapException(S_RS_LOD_MUST_POWER_OF_2 % (w, h))
    
    zooms = []
    current = img
    
    for _ in range(3):
        w, h = current.size
        if w < 2 or h < 2:
            break
        
        new_w, new_h = w // 2, h // 2
        new_img = Image.new(current.mode, (new_w, new_h))
        
        if transparent_color:
            # Mix with transparency
            for y in range(new_h):
                for x in range(new_w):
                    c1 = current.getpixel((x*2, y*2))
                    c2 = current.getpixel((x*2+1, y*2))
                    c3 = current.getpixel((x*2, y*2+1))
                    c4 = current.getpixel((x*2+1, y*2+1))
                    
                    c = mix_cl_tr(mix_cl_tr(c1, c2, transparent_color),
                                  mix_cl_tr(c3, c4, transparent_color),
                                  transparent_color)
                    new_img.putpixel((x, y), c)
        else:
            # Simple resize
            new_img = current.resize((new_w, new_h), Image.BILINEAR)
        
        zooms.append(new_img)
        current = new_img
    
    return zooms


def unpack_bitmap(data: io.BytesIO, size: int) -> Tuple[Image.Image, bytes]:
    """Unpack bitmap from LOD format"""
    # Read header
    hdr_data = data.read(32)
    if len(hdr_data) < 32:
        raise ERSLodException(S_RS_LOD_CORRUPT)
    
    hdr = TMMLodFile.unpack(hdr_data)
    
    # Read compressed data
    compressed_size = hdr.data_size
    compressed_data = data.read(compressed_size)
    
    # Decompress
    if hdr.unp_size > 0:
        pixel_data = zlib.decompress(compressed_data)
    else:
        pixel_data = compressed_data
    
    # Read palette
    palette_data = data.read(768)
    
    # Create image
    img = Image.new('P', (hdr.bmp_width, hdr.bmp_height))
    
    # Set palette
    if len(palette_data) == 768:
        img.putpalette(palette_data)
    
    # Set pixel data
    img.frombytes(pixel_data[:hdr.bmp_width * hdr.bmp_height])
    
    return img, palette_data


def pack_bitmap(img: Image.Image, palette_index: int = 0, bits: int = 0, 
                keep_mipmaps: bool = False) -> bytes:
    """Pack bitmap to LOD format"""
    w, h = img.size
    
    # Convert to palette mode if needed
    if img.mode != 'P':
        img = img.convert('P', palette=Image.ADAPTIVE, colors=256)
    
    # Get pixel data
    pixel_data = img.tobytes()
    
    # Generate mipmaps if needed
    mipmap_data = b''
    if keep_mipmaps and (bits & 2):
        zooms = fill_bitmap_zooms(img)
        for zoom in zooms:
            mipmap_data += zoom.tobytes()
    
    # Compress
    all_data = pixel_data + mipmap_data
    compressed = zlib.compress(all_data, 6)
    
    # Use compressed only if smaller
    if len(compressed) < len(all_data):
        data_to_write = compressed
        unp_size = len(all_data)
    else:
        data_to_write = all_data
        unp_size = 0
    
    # Create header
    hdr = TMMLodFile()
    hdr.bmp_width = w
    hdr.bmp_height = h
    hdr.bmp_width_ln2 = get_ln2(w)
    hdr.bmp_height_ln2 = get_ln2(h)
    hdr.bmp_width_minus1 = w - 1
    hdr.bmp_height_minus1 = h - 1
    hdr.data_size = len(data_to_write)
    hdr.unp_size = unp_size
    hdr.palette = palette_index
    hdr.bits = bits
    hdr.bmp_size = 32 + len(data_to_write) + 768
    
    # Get palette
    palette = img.getpalette()
    if palette:
        palette_bytes = bytes(palette[:768])
    else:
        palette_bytes = bytes(768)
    
    # Pack everything
    result = io.BytesIO()
    result.write(hdr.pack())
    result.write(data_to_write)
    result.write(palette_bytes)
    
    return result.getvalue()


def unpack_sprite(data: io.BytesIO, size: int, palette_data: bytes) -> Image.Image:
    """Unpack sprite from LOD format"""
    # Read sprite header
    hdr_data = data.read(20)
    if len(hdr_data) < 20:
        raise ERSLodException(S_RS_LOD_CORRUPT)
    
    hdr = TSprite.unpack(hdr_data)
    
    # Read line table
    line_count = hdr.h - hdr.yskip
    line_table = []
    for _ in range(line_count):
        line_data = data.read(8)
        if len(line_data) < 8:
            break
        a1, a2, pos = struct.unpack('<hhI', line_data)
        line_table.append((a1, a2, pos))
    
    # Read compressed data
    compressed_data = data.read(hdr.size - 20 - line_count * 8)
    
    # Decompress
    if hdr.unp_size > 0:
        pixel_data = zlib.decompress(compressed_data)
    else:
        pixel_data = compressed_data
    
    # Create image with transparency
    img = Image.new('RGBA', (hdr.w, hdr.h), (0, 0, 0, 0))
    
    # Decode sprite lines
    pixel_stream = io.BytesIO(pixel_data)
    for y, (a1, a2, pos) in enumerate(line_table):
        pixel_stream.seek(pos)
        x = 0
        while x < hdr.w:
            # Read run length
            run = pixel_stream.read(1)
            if not run:
                break
            run_len = run[0]
            
            if run_len & 0x80:
                # Transparent pixels
                x += run_len & 0x7F
            else:
                # Opaque pixels
                for _ in range(run_len):
                    idx = pixel_stream.read(1)
                    if not idx:
                        break
                    # Get color from palette
                    pal_idx = idx[0] * 3
                    if pal_idx + 2 < len(palette_data):
                        r = palette_data[pal_idx]
                        g = palette_data[pal_idx + 1]
                        b = palette_data[pal_idx + 2]
                        img.putpixel((x, y), (r, g, b, 255))
                    x += 1
    
    return img


def pack_sprite(img: Image.Image, palette_index: int) -> bytes:
    """Pack sprite to LOD format"""
    if palette_index < 0:
        raise ERSLodException(S_RS_LOD_SPRITE_MUST_PAL)
    
    w, h = img.size
    
    # Convert to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Encode sprite lines
    lines_data = []
    line_table = []
    
    for y in range(h):
        line_start = len(lines_data)
        x = 0
        
        while x < w:
            # Count transparent pixels
            trans_count = 0
            while x + trans_count < w:
                r, g, b, a = img.getpixel((x + trans_count, y))
                if a > 0:
                    break
                trans_count += 1
            
            if trans_count > 0:
                lines_data.append(0x80 | min(trans_count, 0x7F))
                x += trans_count
            
            # Count opaque pixels
            opaque_start = x
            while x < w:
                r, g, b, a = img.getpixel((x, y))
                if a == 0:
                    break
                x += 1
            
            opaque_count = x - opaque_start
            if opaque_count > 0:
                lines_data.append(opaque_count)
                for i in range(opaque_count):
                    # For now, just use grayscale as palette index
                    r, g, b, a = img.getpixel((opaque_start + i, y))
                    idx = (r + g + b) // 3
                    lines_data.append(idx)
        
        line_table.append((0, 0, line_start))
    
    # Compress line data
    lines_bytes = bytes(lines_data)
    compressed = zlib.compress(lines_bytes, 6)
    
    if len(compressed) < len(lines_bytes):
        data_to_write = compressed
        unp_size = len(lines_bytes)
    else:
        data_to_write = lines_bytes
        unp_size = 0
    
    # Create header
    hdr = TSprite()
    hdr.w = w
    hdr.h = h
    hdr.palette = palette_index
    hdr.yskip = 0
    hdr.unp_size = unp_size
    hdr.size = 20 + len(line_table) * 8 + len(data_to_write)
    
    # Pack everything
    result = io.BytesIO()
    result.write(hdr.pack())
    for a1, a2, pos in line_table:
        result.write(struct.pack('<hhI', a1, a2, pos))
    result.write(data_to_write)
    
    return result.getvalue()


def unpack_pcx(data: io.BytesIO) -> Tuple[Image.Image, Optional[bytes]]:
    """Unpack PCX format"""
    # Read header
    hdr_data = data.read(12)
    if len(hdr_data) < 12:
        raise ERSLodException(S_RS_LOD_CORRUPT)
    
    hdr = TPCXFileHeader.unpack(hdr_data)
    
    # Read image data
    img_data = data.read(hdr.image_size)
    
    # Check if palette exists
    bytes_per_pixel = hdr.image_size // (hdr.width * hdr.height)
    has_palette = bytes_per_pixel == 1
    
    palette_data = None
    if has_palette:
        palette_data = data.read(768)
        img = Image.new('P', (hdr.width, hdr.height))
        if len(palette_data) == 768:
            img.putpalette(palette_data)
        img.frombytes(img_data)
    else:
        # RGB format
        img = Image.frombytes('RGB', (hdr.width, hdr.height), img_data)
    
    return img, palette_data


def pack_pcx(img: Image.Image, keep_bitmap: bool = False) -> bytes:
    """Pack PCX format"""
    w, h = img.size
    
    # Get pixel data
    if img.mode == 'P':
        pixel_data = img.tobytes()
        palette = img.getpalette()
        palette_bytes = bytes(palette[:768]) if palette else bytes(768)
        has_palette = True
    else:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        pixel_data = img.tobytes()
        palette_bytes = b''
        has_palette = False
    
    # Create header
    hdr = TPCXFileHeader()
    hdr.width = w
    hdr.height = h
    hdr.image_size = len(pixel_data)
    
    # Pack
    result = io.BytesIO()
    result.write(hdr.pack())
    result.write(pixel_data)
    if has_palette:
        result.write(palette_bytes)
    
    return result.getvalue()


def pack_lwd(img: Image.Image, transparent_color: Tuple[int, int, int]) -> bytes:
    """Pack LWD transparent bitmap"""
    w, h = img.size
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Encode with transparency
    lines = []
    for y in range(h):
        line = []
        x = 0
        while x < w:
            # Count transparent pixels
            trans_count = 0
            while x + trans_count < w:
                pixel = img.getpixel((x + trans_count, y))
                if pixel != transparent_color:
                    break
                trans_count += 1
            
            if trans_count > 0:
                line.append(struct.pack('<H', trans_count | 0x8000))
                x += trans_count
            
            # Count opaque pixels
            opaque_start = x
            while x < w:
                pixel = img.getpixel((x, y))
                if pixel == transparent_color:
                    break
                x += 1
            
            opaque_count = x - opaque_start
            if opaque_count > 0:
                line.append(struct.pack('<H', opaque_count))
                for i in range(opaque_count):
                    r, g, b = img.getpixel((opaque_start + i, y))
                    # Pack as RGB565
                    rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
                    line.append(struct.pack('<H', rgb565))
        
        lines.append(b''.join(line))
    
    return b''.join(lines)


def unpack_lwd(data: io.BytesIO, width: int, height: int, 
               transparent_color: Tuple[int, int, int]) -> Image.Image:
    """Unpack LWD transparent bitmap"""
    img = Image.new('RGB', (width, height), transparent_color)
    
    for y in range(height):
        x = 0
        while x < width:
            run_data = data.read(2)
            if len(run_data) < 2:
                break
            
            run = struct.unpack('<H', run_data)[0]
            
            if run & 0x8000:
                # Transparent pixels
                x += run & 0x7FFF
            else:
                # Opaque pixels
                for _ in range(run):
                    pixel_data = data.read(2)
                    if len(pixel_data) < 2:
                        break
                    rgb565 = struct.unpack('<H', pixel_data)[0]
                    
                    # Unpack RGB565
                    r = ((rgb565 >> 11) & 0x1F) << 3
                    g = ((rgb565 >> 5) & 0x3F) << 2
                    b = (rgb565 & 0x1F) << 3
                    
                    img.putpixel((x, y), (r, g, b))
                    x += 1
    
    return img


def pack_str(text: str) -> bytes:
    """Pack STR text format"""
    # Simple text packing - just encode as UTF-8 with null terminator
    return text.encode('utf-8') + b'\x00'


def unpack_str(data: io.BytesIO, size: int) -> str:
    """Unpack STR text format"""
    text_data = data.read(size)
    # Remove null terminator and decode
    return text_data.rstrip(b'\x00').decode('utf-8', errors='ignore')


# Export all functions
__all__ = [
    'TMMLodFile',
    'TSprite',
    'TPCXFileHeader',
    'rs_mm_palette_to_bitmap',
    'mix_cl',
    'mix_cl_tr',
    'fill_bitmap_zooms',
    'unpack_bitmap',
    'pack_bitmap',
    'unpack_sprite',
    'pack_sprite',
    'unpack_pcx',
    'pack_pcx',
    'pack_lwd',
    'unpack_lwd',
    'pack_str',
    'unpack_str',
]
