"""Read and update Electron ASAR resources without executing their contents."""
from pathlib import Path
import copy
import hashlib
import json
import struct

BLOCK_SIZE = 4 * 1024 * 1024

class Archive:
    def __init__(self, path):
        self.path = Path(path)
        with self.path.open('rb') as handle:
            prefix = handle.read(16)
            values = struct.unpack('<4I', prefix)
            self.base = 8 + values[1]
            self.header = json.loads(handle.read(values[3]))
        self.entries = dict(self.walk(self.header))

    @staticmethod
    def walk(node, prefix=''):
        for name, entry in node.get('files', {}).items():
            path = prefix + '/' + name
            if 'files' in entry:
                yield from Archive.walk(entry, path)
            else:
                yield path, entry

    def read(self, name):
        entry = self.entries[name]
        if entry.get('unpacked') or 'link' in entry:
            raise ValueError('Not an ordinary packed file: ' + name)
        with self.path.open('rb') as handle:
            handle.seek(self.base + int(entry['offset']))
            result = handle.read(entry['size'])
        if len(result) != entry['size']:
            raise ValueError('Truncated file: ' + name)
        return result

    def json(self, name):
        return json.loads(self.read(name))

    def patch(self, output, replacements):
        output = Path(output)
        if output.resolve() == self.path.resolve() or output.exists():
            raise ValueError('Output must be a new file')
        header = copy.deepcopy(self.header)
        for path in replacements:
            parts = path.strip('/').split('/')
            node = header
            for name in parts[:-1]:
                node = node.setdefault('files', {}).setdefault(name, {'files': {}})
            node.setdefault('files', {}).setdefault(parts[-1], {'size': 0, 'offset': '0'})
        offset = 0
        ordered = []
        for path, entry in self.walk(header):
            if entry.get('unpacked') or 'link' in entry:
                continue
            data = replacements.get(path)
            if data is not None:
                if isinstance(data, str):
                    data = data.encode('utf-8')
                entry['size'] = len(data)
                entry['integrity'] = {
                    'algorithm': 'SHA256',
                    'hash': hashlib.sha256(data).hexdigest(),
                    'blockSize': BLOCK_SIZE,
                    'blocks': [hashlib.sha256(data[i:i + BLOCK_SIZE]).hexdigest()
                               for i in range(0, len(data), BLOCK_SIZE)],
                }
            entry['offset'] = str(offset)
            offset += entry['size']
            ordered.append((path, entry, data))
        raw = json.dumps(header, separators=(',', ':'), ensure_ascii=False).encode()
        padded = (len(raw) + 3) & ~3
        pickle_header = struct.pack('<II', 4 + padded, len(raw)) + raw + b'\0' * (padded - len(raw))
        with output.open('xb') as handle:
            handle.write(struct.pack('<II', 4, len(pickle_header)))
            handle.write(pickle_header)
            for path, entry, data in ordered:
                handle.write(self.read(path) if data is None else data)
        result = Archive(output)
        assert set(result.entries) == set(dict(self.walk(header)))
        for path, entry, data in ordered:
            actual = result.read(path)
            assert len(actual) == entry['size'], path
            if data is not None:
                assert actual == data, path
            else:
                assert actual == self.read(path), path
        return output
