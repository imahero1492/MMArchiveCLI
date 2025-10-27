"""RSLod Part 2 - TRSMMFiles class"""

from .RSLod import *


class TRSMMFiles:
    """Low-level LOD file manager"""
    
    def __init__(self):
        self.options = rs_mm_files_options_initialize()
        self.in_file = ""
        self.out_file = ""
        self.write_stream: Optional[BinaryIO] = None
        self.writes_count = 0
        self.block_stream: Optional[BinaryIO] = None
        self.file_time = 0
        
        self.block_in_file = False
        self.write_on_demand = False
        
        self.data = bytearray()
        self.count = 0
        self.file_size = 0
        self.file_buffers: List[Optional[io.BytesIO]] = []
        self.sorted = True
        self.games_lod = False
        
        self.user_data = bytearray()
        self.user_data_size = 0
        
        self.ignore_unzip_errors = False
        
        # Event handlers
        self.on_read_header: Optional[Callable] = None
        self.on_write_header: Optional[Callable] = None
        self.on_get_file_size: Optional[Callable] = None
        self.on_set_file_size: Optional[Callable] = None
        self.on_before_replace_file: Optional[Callable] = None
        self.on_before_delete_file: Optional[Callable] = None
        self.on_after_rename_file: Optional[Callable] = None
    
    def get_name(self, i: int) -> str:
        """Get file name at index"""
        offset = i * self.options.ItemSize
        name_bytes = self.data[offset:offset + self.options.NameSize]
        return name_bytes.rstrip(b'\x00').decode('ascii', errors='ignore')
    
    def get_address(self, i: int) -> int:
        """Get file address at index"""
        if i < self.count:
            offset = i * self.options.ItemSize + self.options.AddrOffset
            addr = struct.unpack('<I', self.data[offset:offset+4])[0]
            return addr + self.options.AddrStart
        return self.file_size
    
    def get_size(self, i: int) -> int:
        """Get file size at index"""
        if i < len(self.file_buffers) and self.file_buffers[i] is not None:
            return len(self.file_buffers[i].getvalue())
        
        result = 0
        if self.options.SizeOffset < 0:
            if result == 0 and self.options.PackedSizeOffset >= 0:
                offset = i * self.options.ItemSize + self.options.PackedSizeOffset
                result = struct.unpack('<i', self.data[offset:offset+4])[0]
            if result == 0 and self.options.UnpackedSizeOffset >= 0:
                offset = i * self.options.ItemSize + self.options.UnpackedSizeOffset
                result = struct.unpack('<i', self.data[offset:offset+4])[0]
        else:
            offset = i * self.options.ItemSize + self.options.SizeOffset
            result = struct.unpack('<i', self.data[offset:offset+4])[0]
        
        if self.on_get_file_size:
            result = self.on_get_file_size(self, i, result)
        
        return result
    
    def get_unpacked_size(self, i: int) -> int:
        """Get unpacked size at index"""
        if self.options.UnpackedSizeOffset < 0:
            return self.get_size(i)
        offset = i * self.options.ItemSize + self.options.UnpackedSizeOffset
        return struct.unpack('<i', self.data[offset:offset+4])[0]
    
    def get_is_packed(self, i: int) -> bool:
        """Check if file is packed"""
        if self.options.PackedSizeOffset >= 0:
            offset = i * self.options.ItemSize + self.options.PackedSizeOffset
            return struct.unpack('<i', self.data[offset:offset+4])[0] != 0
        elif self.options.SizeOffset >= 0 and self.options.UnpackedSizeOffset >= 0:
            off1 = i * self.options.ItemSize + self.options.SizeOffset
            off2 = i * self.options.ItemSize + self.options.UnpackedSizeOffset
            return struct.unpack('<i', self.data[off1:off1+4])[0] != struct.unpack('<i', self.data[off2:off2+4])[0]
        return False
    
    def get_user_data(self, i: int) -> bytearray:
        """Get user data at index"""
        offset = i * self.user_data_size
        return self.user_data[offset:offset + self.user_data_size]
    
    def check_name(self, name: str):
        """Check if name length is valid"""
        if len(name) >= self.options.NameSize:
            raise ERSLodWrongFileName(S_RS_LOD_LONG_NAME % (name, self.options.NameSize))
    
    def find_file(self, name: str) -> tuple:
        """Find file by name, returns (found, index)"""
        if not self.sorted:
            return self._find_file_linear(name)
        return self._find_file_bin_search(name, 0, self.count - 1)
    
    def _find_file_linear(self, name: str) -> tuple:
        """Linear search for unsorted archives"""
        best_same = 0
        best = 0
        best_c = 1
        
        for i in range(self.count):
            c, same = rs_lod_compare_str_with_count(name, self.get_name(i))
            if c == 0:
                return True, i
            elif same > best_same or (same == best_same and best_c > 0):
                best = i
                if c > 0:
                    best += 1
                best_same = same
                best_c = c
        
        return False, best
    
    def _find_file_bin_search(self, name: str, L: int, H: int) -> tuple:
        """Binary search for sorted archives"""
        while L <= H:
            i = (L + H) // 2
            c = rs_lod_compare_str(name, self.get_name(i))
            
            if c <= 0:
                if c == 0:
                    return True, i
                H = i - 1
            else:
                L = i + 1
        
        return False, L
    
    def load(self, filename: str):
        """Load LOD file"""
        self.close()
        self.in_file = filename
        self.out_file = filename
        self.read_header()
    
    def close(self):
        """Close and cleanup"""
        for buf in self.file_buffers:
            if buf:
                buf.close()
        self.file_buffers = []
        if self.block_stream:
            self.block_stream.close()
            self.block_stream = None
        self.count = 0
        self.options = rs_mm_files_options_initialize()
        self.data = bytearray()
        self.in_file = ""
        self.out_file = ""
        self.sorted = True
        self.user_data = bytearray()
    
    def read_header(self):
        """Read LOD header"""
        stream = self.begin_read()
        if self.block_in_file:
            self.block_stream = stream
        self.file_time = my_get_file_time(self.in_file)
        
        try:
            if self.on_read_header:
                self.on_read_header(self, stream, self.options, self.count)
            
            self.data = bytearray(self.count * self.options.ItemSize)
            self.user_data = bytearray(self.count * self.user_data_size)
            
            if self.count == 0:
                return
            
            stream.seek(self.options.DataStart, 0)
            data_read = stream.read(len(self.data))
            self.data[:len(data_read)] = data_read
        finally:
            self.end_read(stream)
        
        self.calculate_file_size()
        self.sorted = False
        for i in range(self.count - 1):
            if rs_lod_compare_str(self.get_name(i), self.get_name(i + 1)) > 0:
                return
        self.sorted = True
    
    def calculate_file_size(self):
        """Calculate total file size"""
        sz = max(self.options.DataStart, self.options.MinFileSize)
        for i in range(self.count):
            sz = max(sz, self.get_address(i) + self.get_size(i))
        self.file_size = sz
    
    def begin_read(self) -> BinaryIO:
        """Begin read operation"""
        if self.write_stream is None or self.in_file != self.out_file:
            return open(self.in_file, 'rb')
        return self.begin_write()
    
    def end_read(self, stream: BinaryIO):
        """End read operation"""
        if stream is not None:
            if stream == self.write_stream:
                self.end_write()
            elif stream != self.block_stream:
                stream.close()
    
    def begin_write(self) -> BinaryIO:
        """Begin write operation"""
        if self.write_stream is None:
            if self.block_stream and self.in_file == self.out_file:
                self.block_stream.close()
                self.block_stream = None
            self.write_stream = open(self.out_file, 'r+b')
        
        self.write_stream.seek(0, 0)
        self.writes_count += 1
        return self.write_stream
    
    def end_write(self):
        """End write operation"""
        self.writes_count -= 1
        if self.writes_count == 0:
            if self.write_stream:
                self.write_stream.close()
                self.write_stream = None
            if self.block_in_file and self.in_file == self.out_file and not self.block_stream:
                self.block_stream = self.begin_read()
        self.file_time = my_get_file_time(self.in_file)
    
    def raw_extract(self, i: int, output: BinaryIO):
        """Extract file without decompression"""
        stream = self.get_as_is_file_stream(i, True)
        try:
            if self.get_is_packed(i):
                if not self.ignore_unzip_errors:
                    data = stream.read(self.get_size(i))
                    decompressed = zlib.decompress(data)
                    output.write(decompressed)
                else:
                    from .RSLod import unzip_ignore_errors
                    unzip_ignore_errors(output, stream, self.get_unpacked_size(i), True)
            else:
                data = stream.read(self.get_size(i))
                output.write(data)
        finally:
            self.free_as_is_file_stream(i, stream)
    
    def get_as_is_file_stream(self, index: int, ignore_write: bool = False) -> BinaryIO:
        """Get file stream"""
        if index < len(self.file_buffers) and self.file_buffers[index]:
            self.file_buffers[index].seek(0, 0)
            return self.file_buffers[index]
        
        stream = self.begin_read()
        stream.seek(self.get_address(index), 0)
        
        if stream == self.write_stream and not ignore_write:
            mem_stream = io.BytesIO()
            data = stream.read(self.get_size(index))
            mem_stream.write(data)
            mem_stream.seek(0, 0)
            self.end_write()
            return mem_stream
        
        return stream
    
    def free_as_is_file_stream(self, index: int, stream: BinaryIO):
        """Free file stream"""
        if index >= len(self.file_buffers) or self.file_buffers[index] != stream:
            self.end_read(stream)
    
    def check_file_changed(self) -> bool:
        """Check if file was modified"""
        return self.file_time != my_get_file_time(self.in_file)
    
    def add(self, name: str, data: BinaryIO, size: int = -1, compression: int = 6, unpacked_size: int = -1) -> int:
        """Add file to archive"""
        self.check_name(name)
        if size < 0:
            start_pos = data.tell()
            end_pos = data.seek(0, 2)
            size = end_pos - start_pos
            data.seek(start_pos, 0)
        
        unp_size = size
        pk_size = 0
        new_data = None
        
        try:
            # Pack file
            if unpacked_size >= 0:
                unp_size = unpacked_size
                pk_size = size
            elif compression != 0 and size > 64 and (self.options.PackedSizeOffset >= 0 or self.options.UnpackedSizeOffset >= 0):
                new_data = io.BytesIO()
                compressed = zlib.compress(data.read(size), compression)
                new_data.write(compressed)
                compressed_size = new_data.tell()
                if compressed_size < size:
                    pk_size = compressed_size
                    data = new_data
                    data.seek(0, 0)
                    size = pk_size
                else:
                    data.seek(-size, 1)
            
            # Find insert index
            found, result = self.find_add_index(name)
            if found and self.on_before_replace_file:
                self.on_before_replace_file(self, result)
            
            stream = self.begin_write()
            try:
                if found:
                    if self.can_expand(result, size):
                        self.do_write_file(result, data, size, self.get_address(result))
                    else:
                        self.do_write_file(result, data, size, self.file_size)
                    self.user_data[result*self.user_data_size:(result+1)*self.user_data_size] = bytearray(self.user_data_size)
                else:
                    addr = self.options.DataStart + (self.count + 1) * self.options.ItemSize
                    for i in range(self.count):
                        if self.get_address(i) < addr:
                            self.do_move_file(i, self.file_size)
                    
                    self.count += 1
                    self.insert_data(result)
                    self.file_buffers.insert(result, None)
                    self.file_size = max(self.file_size, self.options.DataStart + len(self.data))
                    self.do_write_file(result, data, size, self.file_size)
                
                i = result
                offset = i * self.options.ItemSize
                self.data[offset:offset+self.options.NameSize] = bytearray(self.options.NameSize)
                if name:
                    name_bytes = name.encode('ascii')[:self.options.NameSize]
                    self.data[offset:offset+len(name_bytes)] = name_bytes
                
                if self.options.SizeOffset >= 0:
                    struct.pack_into('<i', self.data, offset + self.options.SizeOffset, size)
                if self.options.UnpackedSizeOffset >= 0:
                    struct.pack_into('<i', self.data, offset + self.options.UnpackedSizeOffset, unp_size)
                if self.options.PackedSizeOffset >= 0:
                    struct.pack_into('<i', self.data, offset + self.options.PackedSizeOffset, pk_size)
                if self.on_set_file_size:
                    self.on_set_file_size(self, i, size)
                
                if not self.write_on_demand:
                    self.write_header()
            finally:
                self.end_write()
            
            return result
        finally:
            if new_data:
                new_data.close()
    
    def delete(self, i: Union[int, str]):
        """Delete file at index or by name"""
        if isinstance(i, str):
            found, idx = self.find_file(i)
            if found:
                self.do_delete(idx)
        else:
            self.do_delete(i)
    
    def do_delete(self, i: int, no_write: bool = False):
        """Internal delete"""
        if self.on_before_delete_file:
            self.on_before_delete_file(self, i)
        
        self.count -= 1
        self.remove_data(i)
        
        if i < len(self.file_buffers):
            if self.file_buffers[i]:
                self.file_buffers[i].close()
            del self.file_buffers[i]
        
        if not no_write and not self.write_on_demand:
            self.write_header()
    
    def rename(self, index: int, new_name: str) -> int:
        """Rename file"""
        self.check_name(new_name)
        locked = not self.write_on_demand
        if locked:
            self.begin_write()
        
        try:
            found, result = self.find_file(new_name)
            if found:
                if result == index:
                    return result
                else:
                    self.do_delete(result, True)
            
            # Remove from current position
            item_data = self.data[index*self.options.ItemSize:(index+1)*self.options.ItemSize]
            user_data = self.user_data[index*self.user_data_size:(index+1)*self.user_data_size]
            file_buf = self.file_buffers[index] if index < len(self.file_buffers) else None
            
            self.data[index*self.options.ItemSize:(index+1)*self.options.ItemSize] = self.data[-self.options.ItemSize:]
            self.user_data[index*self.user_data_size:(index+1)*self.user_data_size] = self.user_data[-self.user_data_size:]
            if index < len(self.file_buffers):
                del self.file_buffers[index]
            self.count -= 1
            
            # Find new position
            found, result = self.find_add_index(new_name)
            assert not found
            self.count += 1
            
            # Insert at new position
            self.data[result*self.options.ItemSize:result*self.options.ItemSize] = item_data
            self.user_data[result*self.user_data_size:result*self.user_data_size] = user_data
            if file_buf:
                self.file_buffers.insert(result, file_buf)
            
            # Write new name
            offset = result * self.options.ItemSize
            self.data[offset:offset+self.options.NameSize] = bytearray(self.options.NameSize)
            if new_name:
                name_bytes = new_name.encode('ascii')[:self.options.NameSize]
                self.data[offset:offset+len(name_bytes)] = name_bytes
            
            if not self.write_on_demand:
                self.write_header()
        finally:
            if locked:
                self.end_write()
        
        if self.on_after_rename_file:
            self.on_after_rename_file(self, result)
        
        return result
    
    def save(self):
        """Save if needed"""
        if self.file_buffers:
            self.do_save()
    
    def do_save(self):
        """Force save"""
        stream = self.begin_write()
        try:
            for i, buf in enumerate(self.file_buffers):
                if buf:
                    buf.seek(0, 0)
                    self.do_write_file(i, buf, buf.seek(0, 2), self.get_address(i), True)
                    buf.close()
            self.file_buffers = []
            self.write_header()
        finally:
            self.end_write()
    
    def save_as(self, filename: str):
        """Save as new file"""
        assert self.write_stream is None
        self.out_file = filename
        old_size = self.file_size
        self.file_size = max(self.options.MinFileSize, self.options.DataStart + len(self.data))
        old_data = bytearray(self.data)
        
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        self.write_stream = open(filename, 'wb')
        self.writes_count += 1
        ok = False
        
        try:
            for i in range(self.count):
                stream = self.get_as_is_file_stream(i)
                try:
                    self.do_write_file(i, stream, self.get_size(i), self.file_size, True)
                finally:
                    self.free_as_is_file_stream(i, stream)
            ok = True
            self.write_header()
        finally:
            self.end_write()
            if not ok:
                self.data = old_data
                self.file_size = old_size
        
        for buf in self.file_buffers:
            if buf:
                buf.close()
        self.file_buffers = []
        if self.block_stream:
            self.block_stream.close()
            self.block_stream = None
        self.in_file = self.out_file
        self.file_time = my_get_file_time(self.in_file)
    
    def new(self, filename: str, options: TRSMMFilesOptions):
        """Create new archive"""
        self.close()
        self.options = options
        self.in_file = filename
        self.out_file = filename
        self.file_size = max(options.DataStart, options.MinFileSize)
        self.file_time = my_get_file_time(self.in_file)
        self.do_save()
    
    def rebuild(self):
        """Rebuild archive (defragment)"""
        name = self.out_file
        s = name + '.tmp'
        import random
        while os.path.exists(s):
            s = name + '.' + format(random.randint(0, 0xFFF), '03X')
        try:
            self.save_as_no_block(s)
            if os.path.exists(name):
                os.remove(name)
            os.rename(s, name)
        finally:
            if os.path.exists(name):
                if os.path.exists(s):
                    os.remove(s)
            else:
                name = s
            self.out_file = name
            self.in_file = name
            self.file_time = my_get_file_time(self.in_file)
        if self.block_in_file:
            self.block_stream = self.begin_read()
    
    def save_as_no_block(self, filename: str):
        """Save without blocking"""
        assert self.write_stream is None
        self.out_file = filename
        old_size = self.file_size
        self.file_size = max(self.options.MinFileSize, self.options.DataStart + len(self.data))
        old_data = bytearray(self.data)
        
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        self.write_stream = open(filename, 'wb')
        self.writes_count += 1
        ok = False
        
        try:
            for i in range(self.count):
                stream = self.get_as_is_file_stream(i)
                try:
                    self.do_write_file(i, stream, self.get_size(i), self.file_size, True)
                finally:
                    self.free_as_is_file_stream(i, stream)
            ok = True
            self.write_header()
        finally:
            self.end_write()
            if not ok:
                self.data = old_data
                self.file_size = old_size
        
        for buf in self.file_buffers:
            if buf:
                buf.close()
        self.file_buffers = []
        if self.block_stream:
            self.block_stream.close()
            self.block_stream = None
        self.in_file = self.out_file
        self.file_time = my_get_file_time(self.in_file)
    
    def merge_to(self, files: 'TRSMMFiles'):
        """Merge this archive into another"""
        files.begin_write()
        try:
            for i in range(self.count):
                stream = self.get_as_is_file_stream(i)
                try:
                    if self.get_is_packed(i):
                        files.add(self.get_name(i), stream, self.get_size(i), 0, self.get_unpacked_size(i))
                    else:
                        files.add(self.get_name(i), stream, self.get_size(i), 0)
                finally:
                    self.free_as_is_file_stream(i, stream)
        finally:
            files.end_write()
    
    def clone_for_processing(self, new_file: str, files_count: int) -> 'TRSMMFiles':
        """Clone for processing"""
        result = TRSMMFiles()
        result.options = self.options
        result.in_file = new_file
        result.out_file = new_file
        result.user_data_size = self.user_data_size
        result.file_size = max(self.options.DataStart + files_count * self.options.ItemSize, self.options.MinFileSize)
        result.games_lod = self.games_lod
        result.sorted = self.sorted
        result.file_time = my_get_file_time(result.in_file)
        return result
    
    def reserve_files_count(self, n: int):
        """Reserve space for n files"""
        self.file_size = max(self.file_size, self.options.DataStart + n * self.options.ItemSize)
    
    def assign_stream(self, stream: BinaryIO):
        """Assign external stream"""
        self.write_stream = stream
        self.writes_count += 1
    
    def write_header(self):
        """Write header"""
        stream = self.begin_write()
        try:
            sz = self.options.DataStart + len(self.data)
            for i in range(self.count):
                addr = self.get_address(i) + self.get_size(i)
                if addr > sz:
                    sz = addr
            self.file_size = sz
            
            if stream.seek(0, 2) != sz:
                stream.seek(0, 0)
                stream.truncate(sz)
                stream.seek(0, 0)
            
            if self.on_write_header:
                self.on_write_header(self, stream)
            
            if self.count == 0:
                return
            stream.seek(self.options.DataStart, 0)
            stream.write(self.data)
        finally:
            self.end_write()
    
    def do_write_file(self, index: int, data: BinaryIO, size: int, addr: int, force_write: bool = False):
        """Write file data"""
        if self.write_on_demand and not force_write:
            if index >= len(self.file_buffers):
                self.file_buffers.extend([None] * (index + 1 - len(self.file_buffers)))
            if data != self.file_buffers[index]:
                if self.file_buffers[index]:
                    self.file_buffers[index].close()
                self.file_buffers[index] = io.BytesIO()
                self.file_buffers[index].write(data.read(size))
        else:
            stream = self.begin_write()
            try:
                # Ensure file is large enough before writing
                current_size = stream.seek(0, 2)
                if addr + size > current_size:
                    stream.truncate(addr + size)
                stream.seek(addr, 0)
                stream.write(data.read(size))
            finally:
                self.end_write()
        
        offset = index * self.options.ItemSize + self.options.AddrOffset
        struct.pack_into('<I', self.data, offset, addr - self.options.AddrStart)
        addr += size
        if addr > self.file_size:
            self.file_size = addr
    
    def do_move_file(self, index: int, addr: int):
        """Move file to new address"""
        if index < len(self.file_buffers) and self.file_buffers[index]:
            self.file_buffers[index].seek(0, 0)
            self.do_write_file(index, self.file_buffers[index], self.file_buffers[index].seek(0, 2), addr)
            return
        
        stream = self.get_as_is_file_stream(index)
        try:
            self.do_write_file(index, stream, self.get_size(index), addr)
        finally:
            self.free_as_is_file_stream(index, stream)
    
    def can_expand(self, index: int, new_size: int) -> bool:
        """Check if file can expand in place"""
        addr = self.get_address(index)
        sz = self.get_size(index)
        if new_size <= sz or addr + sz >= self.file_size:
            return True
        
        if index + 1 < self.count:
            next_addr = self.get_address(index + 1)
            if next_addr >= addr and next_addr - addr >= new_size:
                return True
            return False
        
        for i in range(self.count):
            other_addr = self.get_address(i)
            if other_addr >= addr and other_addr - addr < new_size:
                return False
        return True
    
    def insert_data(self, index: int):
        """Insert data slot"""
        item_size = self.options.ItemSize
        self.data[len(self.data):len(self.data)] = bytearray(item_size)
        if index * item_size < len(self.data) - item_size:
            self.data[index*item_size+item_size:] = self.data[index*item_size:-item_size]
            self.data[index*item_size:(index+1)*item_size] = bytearray(item_size)
        
        self.user_data[len(self.user_data):len(self.user_data)] = bytearray(self.user_data_size)
        if index * self.user_data_size < len(self.user_data) - self.user_data_size:
            self.user_data[index*self.user_data_size+self.user_data_size:] = self.user_data[index*self.user_data_size:-self.user_data_size]
            self.user_data[index*self.user_data_size:(index+1)*self.user_data_size] = bytearray(self.user_data_size)
    
    def remove_data(self, index: int):
        """Remove data slot"""
        item_size = self.options.ItemSize
        self.data[index*item_size:(index+1)*item_size] = self.data[-item_size:]
        self.data = self.data[:-item_size]
        
        self.user_data[index*self.user_data_size:(index+1)*self.user_data_size] = self.user_data[-self.user_data_size:]
        self.user_data = self.user_data[:-self.user_data_size]
    
    def find_add_index(self, name: str) -> tuple:
        """Find index for adding file"""
        found, index = self.find_file(name)
        if not found and self.games_lod:
            i = self.count - 1
            while i >= 0 and not self.is_blv_or_odm(self.get_name(i)):
                i -= 1
            if not self.is_blv_or_odm(name):
                found, index = self._find_file_bin_search(name, i + 1, self.count - 1)
            else:
                index = i + 1
        return found, index
    
    def is_blv_or_odm(self, name: str) -> bool:
        """Check if file is blv or odm"""
        ext = os.path.splitext(name)[1].lower()
        return ext in ['.blv', '.odm']
    
    def set_user_data_size(self, v: int):
        """Set user data size"""
        if v == self.user_data_size:
            return
        assert v <= 2048
        self.user_data = bytearray()
        self.user_data_size = v
        self.user_data = bytearray(self.user_data_size * self.count)
    
    def set_write_on_demand(self, v: bool):
        """Set write on demand mode"""
        if self.write_on_demand == v:
            return
        if not v:
            self.save()
        self.write_on_demand = v
    
    @property
    def file_name(self) -> str:
        """Get filename"""
        return self.out_file
    
    @property
    def archive_size(self) -> int:
        """Get archive size"""
        return self.file_size
