import json
import hashlib
import struct
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'bin/meko'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.blue = self.root / 'Instances/Blue'
        for d in ['KSP.app/Contents/MacOS', 'GameData/Squad', 'saves/Campaign', 'CKAN']:
            (self.blue / d).mkdir(parents=True, exist_ok=True)
        (self.blue / 'KSP.app/Contents/MacOS/KSP').write_text('game')
        (self.blue / 'GameData/Squad/stock.cfg').write_text('stock')
        (self.blue / 'saves/Campaign/persistent.sfs').write_text('original save')
        (self.blue / 'readme.txt').write_text('Version 1.12.5\n')
        (self.blue / 'buildID.txt').write_text('build id = 03190\n')
        self.config = self.root / 'instances.local.json'
        self.save_config({'Blue': {'path': 'Instances/Blue', 'role': 'playable'}})

    def save_config(self, instances):
        self.config.write_text(json.dumps({'instances': instances}))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(CLI), '--config', str(self.config), *args], text=True, capture_output=True)

    def ok(self, *args):
        r = self.run_cli(*args)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def test_clone_preserves_saves_and_isolates_writes(self):
        self.ok('clone', 'Blue', 'Green')
        green = self.root / 'Instances/Green'
        target = green / 'saves/Campaign/persistent.sfs'
        self.assertEqual(target.read_text(), 'original save')
        self.assertNotEqual(target.stat().st_ino, (self.blue / 'saves/Campaign/persistent.sfs').stat().st_ino)
        target.write_text('changed')
        self.assertEqual((self.blue / 'saves/Campaign/persistent.sfs').read_text(), 'original save')
        self.assertEqual(os.readlink(green / 'KSP_x64.exe'), 'KSP.app/Contents/MacOS/KSP')
        self.assertEqual(json.loads(self.config.read_text())['instances']['Green']['role'], 'playable')

    def test_clone_refuses_existing_destination_and_live_registry(self):
        (self.root / 'Instances/Green').mkdir()
        r = self.run_cli('clone', 'Blue', 'Green')
        self.assertIn('already exists', r.stderr)
        (self.root / 'Instances/Green').rmdir()
        (self.blue / 'CKAN/registry.locked').write_text('123')
        r = self.run_cli('clone', 'Blue', 'Green')
        self.assertIn('Close CKAN', r.stderr)
        self.assertFalse((self.root / 'Instances/Green').exists())

    def test_clone_rejects_external_links(self):
        (self.blue / 'GameData/external').symlink_to(self.root)
        r = self.run_cli('clone', 'Blue', 'Green')
        self.assertIn('external symlink', r.stderr)
        self.assertFalse((self.root / 'Instances/Green').exists())

    def test_reference_cannot_be_registered_or_selected(self):
        self.save_config({'Core': {'path': 'Instances/Blue', 'role': 'reference'}})
        for action in ['register', 'select', 'launch']:
            r = self.run_cli(action, 'Core')
            self.assertIn('reference', r.stderr)
            self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.blue / 'KSP_x64.exe').exists())

    def registry(self, version='1.0', dependency=True):
        modules = {'Example': {'source_module': {'identifier': 'Example', 'name': 'Example', 'version': version, 'download_hash': {'sha256': 'a' * 64}}, 'auto_installed': False}}
        if dependency:
            modules['Dependency'] = {'source_module': {'identifier': 'Dependency', 'name': 'Dependency', 'version': '2.0'}, 'auto_installed': True}
        (self.blue / 'CKAN/registry.json').write_text(json.dumps({'installed_modules': modules}))

    def test_snapshot_pins_dependencies_and_records_unmanaged_files(self):
        self.registry()
        (self.blue / 'GameData/manual.cfg').write_text('manual config')
        self.ok('snapshot', 'Blue', 'record')
        record = self.root / 'record'
        exact = json.loads((record / 'exact.ckan').read_text())
        self.assertEqual(exact['depends'], [{'name': 'Dependency', 'version': '2.0'}, {'name': 'Example', 'version': '1.0'}])
        selection = json.loads((record / 'selection.ckan').read_text())
        self.assertEqual(selection['depends'], [{'name': 'Example'}])
        state = json.loads((record / 'state.json').read_text())
        self.assertIn('GameData/manual.cfg', state['files'])
        self.assertFalse(any('saves/' in x for x in state['files']))
        self.assertEqual(state['game']['version'], '1.12.5')
        self.assertEqual(state['game']['build'], '03190')
        self.assertNotIn(str(self.root), (record / 'state.json').read_text())
        r = self.run_cli('snapshot', 'Blue', 'record')
        self.assertIn('already exists', r.stderr)

    def test_diff_shows_upgrades_removals_and_file_changes(self):
        self.registry()
        self.ok('snapshot', 'Blue', 'before')
        self.registry('1.1', dependency=False)
        (self.blue / 'GameData/Squad/stock.cfg').write_text('changed stock')
        self.ok('snapshot', 'Blue', 'after')
        diff = json.loads(self.ok('compare', 'before', 'after').stdout)
        self.assertEqual(diff['mods']['removed'], ['Dependency'])
        self.assertEqual(diff['mods']['changed'], {'Example': ['1.0', '1.1']})
        self.assertIn('GameData/Squad/stock.cfg', diff['files']['changed'])

    def test_readonly_reference_clone_is_writable_and_reference_unchanged(self):
        f = self.blue / 'GameData/Squad/stock.cfg'
        f.chmod(0o444)
        self.save_config({'Core': {'path': 'Instances/Blue', 'role': 'reference'}})
        self.ok('clone', 'Core', 'Base', '--role', 'template')
        target = self.root / 'Instances/Base/GameData/Squad/stock.cfg'
        self.assertTrue(target.stat().st_mode & 0o200)
        self.assertFalse(f.stat().st_mode & 0o200)
        target.write_text('base')
        self.assertEqual(f.read_text(), 'stock')

    def test_core_uses_manifest_files_and_checks_hashes(self):
        steamapps = self.root / 'Steam/steamapps'
        steam = steamapps / 'common/Kerbal Space Program'
        steam.parent.mkdir(parents=True)
        import shutil
        shutil.copytree(self.blue, steam)
        cache = steamapps.parent / 'depotcache'
        cache.mkdir()
        (steamapps / 'appmanifest_220200.acf').write_text('"AppState" { "StateFlags" "4" "buildid" "123" "InstalledDepots" { "220202" { "manifest" "456" } } }')

        def varint(n):
            result = bytearray()
            while n >= 128:
                result.append((n & 127) | 128)
                n >>= 7
            return bytes(result + bytes([n]))

        def field(n, value):
            return varint(n * 8 + 2) + varint(len(value)) + value

        payload = b''
        for relative in ['KSP.app/Contents/MacOS/KSP', 'GameData/Squad/stock.cfg', 'readme.txt', 'buildID.txt']:
            content = (steam / relative).read_bytes()
            row = field(1, relative.encode()) + b'\x10' + varint(len(content)) + field(5, hashlib.sha1(content).digest())
            payload += field(1, row)
        (cache / '220202_456.manifest').write_bytes(struct.pack('<II', 0x71F617D0, len(payload)) + payload)
        self.ok('core', str(steam), 'Core')
        core = self.root / 'Instances/Core'
        self.assertFalse((core / 'saves/Campaign').exists())
        self.assertFalse((core / 'KSP_x64.exe').exists())
        self.assertEqual((core / 'GameData/Squad/stock.cfg').read_text(), 'stock')
        self.assertFalse((core / 'GameData/Squad/stock.cfg').stat().st_mode & 0o200)
        self.assertEqual(json.loads(self.config.read_text())['instances']['Core']['role'], 'reference')
        self.assertTrue((steam / 'GameData/Squad/stock.cfg').stat().st_mode & 0o200)
        (steam / 'GameData/Squad/stock.cfg').write_text('corruption')
        r = self.run_cli('core', str(steam), 'BadCore')
        self.assertIn('hash mismatch', r.stderr)
        self.assertFalse((self.root / 'Instances/BadCore').exists())
        for item in core.rglob('*'):
            if not item.is_symlink():
                item.chmod(item.stat().st_mode | 0o700)
        core.chmod(0o755)

    def test_flags_are_copied_without_overwriting_or_touching_core(self):
        assets = self.root / 'assets'
        assets.mkdir()
        flag = b'\x89PNG\r\n\x1a\n' + b'\x00' * 8 + struct.pack('>II', 256, 160)
        (assets / 'flag.png').write_bytes(flag)
        self.ok('flags', 'Blue', str(assets))
        target = self.blue / 'GameData/Meko/Flags/flag.png'
        self.assertEqual(target.read_bytes(), flag)
        self.assertFalse(target.is_symlink())
        self.ok('flags', 'Blue', str(assets))
        (assets / 'flag.png').write_bytes(flag + b'different')
        r = self.run_cli('flags', 'Blue', str(assets))
        self.assertIn('different', r.stderr)
        self.assertEqual(target.read_bytes(), flag)
        self.save_config({'Core': {'path': 'Instances/Blue', 'role': 'reference'}})
        r = self.run_cli('flags', 'Core', str(assets))
        self.assertIn('reference', r.stderr)

    def test_select_refuses_gui_even_without_registry_lock(self):
        from unittest.mock import patch
        tools = self.root / 'tools'
        tools.mkdir()
        ps = tools / 'ps'
        ps.write_text("#!/bin/sh\nprintf '%s\\n' 'Y:\\Library\\CKAN-GUI\\ckan.exe gui --asroot'\n")
        ps.chmod(0o755)
        with patch.dict(os.environ, {'PATH': str(tools) + os.pathsep + os.environ['PATH']}):
            r = self.run_cli('select', 'Blue')
        self.assertIn('Close CKAN', r.stderr)

    def test_invalid_name_cannot_escape_instances(self):
        r = self.run_cli('clone', 'Blue', '../escape')
        self.assertIn('name', r.stderr)
        self.assertFalse((self.root / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
