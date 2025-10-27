"""RSLod Part 4 - TRSLodBase and TRSLod classes"""

from .RSLod import *
from .RSLod_part2 import TRSMMFiles
from .RSLod_part3 import TRSMMArchive


class TRSLodBase(TRSMMArchive):
    """Base LOD archive class"""
    
    def __init__(self, filename: str = None):
        self.any_header = bytearray(288)  # Size of TRSLodMMHeader
        self.heroes_header = None
        self.mm_header = None
        self.additional_data = bytearray()
        self.version = TRSLodVersion.RSLodHeroes
        
        super().__init__(filename)
    
    def clone_for_processing(self, new_file: str, files_count: int = 0) -> 'TRSLodBase':
        """Clone for processing"""
        result = super().clone_for_processing(new_file, files_count)
        result.any_header = bytearray(self.any_header)
        result.version = self.version
        result.additional_data = bytearray(self.additional_data)
        result.heroes_header = self.heroes_header
        result.mm_header = self.mm_header
        
        if self.version == TRSLodVersion.RSLodHeroes:
            if result.heroes_header:
                result.heroes_header = dict(result.heroes_header)
                result.heroes_header['Count'] = 0
        else:
            if result.mm_header:
                result.mm_header = dict(result.mm_header)
                result.mm_header['Count'] = 0
                result.mm_header['ArchiveSize'] = result.files.file_size - result.files.options.DataStart
        
        if self.version in [TRSLodVersion.RSLodGames, TRSLodVersion.RSLodGames7, 
                           TRSLodVersion.RSLodChapter, TRSLodVersion.RSLodChapter7]:
            result.files.sorted = self.files.sorted
        
        return result
    
    def _create_internal(self, files: TRSMMFiles):
        """Internal constructor"""
        super()._create_internal(files)
        files.on_after_rename_file = self.after_rename_file
    
    def init_options(self, options: TRSMMFilesOptions):
        """Initialize options based on version"""
        if self.version != TRSLodVersion.RSLodHeroes:
            if self.version == TRSLodVersion.RSLodMM8:
                options.NameSize = 0x40
                options.AddrOffset = 0x40
                options.UnpackedSizeOffset = 0x44
                options.ItemSize = 0x4C
            else:
                options.NameSize = 0x10
                options.AddrOffset = 0x10
                options.UnpackedSizeOffset = 0x14
                options.ItemSize = 0x20
            
            options.PackedSizeOffset = -1
            options.AddrStart = self.mm_header['ArchiveStart'] if self.mm_header else 0
            options.DataStart = options.AddrStart
            options.MinFileSize = 0
        else:
            options.NameSize = 0x10
            options.AddrOffset = 0x10
            options.UnpackedSizeOffset = 0x14
            options.PackedSizeOffset = 0x1C
            options.ItemSize = 0x20
            options.AddrStart = 0
            options.DataStart = 92 if self.heroes_header['Signature'] == b'LOD\x00' else 96  # Adjust for LOD format
            options.MinFileSize = 320092
    
    def read_header(self, sender: TRSMMFiles, stream: BinaryIO, options: TRSMMFilesOptions, files_count: int):
        """Read LOD header"""
        # Read initial header data, padding with zeros if file is too small
        current_pos = stream.tell()
        file_size = stream.seek(0, 2)
        stream.seek(current_pos, 0)
        
        bytes_to_read = min(96, file_size - current_pos)
        if bytes_to_read < 96:
            header_data = stream.read(bytes_to_read) + b'\x00' * (96 - bytes_to_read)
        else:
            header_data = my_read_buffer(stream, 96)
        
        signature = header_data[0:4]
        version = struct.unpack('<I', header_data[4:8])[0]
        count = struct.unpack('<I', header_data[8:12])[0]
        
        self.version = TRSLodVersion.RSLodHeroes
        
        # Check signature first - LOD\x00 indicates MM format
        if signature == b'LOD\x00':
            # Check if this is a full MM format or a simple LOD format
            # Full MM format should have more structured data
            # Simple format: LOD\x00 + version + count + file entries
            
            # Try to read as simple format first
            # Check if values look like version/count rather than MM header
            # MM format would have structured data, simple format has reasonable counts
            if ((version < 1000 and count < 10000) or 
                (abs(version - count) <= 1 and count > 1000)):
                # This looks like a simple LOD format with LOD signature
                # Second condition handles HotA.lod (version=4670, count=4669)
                # Allow count=0 for empty archives
                self.heroes_header = {
                    'Signature': signature,
                    'Version': version,
                    'Count': count,
                    'Unknown': header_data[12:96]
                }
                files_count = count
                sender.count = files_count  # Set the count directly
                self.init_options(options)
                return
            
            # MM format
            bytes_to_read = min(192, file_size - stream.tell())
            if bytes_to_read < 192:
                mm_header_data = stream.read(bytes_to_read) + b'\x00' * (192 - bytes_to_read)
            else:
                mm_header_data = my_read_buffer(stream, 192)  # Rest of MM header
            full_header = header_data + mm_header_data
            
            self.mm_header = {
                'Signature': full_header[0:4],
                'Version': full_header[4:84].rstrip(b'\x00'),
                'Description': full_header[84:164].rstrip(b'\x00'),
                'Unk1': struct.unpack('<i', full_header[164:168])[0],
                'Unk2': struct.unpack('<i', full_header[168:172])[0],
                'ArchivesCount': struct.unpack('<i', full_header[172:176])[0],
                'LodType': full_header[256:272].rstrip(b'\x00'),
                'ArchiveStart': struct.unpack('<I', full_header[272:276])[0],
                'ArchiveSize': struct.unpack('<I', full_header[276:280])[0],
                'Unk5': struct.unpack('<i', full_header[280:284])[0],
                'Count': struct.unpack('<H', full_header[284:286])[0],
                'Unk6': struct.unpack('<H', full_header[286:288])[0],
            }
            
            # Detect version
            for ver in TRSLodVersion:
                if ver == TRSLodVersion.RSLodHeroes:
                    continue
                ver_str, lod_type = LOD_TYPES[ver]
                if (self.mm_header['Version'] == ver_str.encode() and 
                    self.mm_header['LodType'] == lod_type.encode()):
                    self.version = ver
                    break
            
            if self.version == TRSLodVersion.RSLodHeroes:
                raise ERSLodException(S_RS_LOD_UNKNOWN)
            
            if self.version == TRSLodVersion.RSLodGames:
                sender.games_lod = True
            
            files_count = self.mm_header['Count']
            self.init_options(options)
            
            # Read additional data
            add_size = self.mm_header['ArchiveStart'] - 288
            if add_size > 0:
                self.additional_data = bytearray(my_read_buffer(stream, add_size))
            
            # Check for Games7 signature
            if self.version == TRSLodVersion.RSLodGames:
                stream.seek(-len(GAMES_LOD7_SIG), 2)
                sig = stream.read(len(GAMES_LOD7_SIG))
                if sig == GAMES_LOD7_SIG:
                    self.version = TRSLodVersion.RSLodGames7
        else:
            # Heroes format
            self.heroes_header = {
                'Signature': signature,
                'Version': version,
                'Count': count,
                'Unknown': header_data[12:92]
            }
            files_count = count
            self.init_options(options)
    
    def write_header(self, sender: TRSMMFiles, stream: BinaryIO):
        """Write LOD header"""
        if self.version == TRSLodVersion.RSLodHeroes:
            # Write Heroes header
            stream.write(self.heroes_header['Signature'])
            stream.write(struct.pack('<I', sender.count))
            stream.write(struct.pack('<I', sender.count))
            stream.write(self.heroes_header['Unknown'])
        else:
            # Write MM header
            self.mm_header['Count'] = sender.count
            self.mm_header['ArchiveSize'] = sender.file_size - sender.options.DataStart
            
            # Build header
            header = bytearray(288)
            header[0:4] = b'LOD\x00'
            
            ver_str, lod_type = LOD_TYPES[self.version]
            header[4:4+len(ver_str)] = ver_str.encode()
            
            desc = LOD_DESCRIPTIONS[self.version]
            header[84:84+len(desc)] = desc.encode()
            
            struct.pack_into('<i', header, 164, 100)  # Unk1
            struct.pack_into('<i', header, 168, 0)    # Unk2
            struct.pack_into('<i', header, 172, 1)    # ArchivesCount
            
            header[256:256+len(lod_type)] = lod_type.encode()
            struct.pack_into('<I', header, 272, 0x120)  # ArchiveStart
            struct.pack_into('<I', header, 276, self.mm_header['ArchiveSize'])
            struct.pack_into('<i', header, 280, 0)  # Unk5
            struct.pack_into('<H', header, 284, sender.count)
            struct.pack_into('<H', header, 286, 0)  # Unk6
            
            stream.write(header)
            if self.additional_data:
                stream.write(self.additional_data)
        
        self.write_games_lod7_sig(sender, stream)
    
    def write_games_lod7_sig(self, sender: TRSMMFiles, stream: BinaryIO):
        """Write Games LOD 7 signature if needed"""
        if self.version != TRSLodVersion.RSLodGames7:
            return
        
        # Check if we need the signature
        for i in range(sender.count):
            name = sender.get_name(i)
            ext = os.path.splitext(name)[1].lower()
            if ext in ['.blv', '.dlv', '.odm', '.ddm']:
                return
        
        # Write signature at end
        sz = max(stream.tell() - len(GAMES_LOD7_SIG), sender.options.DataStart)
        for i in range(sender.count):
            sz = max(sz, sender.get_address(i) + sender.get_size(i))
        
        stream.seek(sz, 0)
        stream.write(GAMES_LOD7_SIG)
    
    def after_rename_file(self, sender: TRSMMFiles, index: int):
        """Handle file rename"""
        if self.version not in [TRSLodVersion.RSLodBitmaps, TRSLodVersion.RSLodIcons, 
                                TRSLodVersion.RSLodMM8, TRSLodVersion.RSLodSprites]:
            return
        
        # Update name in file structure
        if not sender.write_on_demand:
            stream = sender.begin_write()
            try:
                stream.seek(sender.get_address(index), 0)
                name = sender.get_name(index).encode('ascii')
                name = name.ljust(sender.options.NameSize, b'\x00')
                stream.write(name)
            finally:
                sender.end_write()
    
    def get_extract_name(self, index: int) -> str:
        """Get extraction filename"""
        return self.files.get_name(index) + '.mmrawdata'
    
    def new(self, filename: str, version: TRSLodVersion):
        """Create new LOD"""
        self.version = version
        self.any_header = bytearray(288)
        self.additional_data = bytearray()
        
        if version != TRSLodVersion.RSLodHeroes:
            self.mm_header = {
                'Signature': b'LOD\x00',
                'Version': LOD_TYPES[version][0].encode(),
                'Description': LOD_DESCRIPTIONS[version].encode(),
                'Unk1': 100,
                'Unk2': 0,
                'ArchivesCount': 1,
                'LodType': LOD_TYPES[version][1].encode(),
                'ArchiveStart': 0x120,
                'ArchiveSize': 0,
                'Unk5': 0,
                'Count': 0,
                'Unk6': 0,
            }
        else:
            self.heroes_header = {
                'Signature': b'\xC8LOD',
                'Version': 200,
                'Count': 0,
                'Unknown': bytearray(80)
            }
        
        options = rs_mm_files_options_initialize()
        self.init_options(options)
        self.files.new(filename, options)
        self.files.games_lod = version in [TRSLodVersion.RSLodGames, TRSLodVersion.RSLodGames7]
    
    def load(self, filename: str):
        """Load LOD file"""
        super().load(filename)
        
        # Detect Games7 version
        if self.version == TRSLodVersion.RSLodGames:
            for i in range(self.files.count):
                name = self.files.get_name(i)
                ext = os.path.splitext(name)[1].lower()
                if ext in ['.blv', '.dlv', '.odm', '.ddm']:
                    if self.files.get_size(i) < 16:
                        return
                    
                    stream = self.files.get_as_is_file_stream(i, True)
                    try:
                        sig = stream.read(8)
                        sig1, sig2 = struct.unpack('<II', sig)
                        if sig1 == 0x16741 and sig2 == 0x6969766D:
                            self.version = TRSLodVersion.RSLodGames7
                    finally:
                        self.files.free_as_is_file_stream(i, stream)
                    return


class TRSLod(TRSLodBase):
    """Main LOD archive class"""
    
    def __init__(self, filename: str = None):
        self.bitmaps_lods: List['TRSLod'] = []
        self.own_bitmaps_lod = False
        self.last_palette = 0
        
        self.on_need_bitmaps_lod: Optional[Callable] = None
        self.on_need_palette: Optional[Callable] = None
        self.on_convert_to_palette: Optional[Callable] = None
        self.on_sprite_palette: Optional[Callable] = None
        
        super().__init__(filename)
    
    def __del__(self):
        """Destructor"""
        self.set_bitmaps_lod(None)
    
    def get_bitmaps_lod(self) -> Optional['TRSLod']:
        """Get bitmaps LOD"""
        if self.bitmaps_lods:
            return self.bitmaps_lods[0]
        return None
    
    def set_bitmaps_lod(self, v: Optional['TRSLod']):
        """Set bitmaps LOD"""
        if v is not None:
            if not self.bitmaps_lods:
                self.bitmaps_lods = [v]
            else:
                self.bitmaps_lods[0] = v
        else:
            if self.bitmaps_lods and self.own_bitmaps_lod:
                for lod in self.bitmaps_lods:
                    if lod != self:
                        lod.files.close()
            self.bitmaps_lods = []
    
    def find_same_palette(self, pal_entries: bytes, pal: int) -> tuple:
        """Find same palette in bitmaps LOD"""
        if self.version != TRSLodVersion.RSLodBitmaps:
            return False, 0
        
        found1, m1 = self.files.find_file('pal')
        found2, m2 = self.files.find_file('pam')
        if not found1:
            m1 = 0
        if not found2:
            m2 = self.files.count
        
        fr3 = 1
        fr4 = 1000
        fr5 = 10000
        
        for i in range(m1, m2):
            name = self.files.get_name(i)
            if not name.lower().startswith('pal'):
                continue
            
            try:
                j = int(name[3:])
            except:
                continue
            
            if j == 0 or j > 0x7FFF:
                continue
            
            if j <= fr3:
                fr3 = j + 1
            elif j <= fr4:
                fr4 = j + 1
            elif j <= fr5:
                fr5 = j + 1
            
            if self.is_same_palette(pal_entries, i):
                return True, j
        
        # Find free palette index
        if fr3 < 1000:
            pal = fr3
        elif fr4 < 10000:
            pal = fr4
        else:
            pal = fr5
        
        return False, pal
    
    def is_same_palette(self, pal_entries: bytes, i: int) -> bool:
        """Check if palette at index matches"""
        read_off = 16
        file_size = 48 + read_off + 768  # sizeof(TMMLodFile) + read_off + 768
        
        if self.files.get_size(i) != file_size:
            return False
        
        stream = self.files.get_as_is_file_stream(i)
        try:
            stream.seek(read_off, 1)
            pal_file = stream.read(48 + 768)
            if len(pal_file) < 48 + 768:
                return False
            
            # Check header
            bmp_size, data_size, bmp_width = struct.unpack('<III', pal_file[0:12])
            if bmp_size != 0 or data_size != 0 or bmp_width != 0:
                return False
            
            # Compare palette
            return pal_file[48:48+768] == pal_entries
        finally:
            self.files.free_as_is_file_stream(i, stream)
    
    def get_int_at(self, i: int, offset: int) -> int:
        """Get integer at offset in file"""
        stream = self.files.get_as_is_file_stream(i)
        try:
            stream.seek(offset + self.files.options.NameSize, 1)
            return struct.unpack('<i', stream.read(4))[0]
        finally:
            self.files.free_as_is_file_stream(i, stream)
    
    def _create_internal(self, files: TRSMMFiles):
        """Internal constructor"""
        super()._create_internal(files)
        self.on_need_bitmaps_lod = self.std_need_bitmaps_lod
    
    def std_need_bitmaps_lod(self, sender):
        """Standard bitmaps LOD loader"""
        self.load_bitmaps_lods(os.path.dirname(self.files.out_file))
    
    def load_bitmaps_lods(self, directory: str):
        """Load bitmaps LOD files"""
        self.bitmaps_lods = []
        self.own_bitmaps_lod = True
        
        bitmaps_file = os.path.join(directory, 'bitmaps.lod')
        if os.path.exists(bitmaps_file):
            if bitmaps_file == self.files.out_file:
                self.bitmaps_lods.append(self)
            else:
                self.bitmaps_lods.append(TRSLod(bitmaps_file))
        
        # Load additional *.bitmaps.lod files
        for file in Path(directory).glob('*.bitmaps.lod'):
            if file.is_file():
                self.bitmaps_lods.append(TRSLod(str(file)))
    
    def get_extract_name(self, index: int) -> str:
        """Get extraction filename with proper extension"""
        name = self.files.get_name(index)
        
        if self.version == TRSLodVersion.RSLodHeroes:
            ext = os.path.splitext(name)[1].lower()
            if ext == '.pcx':
                return os.path.splitext(name)[0] + '.bmp'
        elif self.version == TRSLodVersion.RSLodSprites:
            return name + '.bmp'
        elif self.version in [TRSLodVersion.RSLodBitmaps, TRSLodVersion.RSLodIcons, TRSLodVersion.RSLodMM8]:
            # Check if it's a palette or bitmap
            stream = self.files.get_as_is_file_stream(index, True)
            try:
                stream.seek(self.files.options.NameSize, 1)
                hdr_data = stream.read(32)
                if len(hdr_data) >= 8:
                    bmp_size, data_size = struct.unpack('<II', hdr_data[0:8])
                    if bmp_size != 0:
                        return name + '.bmp'
                    elif data_size == 0 and self.files.get_size(index) >= 768 + 32 + self.files.options.NameSize:
                        return name + '.act'
            finally:
                self.files.free_as_is_file_stream(index, stream)
        
        return name
    
    def clone_for_processing(self, new_file: str, files_count: int = 0) -> 'TRSLod':
        """Clone for processing"""
        result = type(self)()
        result._create_internal(self.files.clone_for_processing(new_file, files_count))
        result.bitmaps_lods = self.bitmaps_lods
        result.on_need_bitmaps_lod = self.on_need_bitmaps_lod
        result.on_need_palette = self.on_need_palette
        result.on_convert_to_palette = self.on_convert_to_palette
        result.on_sprite_palette = self.on_sprite_palette
        return result
    
    def compare_files(self, archive2: 'TRSMMArchive', name: str = None, index: int = None, index2: int = None) -> bool:
        """Compare files between LOD archives"""
        if self.version == TRSLodVersion.RSLodHeroes:
            return super().compare_files(archive2, name, index, index2)
        
        if not isinstance(archive2, TRSLodBase) or archive2.version == TRSLodVersion.RSLodHeroes:
            return False
        
        # For LOD files, compare considering internal structure
        return super().compare_files(archive2, name, index, index2)
