"""
RSLod Integrated - TRSLod with full graphics support
Integrates graphics functions into TRSLod class
"""

from .RSLod import *
from .RSLod_part2 import TRSMMFiles
from .RSLod_part3 import TRSMMArchive
from .RSLod_part4 import TRSLodBase, TRSLod as TRSLodBase_Original
from .RSLod_graphics import *
from PIL import Image
import io
import os


class TRSLod(TRSLodBase_Original):
    """TRSLod with integrated graphics support"""
    
    def add(self, name: str, data, size: int = -1, pal: int = 0) -> int:
        """Add file to LOD - supports bitmaps, sprites, and raw data"""
        
        # Handle bitmap input
        if isinstance(data, Image.Image):
            return self.add_bitmap(name, data, pal)
        
        # Detect BMP and PCX files - load as Image for add_bitmap
        if name.lower().endswith(('.bmp', '.pcx')):
            if isinstance(data, bytes):
                img = Image.open(io.BytesIO(data))
            elif hasattr(data, 'read'):
                img = Image.open(data)
            else:
                img = data
            return self.add_bitmap(name, img, pal)
        
        # Handle raw data
        if isinstance(data, bytes):
            data = io.BytesIO(data)
        
        return super().add(name, data, size, pal)
    
    def add_bitmap(self, name: str, img: Image.Image, pal: int = 0, keep_mipmaps: bool = True, bits: int = -1) -> int:
        """Add bitmap to LOD with automatic palette handling"""
        
        # Heroes LOD: convert to PCX format
        if self.version == TRSLodVersion.RSLodHeroes:
            packed_data = pack_pcx(img, keep_mipmaps)
            pcx_name = os.path.splitext(name)[0] + '.pcx'
            return super().add(pcx_name, io.BytesIO(packed_data), len(packed_data), pal)
        
        # Check if this LOD type supports bitmaps
        if self.version not in [TRSLodVersion.RSLodBitmaps, TRSLodVersion.RSLodIcons, 
                                TRSLodVersion.RSLodSprites, TRSLodVersion.RSLodMM8]:
            raise ERSLodException(S_RS_LOD_NO_BITMAPS)
        
        # Find palette if needed
        if bits < 0:
            pal, bits = self.find_bitmap_palette(name, img)
        
        # Handle sprites
        if self.version == TRSLodVersion.RSLodSprites:
            if pal < 0:
                raise ERSLodException(S_RS_LOD_SPRITE_MUST_PAL)
            
            # Pack sprite
            packed_data = pack_sprite(img, pal)
            return super().add(name, io.BytesIO(packed_data), len(packed_data), pal)
        
        # Pack bitmap
        packed_data = pack_bitmap(img, pal, bits, keep_mipmaps)
        return super().add(name, io.BytesIO(packed_data), len(packed_data), pal)
    
    def find_bitmap_palette(self, name: str, img: Image.Image) -> tuple:
        """Find appropriate palette for bitmap"""
        pal = 0
        bits = 0
        
        # Sprites need palette
        if self.version == TRSLodVersion.RSLodSprites:
            if self.on_sprite_palette:
                self.on_sprite_palette(self, name, pal, img)
            return pal, bits
        
        # Bitmaps/Icons
        if self.version in [TRSLodVersion.RSLodBitmaps, TRSLodVersion.RSLodIcons, TRSLodVersion.RSLodMM8]:
            # Check if power of 2
            w, h = img.size
            if get_ln2(w) > 0 and get_ln2(h) > 0 and w >= 4 and h >= 4:
                bits = 2  # Enable mipmaps
            
            # Get palette from image
            if img.mode == 'P':
                palette = img.getpalette()
                if palette:
                    pal_bytes = bytes(palette[:768])
                    
                    # Try to find same palette
                    if self.bitmaps_lods:
                        found, pal_idx = self.find_same_palette_in_lods(pal_bytes)
                        if found:
                            pal = pal_idx
                            self.last_palette = pal
                            return pal, bits
                    
                    # Ask for palette
                    if self.on_need_palette:
                        self.on_need_palette(self, img, pal)
                        self.last_palette = pal
                        return pal, bits
        
        return pal, bits
    
    def find_same_palette_in_lods(self, pal_entries: bytes) -> tuple:
        """Find same palette in bitmaps LODs"""
        for lod in reversed(self.bitmaps_lods):
            found, pal_idx = lod.find_same_palette(pal_entries, 0)
            if found:
                return True, pal_idx
        return False, 0
    
    def load_palette(self, pal: int, name: str = '') -> bytes:
        """Load palette from bitmaps LOD"""
        if not self.bitmaps_lods and self.on_need_bitmaps_lod:
            self.on_need_bitmaps_lod(self)
        
        if not self.bitmaps_lods:
            raise ERSLodException(S_RS_LOD_SPRITE_EXTRACT_NEED_LODS)
        
        # Find palette file
        pal_name = f'pal{pal:03d}'
        archive, idx = rs_mm_archives_find(self.bitmaps_lods, pal_name)
        
        if archive is None:
            raise ERSLodException(S_RS_LOD_PAL_NOT_FOUND % (pal, name))
        
        # Extract palette
        stream = archive.files.get_as_is_file_stream(idx)
        try:
            stream.seek(archive.files.options.NameSize + 48, 1)  # Skip name and header
            pal_data = stream.read(768)
            if len(pal_data) != 768:
                raise ERSLodException(S_RS_LOD_ACT_PAL_MUST_768)
            return pal_data
        finally:
            archive.files.free_as_is_file_stream(idx, stream)
    
    def extract(self, index: int, output=None, overwrite: bool = True):
        """Extract file - supports bitmaps, sprites, and raw data"""
        
        # Check if it's a bitmap/sprite that needs conversion
        if self.version in [TRSLodVersion.RSLodBitmaps, TRSLodVersion.RSLodIcons, 
                           TRSLodVersion.RSLodSprites, TRSLodVersion.RSLodMM8]:
            
            # If output is a directory, extract as image
            if isinstance(output, str):
                return self.extract_as_image(index, output, overwrite)
            
            # If no output, return Image object
            if output is None:
                return self.extract_image(index)
        
        # Default extraction
        return super().extract(index, output, overwrite)
    
    def extract_image(self, index: int) -> Image.Image:
        """Extract file as PIL Image"""
        
        stream = self.files.get_as_is_file_stream(index)
        try:
            stream.seek(self.files.options.NameSize, 1)
            
            # Sprites
            if self.version == TRSLodVersion.RSLodSprites:
                size = self.files.get_size(index) - self.files.options.NameSize
                hdr_data = stream.read(20)
                if len(hdr_data) < 20:
                    raise ERSLodException(S_RS_LOD_CORRUPT)
                
                hdr = TSprite.unpack(hdr_data)
                pal_data = self.load_palette(hdr.palette, self.files.get_name(index))
                
                stream.seek(self.files.options.NameSize, 0)
                return unpack_sprite(stream, size, pal_data)
            
            # Bitmaps
            elif self.version in [TRSLodVersion.RSLodBitmaps, TRSLodVersion.RSLodIcons, TRSLodVersion.RSLodMM8]:
                size = self.files.get_size(index) - self.files.options.NameSize
                img, pal_data = unpack_bitmap(stream, size)
                return img
            
            # PCX (Heroes format)
            elif self.version == TRSLodVersion.RSLodHeroes:
                name = self.files.get_name(index)
                if name.lower().endswith('.pcx'):
                    img, pal_data = unpack_pcx(stream)
                    return img
        
        finally:
            self.files.free_as_is_file_stream(index, stream)
        
        # Fallback to raw extraction
        return None
    
    def extract_as_image(self, index: int, directory: str, overwrite: bool = True) -> str:
        """Extract file as image to directory"""
        
        img = self.extract_image(index)
        if img is None:
            return super().extract(index, directory, overwrite)
        
        # Get output filename
        name = self.get_extract_name(index)
        if name.endswith('.mmrawdata'):
            name = os.path.splitext(name)[0] + '.bmp'
        elif name.endswith('.act'):
            # Save palette as image
            stream = self.files.get_as_is_file_stream(index)
            try:
                stream.seek(self.files.options.NameSize + 48, 1)
                pal_data = stream.read(768)
                img = rs_mm_palette_to_bitmap(pal_data)
            finally:
                self.files.free_as_is_file_stream(index, stream)
        
        output_path = os.path.join(directory, name)
        
        if not overwrite and os.path.exists(output_path):
            return output_path
        
        os.makedirs(directory, exist_ok=True)
        img.save(output_path)
        return output_path
    
    def extract_array_or_bmp(self, index: int, arr: list = None) -> Image.Image:
        """Extract as array or bitmap"""
        
        # Try to extract as image
        img = self.extract_image(index)
        if img is not None:
            return img
        
        # Extract as raw array
        if arr is not None:
            stream = self.files.get_as_is_file_stream(index)
            try:
                stream.seek(self.files.options.NameSize, 1)
                size = self.files.get_size(index) - self.files.options.NameSize
                data = stream.read(size)
                arr.clear()
                arr.extend(data)
            finally:
                self.files.free_as_is_file_stream(index, stream)
        
        return None


class TRSLwd(TRSLod):
    """LWD archive with transparent bitmap support"""
    
    def __init__(self, filename: str = None):
        self.transparent_color = (0, 0, 0)  # Default black
        self.on_find_dimentions: Optional[Callable] = None
        super().__init__(filename)
    
    def find_bitmap_palette(self, name: str, img: Image.Image) -> tuple:
        """LWD doesn't use palettes"""
        return 0, 0
    
    def add_bitmap(self, name: str, img: Image.Image, pal: int = 0, keep_mipmaps: bool = False, bits: int = 0) -> int:
        """Add transparent bitmap to LWD"""
        
        # Find dimensions if needed
        w, h = img.size
        if self.on_find_dimentions:
            self.on_find_dimentions(self, name, w, h, w, h)
        
        # Pack LWD
        packed_data = pack_lwd(img, self.transparent_color)
        return self.files.add(name, io.BytesIO(packed_data), len(packed_data))
    
    def extract_image(self, index: int) -> Image.Image:
        """Extract LWD as image"""
        
        stream = self.files.get_as_is_file_stream(index)
        try:
            stream.seek(self.files.options.NameSize, 1)
            
            # Get dimensions from file name or callback
            name = self.files.get_name(index)
            w, h = 256, 256  # Default
            
            if self.on_find_dimentions:
                self.on_find_dimentions(self, name, w, h, w, h)
            
            return unpack_lwd(stream, w, h, self.transparent_color)
        
        finally:
            self.files.free_as_is_file_stream(index, stream)


# Export integrated classes
__all__ = [
    'TRSLod',
    'TRSLwd',
]
