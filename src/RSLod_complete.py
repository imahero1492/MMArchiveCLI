"""
Complete RSLod module - combines all parts
Import this for full functionality
"""

# Import all parts
from .RSLod import *
from .RSLod_part2 import TRSMMFiles
from .RSLod_part3 import TRSArchive, TRSMMArchive
from .RSLod_part4 import TRSLodBase
from .RSLod_integrated import TRSLod, TRSLwd as TRSLwdIntegrated


# Use integrated LWD with graphics support
TRSLwd = TRSLwdIntegrated


class TRSSnd(TRSMMArchive):
    """SND archive (sounds)"""
    
    def __init__(self, filename: str = None):
        self.mm = False
        super().__init__(filename)
    
    def add(self, name: str, data: Union[BinaryIO, bytes], size: int = -1, pal: int = 0) -> int:
        """Add file to SND archive"""
        if isinstance(data, bytes):
            data = io.BytesIO(data)
        return self.files.add(os.path.splitext(name)[0], data, size)
    
    def init_options(self, options: TRSMMFilesOptions):
        """Initialize SND options"""
        options.NameSize = 0x28
        options.AddrOffset = 0x28
        options.SizeOffset = 0x2C
        if self.mm:
            options.UnpackedSizeOffset = 0x30
            options.ItemSize = 0x34
        else:
            options.ItemSize = 0x30
        options.DataStart = 4
        options.AddrStart = 0
        options.MinFileSize = 0
    
    def read_header(self, sender: TRSMMFiles, stream: BinaryIO, options: TRSMMFilesOptions, files_count: int):
        """Read SND header"""
        count_data = stream.read(4)
        if len(count_data) < 4:
            raise ERSLodException(S_RS_LOD_UNKNOWN_SND)
        
        files_count = struct.unpack('<I', count_data)[0]
        
        # Heuristics to detect MM format
        if files_count > 0:
            # Try to read first entry
            entry_data = stream.read(0x34)
            if len(entry_data) >= 0x34:
                addr = struct.unpack('<I', entry_data[0x28:0x2C])[0]
                stream.seek(addr, 0)
                sig = stream.read(2)
                if len(sig) == 2:
                    sig_val = struct.unpack('<H', sig)[0]
                    self.mm = (sig_val == 0x789C)  # zlib signature
        
        self.init_options(options)
        stream.seek(4, 0)
    
    def write_header(self, sender: TRSMMFiles, stream: BinaryIO):
        """Write SND header"""
        stream.write(struct.pack('<I', sender.count))
    
    def get_extract_name(self, index: int) -> str:
        """Get extraction filename"""
        return self.files.get_name(index) + '.wav'
    
    def new(self, filename: str, might_and_magic: bool):
        """Create new SND archive"""
        self.mm = might_and_magic
        options = rs_mm_files_options_initialize()
        self.init_options(options)
        self.files.new(filename, options)
    
    def clone_for_processing(self, new_file: str, files_count: int = 0) -> 'TRSSnd':
        """Clone for processing"""
        result = super().clone_for_processing(new_file, files_count)
        result.mm = self.mm
        return result


class TRSVid(TRSMMArchive):
    """VID archive (videos)"""
    
    def __init__(self, filename: str = None):
        self.no_extension = False
        self.init_size_table: List[int] = []
        self.tag_size = 4
        super().__init__(filename)
    
    def _create_internal(self, files: TRSMMFiles):
        """Internal constructor"""
        super()._create_internal(files)
        files.on_get_file_size = self.get_file_size
        files.on_set_file_size = self.set_file_size
        files.set_user_data_size(4)  # VID files need 4 bytes per file for size storage
    
    def get_file_size(self, sender: TRSMMFiles, index: int, size: int) -> int:
        """Get file size callback"""
        user_data = sender.get_user_data(index)
        stored_size = struct.unpack('<i', user_data[0:4])[0] if len(user_data) >= 4 else 0
        
        if stored_size == 0:
            stream = sender.get_as_is_file_stream(index, True)
            try:
                start = stream.tell()
                if self.init_size_table:
                    sz = start + self.init_size_table[index]
                    if index == sender.count - 1:
                        self.init_size_table = []
                else:
                    sz = stream.seek(0, 2)
                
                # Find minimum address after this file
                for i in range(sender.count):
                    addr = sender.get_address(i)
                    if addr >= start and addr < sz and i != index:
                        sz = addr
                
                size = sz - start
                struct.pack_into('<i', user_data, 0, size + 1)
            finally:
                sender.free_as_is_file_stream(index, stream)
            return size
        else:
            return stored_size - 1
    
    def set_file_size(self, sender: TRSMMFiles, index: int, size: int):
        """Set file size callback"""
        user_data = sender.get_user_data(index)
        struct.pack_into('<i', user_data, 0, size + 1)
    
    def add(self, name: str, data: Union[BinaryIO, bytes], size: int = -1, pal: int = 0) -> int:
        """Add file to VID archive"""
        if isinstance(data, bytes):
            data = io.BytesIO(data)
        if self.no_extension and name.lower().endswith('.smk'):
            return super().add(os.path.splitext(name)[0], data, size, pal)
        return super().add(name, data, size, pal)
    
    def init_options(self, options: TRSMMFilesOptions):
        """Initialize VID options"""
        options.NameSize = 0x28
        options.AddrOffset = 0x28
        options.ItemSize = 0x2C
        options.DataStart = 4
        options.AddrStart = 0
        options.MinFileSize = 0
    
    def read_header(self, sender: TRSMMFiles, stream: BinaryIO, options: TRSMMFilesOptions, files_count: int):
        """Read VID header"""
        count_data = my_read_buffer(stream, 4)
        files_count = struct.unpack('<I', count_data)[0]
        sender.count = files_count
        self.init_options(options)
        
        # Check for size table signature
        file_size = stream.seek(0, 2)
        if file_size < len(VID_SIZE_SIG_OLD):
            stream.seek(4, 0)
            return
        stream.seek(file_size - len(VID_SIZE_SIG_OLD), 0)
        sig = stream.read(len(VID_SIZE_SIG_OLD))
        
        if sig == VID_SIZE_SIG_OLD:
            # Old format with size table
            stream.seek(file_size - len(VID_SIZE_SIG_OLD) - files_count * 4, 0)
            if files_count > 0:
                size_data = my_read_buffer(stream, files_count * 4)
                self.init_size_table = list(struct.unpack(f'<{files_count}I', size_data))
        elif sig == VID_SIZE_SIG_END:
            # New format with size table
            stream.seek(file_size - len(VID_SIZE_SIG_END) * 2 - files_count * 4, 0)
            start_sig = stream.read(len(VID_SIZE_SIG_START))
            if start_sig == VID_SIZE_SIG_START and files_count > 0:
                size_data = my_read_buffer(stream, files_count * 4)
                self.init_size_table = list(struct.unpack(f'<{files_count}I', size_data))
        
        if sig == VID_SIZE_SIG_NO_EXT:
            self.no_extension = True
        
        stream.seek(4, 0)
    
    def write_header(self, sender: TRSMMFiles, stream: BinaryIO):
        """Write VID header"""
        n = sender.count
        stream.seek(0, 0)
        stream.write(struct.pack('<I', n))
        
        need_size = self.need_size_table(stream)
        need_no_ext = self.need_no_ext_sig()
        
        i = 0
        if need_size:
            i = len(VID_SIZE_SIG_START) * 2 + n * 4
        if need_no_ext:
            i += len(VID_SIZE_SIG_NO_EXT)
        
        if i == 0:
            return
        
        # Calculate end position
        sz = max(stream.seek(0, 2) - i, sender.options.DataStart)
        for idx in range(n):
            sz = max(sz, sender.get_address(idx) + sender.get_size(idx))
        
        stream.seek(sz, 0)
        
        if need_no_ext:
            stream.write(VID_SIZE_SIG_NO_EXT)
        
        if need_size:
            sizes = [sender.get_size(idx) for idx in range(n)]
            stream.write(VID_SIZE_SIG_START)
            stream.write(struct.pack(f'<{n}I', *sizes))
            stream.write(VID_SIZE_SIG_END)
    
    def get_extract_name(self, index: int) -> str:
        """Get extraction filename"""
        name = self.files.get_name(index)
        if not os.path.splitext(name)[1]:
            return name + '.smk'
        return name
    
    def new(self, filename: str, no_extension: bool):
        """Create new VID archive"""
        self.no_extension = no_extension
        options = rs_mm_files_options_initialize()
        self.init_options(options)
        self.files.new(filename, options)
    
    def load(self, filename: str):
        """Load VID file"""
        self.no_extension = False
        super().load(filename)
        
        # Detect if files have no extension
        for i in range(self.files.count):
            name = self.files.get_name(i)
            ext = os.path.splitext(name)[1]
            if not ext:
                self.no_extension = True
                return
            elif ext.lower() == '.smk':
                return
    
    def clone_for_processing(self, new_file: str, files_count: int = 0) -> 'TRSVid':
        """Clone for processing"""
        result = super().clone_for_processing(new_file, files_count)
        result.no_extension = self.no_extension
        return result
    
    def need_size_table(self, stream: BinaryIO) -> bool:
        """Check if size table is needed"""
        f1 = stream.seek(0, 2)
        for i in range(self.files.count):
            addr = self.files.get_address(i)
            if addr < f1:
                f1 = addr
        
        sz = 0
        for i in range(self.files.count):
            sz += self.files.get_size(i)
        
        return f1 + sz != stream.seek(0, 2)
    
    def need_no_ext_sig(self) -> bool:
        """Check if no-extension signature is needed"""
        if not self.no_extension:
            return False
        for i in range(self.files.count):
            if not os.path.splitext(self.files.get_name(i))[1]:
                return False
        return True


# Utility functions
def rs_load_mm_archive(filename: str) -> TRSMMArchive:
    """Load MM archive based on extension"""
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == '.snd':
        return TRSSnd(filename)
    elif ext == '.vid':
        return TRSVid(filename)
    elif ext == '.lwd':
        return TRSLwd(filename)
    else:
        return TRSLod(filename)


def rs_mm_archives_find(archives: List[TRSMMArchive], name: str) -> tuple:
    """Find file in archive array"""
    for archive in reversed(archives):
        found, index = archive.files.find_file(name)
        if found:
            return archive, index
    return None, -1


def rs_mm_archives_check_file_changed(archives: List[TRSMMArchive], ignore: TRSMMArchive = None) -> bool:
    """Check if any archive file changed"""
    for archive in archives:
        if archive != ignore and archive.files.check_file_changed():
            return True
    return False


def rs_mm_archives_free(archives: List[TRSMMArchive]):
    """Free archive array"""
    for archive in archives:
        archive.files.close()
    archives.clear()


def rs_mm_archives_find_same_palette(archives: List['TRSLod'], pal_entries: bytes) -> int:
    """Find same palette in archive array"""
    for archive in reversed(archives):
        if isinstance(archive, TRSLod):
            pal = 0
            if archive.find_same_palette(pal_entries, pal):
                return pal
    return 0


def rs_mm_archives_is_same_palette(archives: List['TRSLod'], pal_entries: bytes, pal: int) -> bool:
    """Check if palette matches"""
    lod, idx = rs_mm_archives_find(archives, f'pal{pal:03d}')
    return lod is not None and isinstance(lod, TRSLod) and lod.is_same_palette(pal_entries, idx)


# Export main classes
__all__ = [
    'TRSMMFiles',
    'TRSArchive',
    'TRSMMArchive',
    'TRSLodBase',
    'TRSLod',
    'TRSLwd',
    'TRSSnd',
    'TRSVid',
    'TRSLodVersion',
    'TRSMMFilesOptions',
    'ERSLodException',
    'ERSLodWrongFileName',
    'ERSLodBitmapException',
    'rs_load_mm_archive',
    'rs_mm_archives_find',
    'rs_mm_archives_check_file_changed',
    'rs_mm_archives_free',
    'rs_mm_archives_find_same_palette',
    'rs_mm_archives_is_same_palette',
    'rs_mm_files_options_initialize',
    'rs_lod_compare_str',
]
