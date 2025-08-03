import hashlib

class FileUpload():
    def __init__(self, file_bytes, file_size:int):
        self.file = file_bytes
        self.file_size = file_size
        self.file_hash = None

    async def hash_file(self):
        try:
            hashed_file  = hashlib.sha256(self.file).hexdigest()
        except Exception as e:
            return None
        
        return hashed_file