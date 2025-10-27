"""RSLod Part 3 - TRSArchive and TRSMMArchive classes"""

from .RSLod import *
from .RSLod_part2 import TRSMMFiles


class TRSArchive:
    """Base archive class"""
    
    def __init__(self, filename: str = None):
        if filename:
            self.load(filename)
    
    def load(self, filename: str):
        """Load archive"""
        raise NotImplementedError
    
    def save_as(self, filename: str):
        """Save archive as"""
        raise NotImplementedError
    
    def get_count(self) -> int:
        """Get file count"""
        raise NotImplementedError
    
    def get_file_name(self, i: int) -> str:
        """Get file name"""
        raise NotImplementedError
    
    @property
    def count(self) -> int:
        return self.get_count()
    
    def names(self, i: int) -> str:
        return self.get_file_name(i)


class TRSMMArchive(TRSArchive):
    """MM Archive base class"""
    
    def __init__(self, filename: str = None):
        self.files = TRSMMFiles()
        self.tag_size = 0
        self.backup_on_add = False
        self.backup_on_add_overwrite = False
        self.backup_on_delete = False
        self.backup_on_delete_overwrite = False
        
        self._create_internal(self.files)
        if filename:
            self.load(filename)
    
    def _create_internal(self, files: TRSMMFiles):
        """Internal constructor"""
        self.files = files
        files.on_read_header = self.read_header
        files.on_write_header = self.write_header
        files.user_data_size = self.tag_size
        files.on_before_replace_file = self.before_replace_file
        files.on_before_delete_file = self.before_delete_file
    
    def get_count(self) -> int:
        return self.files.count
    
    def get_file_name(self, i: int) -> str:
        return self.files.get_name(i)
    
    def read_header(self, sender: TRSMMFiles, stream: BinaryIO, options: TRSMMFilesOptions, files_count: int):
        """Read header - must be overridden"""
        raise NotImplementedError
    
    def write_header(self, sender: TRSMMFiles, stream: BinaryIO):
        """Write header - must be overridden"""
        raise NotImplementedError
    
    def load(self, filename: str):
        """Load archive"""
        self.files.load(filename)
    
    def save_as(self, filename: str):
        """Save archive"""
        self.files.save_as(filename)
    
    def add(self, name: str, data: Union[BinaryIO, bytes, str], size: int = -1, pal: int = 0) -> int:
        """Add file to archive"""
        if isinstance(data, bytes):
            data = io.BytesIO(data)
        elif isinstance(data, str):
            # If it's a string, treat as filename
            if os.path.isfile(data):
                with open(data, 'rb') as f:
                    return self.files.add(os.path.basename(name) if name else os.path.basename(data), f, size)
            else:
                # Treat as string data
                data = io.BytesIO(data.encode('utf-8'))
        return self.files.add(name, data, size)
    
    def extract(self, index: int, output: Union[str, BinaryIO] = None, overwrite: bool = True) -> Union[str, io.BytesIO]:
        """Extract file"""
        if isinstance(output, str):
            # Extract to directory
            clean_name = self.get_extract_name(index).replace('\x00', '')  # Remove all null chars
            filename = os.path.join(output, clean_name)
            if not overwrite and os.path.exists(filename):
                return ""
            os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
            with open(filename, 'wb') as f:
                self.files.raw_extract(index, f)
            return filename
        elif output is not None:
            # Extract to stream
            self.files.raw_extract(index, output)
            return self.get_extract_name(index)
        else:
            # Extract to memory
            mem = io.BytesIO()
            self.files.raw_extract(index, mem)
            mem.seek(0, 0)
            return mem
    
    def extract_array_or_bmp(self, index: int) -> tuple:
        """Extract file as array or bitmap"""
        arr = self.extract_array(index)
        return arr, None
    
    def extract_array(self, index: int) -> bytes:
        """Extract file as bytes"""
        mem = io.BytesIO()
        self.files.raw_extract(index, mem)
        return mem.getvalue()
    
    def extract_string(self, index: int) -> str:
        """Extract file as string"""
        data = self.extract_array(index)
        return data.decode('utf-8', errors='ignore')
    
    def get_extract_name(self, index: int) -> str:
        """Get extraction filename"""
        return self.files.get_name(index).rstrip('\x00')
    
    def before_replace_file(self, sender: TRSMMFiles, index: int):
        """Called before replacing file"""
        if self.backup_on_add:
            self.backup_file(index, self.backup_on_add_overwrite)
    
    def before_delete_file(self, sender: TRSMMFiles, index: int):
        """Called before deleting file"""
        if self.backup_on_delete:
            self.backup_file(index, self.backup_on_delete_overwrite)
    
    def backup_file(self, index: int, overwrite: bool) -> bool:
        """Backup file"""
        try:
            old = self.files.ignore_unzip_errors
            self.files.ignore_unzip_errors = True
            self.do_backup_file(index, overwrite)
            self.files.ignore_unzip_errors = old
            return True
        except:
            return False
    
    def do_backup_file(self, index: int, overwrite: bool):
        """Perform backup"""
        backup_dir = self.make_backup_dir()
        self.extract(index, backup_dir, overwrite)
    
    def make_backup_dir(self) -> str:
        """Create backup directory"""
        backup_dir = self.files.out_file + ' Backup'
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir
    
    def compare_files(self, archive2: 'TRSMMArchive', name: str = None, index: int = None, index2: int = None) -> bool:
        """Compare files between archives"""
        if name:
            found1, idx1 = self.files.find_file(name)
            found2, idx2 = archive2.files.find_file(name)
            if not (found1 and found2):
                return False
            return self.compare_files(archive2, index=idx1, index2=idx2)
        
        # Compare by index
        size1 = self.files.get_size(index)
        size2 = archive2.files.get_size(index2)
        unp_size1 = 0
        unp_size2 = 0
        
        if self.files.get_is_packed(index):
            unp_size1 = self.files.get_unpacked_size(index)
        if archive2.files.get_is_packed(index2):
            unp_size2 = archive2.files.get_unpacked_size(index2)
        
        # Check sizes match
        if unp_size1 != 0:
            size1 = unp_size1
        if unp_size2 != 0:
            size2 = unp_size2
        if size1 != size2:
            return False
        
        stream1 = self.files.get_as_is_file_stream(index)
        stream2 = archive2.files.get_as_is_file_stream(index2)
        
        try:
            return self.do_compare_files(stream1, stream2, self.files.get_size(index), 
                                        unp_size1, archive2.files.get_size(index2), unp_size2,
                                        self.files.ignore_unzip_errors or archive2.files.ignore_unzip_errors)
        finally:
            self.files.free_as_is_file_stream(index, stream1)
            archive2.files.free_as_is_file_stream(index2, stream2)
    
    def do_compare_files(self, r: BinaryIO, r2: BinaryIO, size: int, unp_size: int, 
                        size2: int, unp_size2: int, ignore_unzip_errors: bool) -> bool:
        """Compare file streams"""
        # Raw compare first
        result = (size == size2) and (unp_size == unp_size2)
        if result:
            data1 = r.read(min(512, size))
            data2 = r2.read(min(512, size2))
            result = data1 == data2
            if result or unp_size == 0:
                return result
            r.seek(-len(data1), 1)
            r2.seek(-len(data2), 1)
        
        # Compare unpacked
        a = r
        a2 = r2
        if unp_size != 0:
            a = io.BytesIO(zlib.decompress(r.read(size)))
            size = unp_size
        if unp_size2 != 0:
            a2 = io.BytesIO(zlib.decompress(r2.read(size2)))
        
        try:
            data1 = a.read(size)
            data2 = a2.read(size)
            return data1 == data2
        except:
            if ignore_unzip_errors:
                return True
            return False
    
    def clone_for_processing(self, new_file: str, files_count: int = 0) -> 'TRSMMArchive':
        """Clone for processing"""
        result = type(self)()
        result._create_internal(self.files.clone_for_processing(new_file, files_count))
        return result
    
    @property
    def raw_files(self) -> TRSMMFiles:
        return self.files
