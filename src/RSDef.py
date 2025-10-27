"""
RSDef - DEF Sprite File Handler for Heroes games
Direct Python conversion from RSDef.pas

Copyright (c) Rozhenko Sergey
http://sites.google.com/site/sergroj/
sergroj@mail.ru
"""

import struct
import io
from typing import Optional, Callable, List, BinaryIO
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


# Exceptions
class ERSDefException(Exception):
    pass


# Constants
RSFullBmp = object()  # Special constant like TBitmap(1) in Pascal

# Resource strings
S_RS_INVALID_DEF = 'Def file is invalid'


# Data structures
@dataclass
class TRSDefHeader:
    TypeOfDef: int
    Width: int
    Height: int
    GroupsCount: int
    Palette: bytes  # 768 bytes


@dataclass
class TRSDefGroup:
    GroupNum: int
    ItemsCount: int
    Unk2: int
    Unk3: int


@dataclass
class TRSDefPic:
    FileSize: int
    Compression: int
    Width: int
    Height: int
    FrameWidth: int
    FrameHeight: int
    FrameLeft: int
    FrameTop: int


@dataclass
class TMsk:
    Width: int
    Height: int
    MaskObject: bytes  # 6 bytes
    MaskShadow: bytes  # 6 bytes


# Helper functions
def make_log_palette(palette_data: bytes) -> List[tuple]:
    """Convert 768-byte palette to list of RGB tuples"""
    if len(palette_data) != 768:
        raise ValueError("Palette must be 768 bytes")
    
    palette = []
    for i in range(256):
        r = palette_data[i * 3]
        g = palette_data[i * 3 + 1]
        b = palette_data[i * 3 + 2]
        palette.append((r, g, b))
    return palette


def swap_color(color: int) -> int:
    """Swap color bytes (BGR to RGB)"""
    return ((color & 0xFF) << 16) | (color & 0xFF00) | ((color >> 16) & 0xFF)


class TRSDefWrapper:
    """DEF file wrapper for reading and extracting sprites"""
    
    def __init__(self, data: bytes):
        self.data = data
        self.use_custom_palette = True
        self._pic_links: Optional[List[int]] = None
        self._pic_name_links: Optional[List[bytes]] = None
        self._pictures_count = 0
        self._pal: Optional[List[tuple]] = None
        self._pure_pal: Optional[List[tuple]] = None
        self.on_prepare_palette: Optional[Callable] = None
        
        self._parse_header()
    
    def _parse_header(self):
        """Parse DEF file header and structure"""
        if len(self.data) < 12:
            raise ERSDefException(S_RS_INVALID_DEF)
        
        # Read main header
        type_of_def, width, height, groups_count = struct.unpack('<IIII', self.data[0:16])
        palette = self.data[16:784]
        
        self.header = TRSDefHeader(type_of_def, width, height, groups_count, palette)
        
        # Parse groups
        self.groups: List[TRSDefGroup] = []
        self.item_names: List[List[bytes]] = []
        self.item_pointers: List[List[int]] = []
        
        offset = 784
        
        for _ in range(groups_count):
            if offset + 16 > len(self.data):
                raise ERSDefException(S_RS_INVALID_DEF)
            
            group_num, items_count, unk2, unk3 = struct.unpack('<IIII', self.data[offset:offset+16])
            group = TRSDefGroup(group_num, items_count, unk2, unk3)
            self.groups.append(group)
            offset += 16
            
            # Read item names
            names = []
            for _ in range(items_count):
                if offset + 13 > len(self.data):
                    raise ERSDefException(S_RS_INVALID_DEF)
                name = self.data[offset:offset+13]
                names.append(name)
                offset += 13
            self.item_names.append(names)
            
            # Read item pointers
            pointers = []
            for _ in range(items_count):
                if offset + 4 > len(self.data):
                    raise ERSDefException(S_RS_INVALID_DEF)
                ptr = struct.unpack('<I', self.data[offset:offset+4])[0]
                pointers.append(ptr)
                offset += 4
            self.item_pointers.append(pointers)
            
            self._pictures_count += items_count
    
    def _pic_links_needed(self):
        """Build flat list of picture offsets"""
        if self._pic_links is None:
            self._pic_links = []
            for group_idx, group in enumerate(self.groups):
                for item_idx in range(group.ItemsCount):
                    self._pic_links.append(self.item_pointers[group_idx][item_idx])
    
    def _pic_name_links_needed(self):
        """Build flat list of picture names"""
        if self._pic_name_links is None:
            self._pic_name_links = []
            for group_idx, group in enumerate(self.groups):
                for item_idx in range(group.ItemsCount):
                    self._pic_name_links.append(self.item_names[group_idx][item_idx])
    
    def get_pic_header(self, *args) -> TRSDefPic:
        """Get picture header by index or (group, index)"""
        if len(args) == 1:
            pic_num = args[0]
            self._pic_links_needed()
            offset = self._pic_links[pic_num]
        else:
            group, pic_num = args
            offset = self.item_pointers[group][pic_num]
        
        if offset + 32 > len(self.data):
            raise ERSDefException(S_RS_INVALID_DEF)
        
        values = struct.unpack('<8I', self.data[offset:offset+32])
        return TRSDefPic(*values)
    
    def get_pic_name(self, *args) -> str:
        """Get picture name by index or (group, index)"""
        if len(args) == 1:
            pic_num = args[0]
            self._pic_name_links_needed()
            name_bytes = self._pic_name_links[pic_num]
        else:
            group, pic_num = args
            name_bytes = self.item_names[group][pic_num]
        
        return name_bytes.rstrip(b'\x00').decode('ascii', errors='ignore')
    
    def rebuild_pal(self):
        """Rebuild palette from header"""
        self._pal = make_log_palette(self.header.Palette)
        if self.on_prepare_palette:
            self.on_prepare_palette(self, self._pal)
    
    def _do_extract_buffer(self, offset: int, both_buffers: bool = False) -> tuple:
        """Extract picture buffer from DEF data (DoExtractBuffer)"""
        # Get header
        if offset < self._pictures_count:
            self._pic_links_needed()
            block_offset = self._pic_links[offset]
        else:
            block_offset = offset
        
        values = struct.unpack('<8I', self.data[block_offset:block_offset+32])
        pic_hdr = TRSDefPic(*values)
        block = block_offset + 32
        
        x = pic_hdr.Width
        y = pic_hdr.Height
        
        # Handle old format DEFs
        if pic_hdr.FrameWidth > x and pic_hdr.FrameHeight > y and pic_hdr.Compression == 1:
            pic_hdr.FrameLeft = 0
            pic_hdr.FrameTop = 0
            pic_hdr.FrameWidth = x
            pic_hdr.FrameHeight = y
            block -= 16
        else:
            x = pic_hdr.FrameWidth
            y = pic_hdr.FrameHeight
        
        if pic_hdr.Compression == 0:
            pic = self.data[block:block + x * y]
            return pic_hdr, pic, None, None
        
        # Allocate buffers
        buf = bytearray(x * y)
        if both_buffers:
            sh_buf = bytearray(x * y)
            for i in range(len(buf)):
                buf[i] = 0
            for i in range(len(sh_buf)):
                sh_buf[i] = 255
        else:
            sh_buf = buf
        
        # Decompress
        if pic_hdr.Compression == 1:
            for j in range(y):
                line_offset = struct.unpack('<I', self.data[block + j * 4:block + j * 4 + 4])[0]
                p = block + line_offset
                i = 0
                while i < x:
                    if p >= len(self.data) - 1:
                        break
                    code = self.data[p]
                    p += 1
                    value = self.data[p]
                    p += 1
                    length = value + 1
                    
                    if code == 255:
                        for k in range(min(length, x - i)):
                            if p + k < len(self.data):
                                buf[j * x + i + k] = self.data[p + k]
                        p += length
                    else:
                        for k in range(min(length, x - i)):
                            sh_buf[j * x + i + k] = code
                    i += length
                    if i < 0:
                        break
        
        elif pic_hdr.Compression in [2, 3]:
            if pic_hdr.Compression == 3:
                y = y * (x // 32)
                x = 32
            
            for j in range(y):
                line_offset = struct.unpack('<H', self.data[block + j * 2:block + j * 2 + 2])[0]
                p = block + line_offset
                i = 0
                while i < x:
                    if p >= len(self.data):
                        break
                    value = self.data[p]
                    p += 1
                    code = value // 32
                    length = (value & 31) + 1
                    
                    if code == 7:
                        for k in range(min(length, x - i)):
                            if p + k < len(self.data):
                                buf[j * x + i + k] = self.data[p + k]
                        p += length
                    else:
                        for k in range(min(length, x - i)):
                            sh_buf[j * x + i + k] = code
                            if code == 5 and both_buffers:
                                buf[j * x + i + k] = code
                    i += length
                    if i < 0:
                        break
        
        pic = self.data[block:block + 1] if buf is None else bytes(buf)
        return pic_hdr, pic, bytes(buf) if buf else None, bytes(sh_buf) if sh_buf != buf else None
    
    def _extract_buffer(self, offset: int) -> tuple:
        """Extract picture buffer from DEF data"""
        pic_hdr = self.get_pic_header(offset) if isinstance(offset, int) and offset < self._pictures_count else None
        
        if pic_hdr is None:
            # Parse from raw offset
            values = struct.unpack('<8I', self.data[offset:offset+32])
            pic_hdr = TRSDefPic(*values)
            block_offset = offset + 32
        else:
            self._pic_links_needed()
            block_offset = self._pic_links[offset] + 32
        
        x = pic_hdr.FrameWidth
        y = pic_hdr.FrameHeight
        
        # Handle old format DEFs
        if pic_hdr.FrameWidth > pic_hdr.Width and pic_hdr.FrameHeight > pic_hdr.Height and pic_hdr.Compression == 1:
            pic_hdr.FrameLeft = 0
            pic_hdr.FrameTop = 0
            pic_hdr.FrameWidth = pic_hdr.Width
            pic_hdr.FrameHeight = pic_hdr.Height
            x = pic_hdr.Width
            y = pic_hdr.Height
            block_offset -= 16
        
        if pic_hdr.Compression == 0:
            # No compression
            pic_data = self.data[block_offset:block_offset + x * y]
            return pic_hdr, pic_data, None
        
        # Decompress
        buf = bytearray(x * y)
        sh_buf = bytearray(x * y)
        
        for i in range(len(sh_buf)):
            sh_buf[i] = 255
        
        if pic_hdr.Compression == 1:
            # Type 1 compression
            offsets_size = y * 4
            for j in range(y):
                line_offset = struct.unpack('<I', self.data[block_offset + j * 4:block_offset + j * 4 + 4])[0]
                p = block_offset + line_offset
                i = 0
                
                while i < x:
                    if p >= len(self.data) - 1:
                        break
                    code = self.data[p]
                    p += 1
                    value = self.data[p]
                    p += 1
                    length = value + 1
                    
                    if code == 255:
                        # Copy pixels
                        for k in range(min(length, x - i)):
                            if p + k < len(self.data):
                                buf[j * x + i + k] = self.data[p + k]
                        p += length
                    else:
                        # Fill shadow
                        for k in range(min(length, x - i)):
                            sh_buf[j * x + i + k] = code
                    
                    i += length
        
        elif pic_hdr.Compression in [2, 3]:
            # Type 2/3 compression
            if pic_hdr.Compression == 3:
                y = y * (x // 32)
                x = 32
            
            for j in range(y):
                line_offset = struct.unpack('<H', self.data[block_offset + j * 2:block_offset + j * 2 + 2])[0]
                p = block_offset + line_offset
                i = 0
                
                while i < x:
                    if p >= len(self.data):
                        break
                    value = self.data[p]
                    p += 1
                    code = value // 32
                    length = (value & 31) + 1
                    
                    if code == 7:
                        # Copy pixels
                        for k in range(min(length, x - i)):
                            if p + k < len(self.data):
                                buf[j * x + i + k] = self.data[p + k]
                        p += length
                    else:
                        # Fill shadow
                        for k in range(min(length, x - i)):
                            sh_buf[j * x + i + k] = code
                            if code == 5:  # Flag color
                                buf[j * x + i + k] = code
                    
                    i += length
        
        return pic_hdr, bytes(buf), bytes(sh_buf)
    
    def _do_extract_bmp(self, offset: int, bmp, bmp_spec):
        """Extract bitmap (DoExtractBmp)"""
        if Image is None:
            raise ImportError("PIL/Pillow required")
        
        pic_hdr, pic, buf, sh_buf = self._do_extract_buffer(offset, bmp_spec is not None)
        
        if bmp is not None:
            # Init bitmap
            bmp = Image.new('P', (0, 0))
            
            # Set palette
            if bmp_spec is None:
                if self._pal is None:
                    self.rebuild_pal()
                pal_data = [c for rgb in self._pal for c in rgb]
            else:
                if self._pure_pal is None:
                    self._pure_pal = make_log_palette(self.header.Palette)
                pal_data = [c for rgb in self._pure_pal for c in rgb]
            
            # Create bitmap
            bmp = Image.new('P', (pic_hdr.Width, pic_hdr.Height), 0)
            bmp.putpalette(pal_data)
            
            # Paste frame
            if buf:
                frame = Image.frombytes('P', (pic_hdr.FrameWidth, pic_hdr.FrameHeight), buf)
                frame.putpalette(pal_data)
                bmp.paste(frame, (pic_hdr.FrameLeft, pic_hdr.FrameTop))
        
        if bmp_spec is not None:
            if self._pure_pal is None:
                self._pure_pal = make_log_palette(self.header.Palette)
            pal_data = [c for rgb in self._pure_pal for c in rgb]
            
            bmp_spec = Image.new('P', (pic_hdr.Width, pic_hdr.Height), 0)
            bmp_spec.putpalette(pal_data)
            
            if sh_buf is None:
                sh_buf = bytes([255] * (pic_hdr.FrameWidth * pic_hdr.FrameHeight))
            
            if sh_buf:
                frame = Image.frombytes('P', (pic_hdr.FrameWidth, pic_hdr.FrameHeight), sh_buf)
                frame.putpalette(pal_data)
                bmp_spec.paste(frame, (pic_hdr.FrameLeft, pic_hdr.FrameTop))
        
        return bmp, bmp_spec
    
    def _make_full_bmp(self, bmp, bmp_spec):
        """Merge main and shadow bitmaps into 32-bit RGBA (MakeFullBmp)"""
        if Image is None:
            raise ImportError("PIL/Pillow required")
        
        w, h = bmp.size
        result = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        
        if h == 0:
            return result
        
        if self._pure_pal is None:
            self._pure_pal = make_log_palette(self.header.Palette)
        if self._pal is None:
            self.rebuild_pal()
        
        # Convert palettes to lookup arrays
        pal1 = [swap_color((r << 16) | (g << 8) | b) for r, g, b in self._pure_pal]
        pal2 = [swap_color((r << 16) | (g << 8) | b) for r, g, b in self._pal]
        
        # Get pixel data
        pixels1 = bmp.load()
        pixels2 = bmp_spec.load()
        result_pixels = result.load()
        
        for y in range(h):
            for x in range(w):
                p1 = pixels1[x, y] if isinstance(pixels1[x, y], int) else pixels1[x, y][0]
                p2 = pixels2[x, y] if isinstance(pixels2[x, y], int) else pixels2[x, y][0]
                
                if p2 == 255:
                    color = pal1[p1]
                else:
                    color = pal2[p2]
                
                # Convert back to RGB
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                result_pixels[x, y] = (r, g, b, 255)
        
        return result
    
    def extract_bmp(self, *args, bitmap=None, bmp_spec=None):
        """Extract bitmap by index or (group, index)
        
        Special values:
        - bitmap=None: Create new bitmap
        - bmp_spec=None: No shadow extraction
        - bmp_spec=RSFullBmp: Create 32-bit RGBA with shadow merged
        """
        if Image is None:
            raise ImportError("PIL/Pillow is required for bitmap extraction")
        
        # Handle special RSFullBmp constant (like Pascal's TBitmap(1))
        if bitmap is RSFullBmp:
            bitmap = bmp_spec
            bmp_spec = RSFullBmp
            if bitmap is RSFullBmp:
                bitmap = None
        
        if len(args) == 1:
            pic_num = args[0]
            self._pic_links_needed()
            offset = self._pic_links[pic_num]
        else:
            group, pic_num = args
            offset = self.item_pointers[group][pic_num]
        
        pic_hdr, buf, sh_buf = self._extract_buffer(offset)
        
        # Create palette
        if self._pal is None:
            self.rebuild_pal()
        
        if self._pure_pal is None:
            self._pure_pal = make_log_palette(self.header.Palette)
        
        # Handle RSFullBmp mode - merge main and shadow into 32-bit RGBA
        if bmp_spec is RSFullBmp:
            # Create temporary bitmaps
            b1 = Image.new('P', (pic_hdr.Width, pic_hdr.Height), 0)
            b2 = Image.new('P', (pic_hdr.Width, pic_hdr.Height), 0)
            
            if self._pure_pal is None:
                self._pure_pal = make_log_palette(self.header.Palette)
            
            pal_data = [c for rgb in self._pure_pal for c in rgb]
            b1.putpalette(pal_data)
            b2.putpalette(pal_data)
            
            # Paste frames
            if buf:
                frame_img = Image.frombytes('P', (pic_hdr.FrameWidth, pic_hdr.FrameHeight), buf)
                frame_img.putpalette(pal_data)
                b1.paste(frame_img, (pic_hdr.FrameLeft, pic_hdr.FrameTop))
            
            if sh_buf:
                frame_spec = Image.frombytes('P', (pic_hdr.FrameWidth, pic_hdr.FrameHeight), sh_buf)
                frame_spec.putpalette(pal_data)
                b2.paste(frame_spec, (pic_hdr.FrameLeft, pic_hdr.FrameTop))
            
            return self._make_full_bmp(b1, b2)
        
        # Create main image
        img = Image.new('P', (pic_hdr.Width, pic_hdr.Height), 0)
        img.putpalette([c for rgb in (self._pal if self.use_custom_palette else self._pure_pal) for c in rgb])
        
        # Paste frame
        if buf:
            frame_img = Image.frombytes('P', (pic_hdr.FrameWidth, pic_hdr.FrameHeight), buf)
            frame_img.putpalette(img.getpalette())
            img.paste(frame_img, (pic_hdr.FrameLeft, pic_hdr.FrameTop))
        
        # Create shadow image if requested
        img_spec = None
        if bmp_spec is not None and bmp_spec is not RSFullBmp and sh_buf:
            img_spec = Image.new('P', (pic_hdr.Width, pic_hdr.Height), 0)
            img_spec.putpalette([c for rgb in self._pure_pal for c in rgb])
            
            frame_spec = Image.frombytes('P', (pic_hdr.FrameWidth, pic_hdr.FrameHeight), sh_buf)
            frame_spec.putpalette(img_spec.getpalette())
            img_spec.paste(frame_spec, (pic_hdr.FrameLeft, pic_hdr.FrameTop))
        
        return img if bmp_spec is None else (img, img_spec)
    
    def extract_def_tool_list(self, filename: str, external_shadow: bool = False, in_24_bits: bool = False) -> str:
        """Extract all pictures and create DefTool list file"""
        dir_path = Path(filename).parent
        shadow_dir = ''
        
        if external_shadow and self.header.TypeOfDef not in [0x40, 0x45, 0x46, 0x47]:
            shadow_dir = 'Shadow\\'
            i = 0
            while (dir_path / shadow_dir).exists():
                shadow_dir = f'Shadow_{i}\\'
                i += 1
            (dir_path / shadow_dir).mkdir(parents=True, exist_ok=True)
        
        # Build INI content manually for exact format match
        ini_lines = ['[Data]']
        
        ini_lines.append(f'Type={self.header.TypeOfDef - 0x40}')
        ini_lines.append(f'Shadow Type={2 if shadow_dir else 0}')
        
        # Write groups
        max_group = 0
        for group_idx, group in enumerate(self.groups):
            max_group = max(max_group, group.GroupNum)
            files = '|'.join([self.get_pic_name(group_idx, i) + '.bmp' for i in range(group.ItemsCount)]) + '|'
            ini_lines.append(f'Group{group.GroupNum}={files}')
            
            if shadow_dir:
                shadow_files = '|'.join([shadow_dir + self.get_pic_name(group_idx, i) + '.bmp' for i in range(group.ItemsCount)]) + '|'
                ini_lines.append(f'Shadow{group.GroupNum}={shadow_files}')
        
        ini_lines.append(f'Groups Number={max_group + 1}')
        ini_lines.append('Generate Selection=false')
        
        # Color boxes configuration
        if self._pure_pal is None:
            self._pure_pal = make_log_palette(self.header.Palette)
        
        colors_str = '|'.join([f'${r:02X}{g:02X}{b:02X}' for r, g, b in self._pure_pal[0:8]]) + '|'
        ini_lines.append(f'ColorsBox.Colors={colors_str}')
        ini_lines.append(f'ShadowColorsBox.Colors={colors_str}')
        
        if self.header.TypeOfDef == 0x47:
            player_colors = '|'.join([f'${r:02X}{g:02X}{b:02X}' for r, g, b in self._pure_pal[224:256]]) + '|'
            ini_lines.append(f'ColorsBox.PlayerColors={player_colors}')
        
        # Color checks
        color_checks = [False] * 9
        color_checks[0] = True
        color_checks[5] = (self.header.TypeOfDef in [0x43, 0x44])
        if not shadow_dir and self.header.TypeOfDef == 0x42:
            for i in range(1, 8):
                color_checks[i] = True
        
        ini_lines.append(f'ColorsBox.ColorChecks={"|" .join(["1" if c else "0" for c in color_checks]) + "|"}')
        
        shadow_checks = ['1'] * 8
        ini_lines.append(f'ShadowColorsBox.ColorChecks={"|" .join(shadow_checks) + "|"}')
        
        # Write INI file
        with open(filename, 'w') as f:
            f.write('\n'.join(ini_lines) + '\n')
        
        # Extract images
        errors = []
        for i in range(self._pictures_count):
            try:
                if external_shadow and shadow_dir:
                    img, img_spec = self.extract_bmp(i, bmp_spec=True)
                    if in_24_bits:
                        img = img.convert('RGB')
                        img_spec = img_spec.convert('RGB')
                    img.save(dir_path / (self.get_pic_name(i) + '.bmp'))
                    img_spec.save(dir_path / shadow_dir / (self.get_pic_name(i) + '.bmp'))
                else:
                    img = self.extract_bmp(i)
                    if in_24_bits:
                        img = img.convert('RGB')
                    img.save(dir_path / (self.get_pic_name(i) + '.bmp'))
            except Exception as e:
                errors.append(str(e))
        
        return '\n'.join(errors)
    
    @property
    def pictures_count(self) -> int:
        return self._pictures_count
    
    @property
    def def_palette(self) -> Optional[List[tuple]]:
        if self._pure_pal is None:
            self._pure_pal = make_log_palette(self.header.Palette)
        return self._pure_pal


class TRSPicBuffer:
    """Picture buffer for loading and caching bitmaps"""
    
    def __init__(self):
        self._pics: List[Optional[Image.Image]] = []
        self._files: Optional[List[str]] = None
        self.links: List[int] = []
    
    def initialize(self, files: List[str]):
        """Initialize buffer with file list"""
        k = len(files)
        self._files = files
        
        # Free existing pics
        self._pics = [None] * k
        self.links = list(range(k))
        
        # Find duplicate files
        for i in range(k):
            for j in range(i):
                if Path(files[i]).resolve() == Path(files[j]).resolve():
                    self.links[i] = j
                    break
    
    def load_pic(self, i: int):
        """Load picture by index"""
        if Image is None:
            raise ImportError("PIL/Pillow required")
        
        i = self.links[i]
        if self._pics[i] is None:
            self._pics[i] = Image.open(self._files[i])
        return self._pics[i]


class TRSDefMaker:
    """DEF file creator/packer"""
    
    def __init__(self):
        self.pic_names: List[str] = []
        self.pics: List[Image.Image] = []
        self.pics_spec: List[Optional[Image.Image]] = []
        self.compression: int = 0
        self.def_type: int = 0x43
        self._groups: List[List[int]] = []
    
    def add_pic(self, name: str, pic, pic_spec=None) -> int:
        """Add picture to DEF"""
        i = len(self.pics)
        self.pic_names.append(name)
        self.pics.append(pic)
        self.pics_spec.append(pic_spec)
        return i
    
    def add_item(self, group: int, pic_num: int):
        """Add item to group"""
        while len(self._groups) <= group:
            self._groups.append([])
        self._groups[group].append(pic_num)
    
    def _pack_bitmap(self, bmp, spec, compr: int) -> bytes:
        """Pack bitmap with compression"""
        if Image is None:
            raise ImportError("PIL/Pillow required")
        
        # Convert to paletted if needed
        if bmp.mode != 'P':
            bmp = bmp.convert('P', palette=Image.ADAPTIVE, colors=256)
        
        w, h = bmp.size
        
        if compr == 3:
            assert (w % 32 == 0) and (h % 32 == 0), "Dimensions must divide by 32"
        
        # Get frame rect (non-zero area)
        if compr != 0:
            # Find bounding box
            if spec:
                bbox = spec.getbbox()
            else:
                bbox = bmp.getbbox()
            
            if bbox:
                r_left, r_top, r_right, r_bottom = bbox
            else:
                r_left = r_top = r_right = r_bottom = 0
            
            if compr == 3:
                r_left = (r_left // 32) * 32
                r_top = (r_top // 32) * 32
                r_right = ((r_right + 31) // 32) * 32
                r_bottom = ((r_bottom + 31) // 32) * 32
        else:
            r_left, r_top, r_right, r_bottom = 0, 0, w, h
        
        frame_w = r_right - r_left
        frame_h = r_bottom - r_top
        
        # Create header
        result = bytearray()
        result.extend(struct.pack('<8I', 0, compr, w, h, frame_w, frame_h, r_left, r_top))
        
        if frame_w == 0:
            struct.pack_into('<I', result, 0, len(result) - 32)
            return bytes(result)
        
        # Get pixel data
        pixels = bmp.load()
        buf = bytearray(frame_w * frame_h)
        sh_buf = bytearray(frame_w * frame_h)
        
        for y in range(frame_h):
            for x in range(frame_w):
                px = pixels[r_left + x, r_top + y]
                buf[y * frame_w + x] = px if isinstance(px, int) else px[0]
                sh_buf[y * frame_w + x] = 255
        
        if spec:
            spec_pixels = spec.load()
            for y in range(frame_h):
                for x in range(frame_w):
                    px = spec_pixels[r_left + x, r_top + y]
                    sh_buf[y * frame_w + x] = px if isinstance(px, int) else px[0]
        else:
            # Convert buf to shadow
            for i in range(len(sh_buf)):
                if compr == 1:
                    sh_buf[i] = buf[i] if buf[i] < 8 else 255
                else:
                    sh_buf[i] = buf[i] if buf[i] < 7 else 255
        
        # Compress
        if compr == 0:
            result.extend(buf)
        elif compr == 1:
            # Type 1 compression
            offset_table = bytearray(frame_h * 4)
            compressed = bytearray()
            
            for j in range(frame_h):
                struct.pack_into('<I', offset_table, j * 4, len(compressed))
                i = 0
                while i < frame_w:
                    code = sh_buf[j * frame_w + i]
                    length = 1
                    while i + length < frame_w and sh_buf[j * frame_w + i + length] == code:
                        length += 1
                        if length >= 256:
                            break
                    
                    compressed.append(code)
                    compressed.append(length - 1)
                    if code == 255:
                        compressed.extend(buf[j * frame_w + i:j * frame_w + i + length])
                    i += length
            
            result.extend(offset_table)
            result.extend(compressed)
        
        elif compr in [2, 3]:
            # Type 2/3 compression
            if compr == 3:
                frame_h = frame_h * (frame_w // 32)
                frame_w = 32
            
            offset_table = bytearray(frame_h * 2)
            compressed = bytearray()
            
            for j in range(frame_h):
                struct.pack_into('<H', offset_table, j * 2, len(compressed))
                i = 0
                while i < frame_w:
                    code = sh_buf[j * frame_w + i]
                    length = 1
                    while i + length < frame_w and sh_buf[j * frame_w + i + length] == code:
                        length += 1
                        if length >= 32:
                            break
                    
                    compressed.append((length - 1) | (code << 5))
                    if code >= 7:
                        compressed.extend(buf[j * frame_w + i:j * frame_w + i + length])
                    i += length
            
            result.extend(offset_table)
            result.extend(compressed)
        
        # Update file size
        struct.pack_into('<I', result, 0, len(result) - 32)
        return bytes(result)
    
    def make(self, stream):
        """Create DEF file and write to stream"""
        if not self.pics:
            raise ValueError("At least one picture required")
        
        # Calculate header size
        gr_count = sum(1 for g in self._groups if g)
        header_size = 784  # TRSDefHeader size
        for g in self._groups:
            if g:
                header_size += 16 + 13 * len(g) + 4 * len(g)
        
        # Pack pictures
        pic_data = []
        offsets = []
        offset = header_size
        
        for i in range(len(self.pics)):
            data = self._pack_bitmap(self.pics[i], self.pics_spec[i], self.compression)
            pic_data.append(data)
            offsets.append(offset)
            offset += len(data)
        
        # Create header
        header = bytearray(header_size)
        
        # Main header
        w, h = self.pics[0].size
        struct.pack_into('<IIII', header, 0, self.def_type, w, h, gr_count)
        
        # Palette
        palette = self.pics[0].getpalette()
        if palette:
            for i in range(256):
                header[16 + i * 3] = palette[i * 3]
                header[16 + i * 3 + 1] = palette[i * 3 + 1]
                header[16 + i * 3 + 2] = palette[i * 3 + 2]
        
        # Groups
        p = 784
        for i, group in enumerate(self._groups):
            if group:
                struct.pack_into('<IIII', header, p, i, len(group), 0, 0)
                p += 16
                
                # Names
                for pic_num in group:
                    name_bytes = self.pic_names[pic_num].encode('ascii')[:13]
                    header[p:p + len(name_bytes)] = name_bytes
                    p += 13
                
                # Offsets
                for pic_num in group:
                    struct.pack_into('<I', header, p, offsets[pic_num])
                    p += 4
        
        # Write to stream
        stream.write(bytes(header))
        for data in pic_data:
            stream.write(data)


# Helper functions for mask generation
_msk_init_done = False
_obj_array = [False] * 256
_sh_array = [False] * 256

def _init_msk_arrays():
    """Initialize mask color arrays"""
    global _msk_init_done, _obj_array, _sh_array
    if not _msk_init_done:
        _sh_array[1] = True
        _sh_array[4] = True
        for i in range(5, 256):
            _obj_array[i] = True
        _obj_array[6] = False
        _msk_init_done = True

def _process_square(buf: bytes, offset: int, w: int, colors: List[bool]) -> bool:
    """Check if 32x32 square has any matching colors"""
    for y in range(32):
        for x in range(32):
            idx = offset + y * w + x
            if idx < len(buf) and colors[buf[idx]]:
                return True
    return False

def _process_pic(buf: bytes, w: int, h: int, mask: bytearray, colors: List[bool]):
    """Process picture and update mask"""
    for y in range(h // 32):
        for x in range(w // 32):
            if y < 6 and x < 8:
                offset = (y * 32) * w + (x * 32)
                if (mask[5 - y] & (1 << (7 - x))) == 0:
                    if _process_square(buf, offset, w, colors):
                        mask[5 - y] |= (1 << (7 - x))

# Helper functions for TRSDefMaker
def _buf_to_sh_buf(buf: bytearray, std_num: int):
    """Convert buffer to shadow buffer"""
    for i in range(len(buf)):
        if buf[i] >= std_num:
            buf[i] = 255

def _seq_length(buf: bytes, offset: int, max_len: int) -> int:
    """Get length of sequence with same value"""
    if offset >= len(buf):
        return 0
    val = buf[offset]
    length = 1
    while length < max_len and offset + length < len(buf) and buf[offset + length] == val:
        length += 1
    return length

def rs_make_msk(def_wrapper_or_data, msk: Optional[TMsk] = None) -> TMsk:
    """Create mask from DEF file (overloaded)
    
    Usage:
        rs_make_msk(def_wrapper) -> TMsk
        rs_make_msk(def_wrapper, msk) -> None (modifies msk)
        rs_make_msk(def_data) -> TMsk
        rs_make_msk(def_data, msk) -> None (modifies msk)
    """
    _init_msk_arrays()
    
    # Handle bytes input
    if isinstance(def_wrapper_or_data, bytes):
        wrapper = TRSDefWrapper(def_wrapper_or_data)
        result = rs_make_msk(wrapper, msk)
        return result
    
    def_wrapper = def_wrapper_or_data
    
    # Create or use provided mask
    if msk is None:
        msk = TMsk(
            def_wrapper.header.Width // 32,
            def_wrapper.header.Height // 32,
            bytes(6),
            bytes(6)
        )
        return_msk = True
    else:
        msk.Width = def_wrapper.header.Width // 32
        msk.Height = def_wrapper.header.Height // 32
        return_msk = False
    
    mask_object = bytearray(msk.MaskObject if msk.MaskObject else bytes(6))
    mask_shadow = bytearray(msk.MaskShadow if msk.MaskShadow else bytes(6))
    
    def_wrapper._pic_links_needed()
    
    for i in range(def_wrapper.pictures_count):
        try:
            pic_hdr, buf, sh_buf = def_wrapper._extract_buffer(i)
            w = pic_hdr.Width
            h = pic_hdr.Height
            
            if w % 32 != 0 or h % 32 != 0:
                continue
            
            if buf:
                _process_pic(buf, w, h, mask_object, _obj_array)
            if sh_buf:
                _process_pic(sh_buf, w, h, mask_shadow, _sh_array)
        except:
            continue
    
    msk.MaskObject = bytes(mask_object)
    msk.MaskShadow = bytes(mask_shadow)
    
    if return_msk:
        return msk
