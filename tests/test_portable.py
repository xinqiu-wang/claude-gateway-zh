import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PortableToolTests(unittest.TestCase):
    def test_launcher_resolves_symlink_from_another_directory_with_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            checkout = base / 'another user checkout'
            checkout.mkdir()
            shutil.copy2(ROOT / 'claude-zh', checkout / 'claude-zh')
            (checkout / 'inject.py').write_text('import sys; print("resolved:" + sys.argv[1])\n')
            link = base / 'bin' / 'claude-zh'
            link.parent.mkdir()
            link.symlink_to(checkout / 'claude-zh')
            result = subprocess.run(['bash', str(link), 'status'], cwd='/', capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), 'resolved:status')

    def test_asar_patch_keeps_unmodified_bytes_and_adds_language(self):
        asar = load('asar_tools')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = {'files': {'sample.txt': {'size': 5, 'offset': '0'}}}
            raw = json.dumps(header, separators=(',', ':')).encode()
            padded = (len(raw) + 3) & ~3
            pickle_header = struct.pack('<II', 4 + padded, len(raw)) + raw + b'\0' * (padded - len(raw))
            source = root / 'sample.asar'
            source.write_bytes(struct.pack('<II', 4, len(pickle_header)) + pickle_header + b'hello')
            archive = asar.Archive(source)
            output = root / 'patched.asar'
            translated = '{"title":"设置"}'.encode()
            archive.patch(output, {'/i18n/zh-Hans.json': translated})
            result = asar.Archive(output)
            self.assertEqual(result.read('/sample.txt'), b'hello')
            self.assertEqual(result.read('/i18n/zh-Hans.json'), translated)
            with self.assertRaises(ValueError):
                archive.patch(source, {})

    def test_unknown_runtime_layout_stops_before_output(self):
        runtime = load('runtime_patch')
        class UnknownArchive:
            entries = {'/assets/new.js': {}}
            def read(self, path):
                return b'export const changedLayout=true;'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, '无法唯一识别'):
                runtime.apply({'ion-dist.asar': UnknownArchive()}, {}, {}, Path(tmp))
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
