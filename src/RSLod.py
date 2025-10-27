"""
RSLod - LOD Archive Handler for Heroes/Might & Magic games
Direct Python conversion from RSLod.pas

Copyright (c) Rozhenko Sergey
http://sites.google.com/site/sergroj/
sergroj@mail.ru
"""

import struct
import zlib
import os
import io
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Callable, BinaryIO, Union
from pathlib import Path


# Constants
HEROES_ID = b'\xC8'
MM6_ID = b'MMVI'
MM8_ID = b'MMVIII'

VID_SIZE_SIG_OLD = b'\x3E\xB9\xC5\xC5\x79\x47\x48\xbd\x91\x3A\xAC\xEB\x28\xEB\xE0\x15'
VID_SIZE_SIG_START = b'\x87\x03\xC2\x4E\x26\xCF\x4c\xc6\x97\xDD\xE2\xEC\xAE\xBE\xCD\xB4'
VID_SIZE_SIG_END = b'\x0B\x74\x52\x46\x76\x09\x4d\x9f\xAF\xE5\x3F\x7E\x9B\x23\x78\x0E'
VID_SIZE_SIG_NO_EXT = b'\x3F\x78\xDE\x47\xE9\x2E\x40\x65\x9A\xF1\x74\xBB\xAE\x9D\x77\xD7'
GAMES_LOD7_SIG = VID_SIZE_SIG_OLD

POWER_OF_2 = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768]


# Exceptions
class ERSLodException(Exception):
    pass


class ERSLodWrongFileName(ERSLodException):
    pass


class ERSLodBitmapException(ERSLodException):
    pass


# Resource strings
S_RS_LOD_CORRUPT = 'File invalid or corrupt'
S_RS_LOD_LONG_NAME = 'File name (%s) length exceeds %d symbols'
S_RS_LOD_UNKNOWN = 'Unknown LOD version'
S_RS_LOD_UNKNOWN_SND = 'Unknown SND format'
S_RS_LOD_SPRITE_MUST_PAL = 'Palette index for sprite must be specified'
S_RS_LOD_SPRITE_MUST_256 = 'Sprites must be in 256 colors format'
S_RS_LOD_NO_BITMAPS = "This LOD type doesn't support bitmaps"
S_RS_LOD_SPRITE_MUST_BMP = 'Cannot add files other than bitmaps into sprites.lod'
S_RS_LOD_ACT_PAL_MUST_768 = 'ACT palette size must be 768 bytes'
S_RS_LOD_SPRITE_EXTRACT_NEED_LODS = 'BitmapsLod and TextsLod must be specified to extract images from sprites.lod'
S_RS_LOD_PAL_NOT_FOUND = 'File "PAL%.3d" referenced by "%s" not found in BitmapsLods'
S_RS_LOD_MUST_POWER_OF_2 = "Bitmap %s must be a power of 2 and can't be less than 4"
S_READ_FAILED = 'Failed to read %d bytes at offset %d'


# Enums
class TRSLodVersion(Enum):
    RSLodHeroes = 0
    RSLodBitmaps = 1
    RSLodIcons = 2
    RSLodSprites = 3
    RSLodGames = 4
    RSLodGames7 = 5
    RSLodChapter = 6
    RSLodChapter7 = 7
    RSLodMM8 = 8


# LOD Type definitions
LOD_TYPES = {
    TRSLodVersion.RSLodHeroes: ('', ''),
    TRSLodVersion.RSLodBitmaps: ('MMVI', 'bitmaps'),
    TRSLodVersion.RSLodIcons: ('MMVI', 'icons'),
    TRSLodVersion.RSLodSprites: ('MMVI', 'sprites08'),
    TRSLodVersion.RSLodGames: ('GameMMVI', 'maps'),
    TRSLodVersion.RSLodGames7: ('GameMMVI', 'maps'),
    TRSLodVersion.RSLodChapter: ('MMVI', 'chapter'),
    TRSLodVersion.RSLodChapter7: ('MMVII', 'chapter'),
    TRSLodVersion.RSLodMM8: ('MMVIII', 'language'),
}

LOD_DESCRIPTIONS = {
    TRSLodVersion.RSLodHeroes: '',
    TRSLodVersion.RSLodBitmaps: 'Bitmaps for MMVI.',
    TRSLodVersion.RSLodIcons: 'Icons for MMVI.',
    TRSLodVersion.RSLodSprites: 'Sprites for MMVI.',
    TRSLodVersion.RSLodGames: 'Maps for MMVI',
    TRSLodVersion.RSLodGames7: 'Maps for MMVI',
    TRSLodVersion.RSLodChapter: 'newmaps for MMVI',
    TRSLodVersion.RSLodChapter7: 'newmaps for MMVII',
    TRSLodVersion.RSLodMM8: 'Language for MMVIII.',
}


# Data structures
@dataclass
class TRSLodHeroesHeader:
    Signature: bytes  # 4 bytes
    Version: int  # DWord
    Count: int  # DWord
    Unknown: bytes  # 80 bytes


@dataclass
class TRSLodMMHeader:
    Signature: bytes  # 4 bytes
    Version: bytes  # 80 bytes
    Description: bytes  # 80 bytes
    Unk1: int
    Unk2: int
    ArchivesCount: int
    Unknown: bytes  # 80 bytes
    LodType: bytes  # 16 bytes
    ArchiveStart: int
    ArchiveSize: int
    Unk5: int
    Count: int  # uint2
    Unk6: int  # uint2


@dataclass
class TRSMMFilesOptions:
    NameSize: int = 0
    AddrOffset: int = -1
    SizeOffset: int = -1
    UnpackedSizeOffset: int = -1
    PackedSizeOffset: int = -1
    ItemSize: int = 0
    DataStart: int = 0
    AddrStart: int = 0
    MinFileSize: int = 0


@dataclass
class TMMLodFile:
    BmpSize: int
    DataSize: int
    BmpWidth: int
    BmpHeight: int
    BmpWidthLn2: int
    BmpHeightLn2: int
    BmpWidthMinus1: int
    BmpHeightMinus1: int
    Palette: int
    _unk: int
    UnpSize: int
    Bits: int


@dataclass
class TSpriteLine:
    a1: int
    a2: int
    pos: int


@dataclass
class TSprite:
    Size: int
    w: int
    h: int
    Palette: int
    unk_1: int
    yskip: int
    unk_2: int
    UnpSize: int


@dataclass
class TPCXFileHeader:
    ImageSize: int
    Width: int
    Height: int


@dataclass
class TMM6GamesFile:
    DataSize: int
    UnpackedSize: int


@dataclass
class TMM7GamesFile:
    Sig1: int
    Sig2: int
    DataSize: int
    UnpackedSize: int


# Helper functions
def rs_lod_compare_str(s1: str, s2: str) -> int:
    """Case-insensitive string comparison (_stricmp)"""
    s1_lower = s1.lower()
    s2_lower = s2.lower()
    if s1_lower < s2_lower:
        return -1
    elif s1_lower > s2_lower:
        return 1
    return 0


def rs_lod_compare_str_with_count(s1: str, s2: str) -> tuple:
    """Case-insensitive string comparison with same character count"""
    same_count = 0
    for c1, c2 in zip(s1.lower(), s2.lower()):
        if c1 != c2:
            break
        same_count += 1
    
    result = rs_lod_compare_str(s1, s2)
    return result, same_count


def my_get_file_time(filename: str) -> int:
    """Get file modification time"""
    try:
        return int(os.path.getmtime(filename) * 10000000)
    except:
        return 0


def get_ln2(v: int) -> int:
    """Get log2 of value if it's a power of 2"""
    result = 0
    while v != 0 and (v & 1) == 0:
        v >>= 1
        result += 1
    return result if v == 1 else 0


def rs_mm_files_options_initialize() -> TRSMMFilesOptions:
    """Initialize options with default values"""
    return TRSMMFilesOptions()


def my_read_buffer(stream: BinaryIO, size: int) -> bytes:
    """Read buffer with assertion"""
    data = stream.read(size)
    if len(data) != size:
        raise ERSLodException(S_READ_FAILED % (size, stream.tell()))
    return data


def unzip_ignore_errors(output: BinaryIO, input: BinaryIO, unp: int, noless: bool):
    """Unzip with error handling"""
    old_pos = output.tell()
    old_pos_i = input.tell()
    
    try:
        data = zlib.decompress(input.read())
        output.write(data[:unp])
    except:
        input.seek(old_pos_i)
        try:
            decompressor = zlib.decompressobj()
            read_ok = output.tell() - old_pos
            remaining = unp - read_ok
            
            for _ in range(remaining):
                try:
                    chunk = input.read(1)
                    if chunk:
                        output.write(decompressor.decompress(chunk))
                except:
                    break
        except:
            pass
        
        if noless:
            read_ok = output.tell() - old_pos
            for _ in range(unp - read_ok):
                output.write(b'\x00')
