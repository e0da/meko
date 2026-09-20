"""Read installed Steam depot file lists; no network or account credentials.

Wire fields follow ValvePython/steam protobufs/content_manifest.proto.
"""
from pathlib import PurePosixPath
import re
import struct


def vdf(text):
    tokens = iter(re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"|([{}])', text))

    def block():
        result = {}
        for key, marker in tokens:
            if marker == '}':
                return result
            value, marker = next(tokens)
            result[key] = block() if marker == '{' else value
        return result

    return block()


def fields(data):
    offset = 0

    def number():
        nonlocal offset
        value = 0
        for shift in range(0, 70, 7):
            byte = data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError('Invalid protobuf varint')

    while offset < len(data):
        tag = number()
        kind = tag & 7
        if kind == 0:
            value = number()
        elif kind in (1, 2, 5):
            size = number() if kind == 2 else (8 if kind == 1 else 4)
            value = data[offset:offset + size]
            if len(value) != size:
                raise ValueError('Truncated Steam manifest')
            offset += size
        else:
            raise ValueError('Unsupported protobuf field')
        yield tag >> 3, value


def manifest_files(path):
    data = path.read_bytes()
    magic, size = struct.unpack_from('<II', data)
    if magic != 0x71F617D0 or len(data) < 8 + size:
        raise ValueError(f'Unsupported or truncated Steam manifest: {path.name}')
    for number, mapping in fields(data[8:8 + size]):
        if number != 1:
            continue
        entry = dict(fields(mapping))
        name = entry[1].decode().rstrip('\0').replace('\\', '/')
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('Unsafe path in Steam manifest')
        yield name, entry.get(5, b'').hex(), entry.get(2, 0), entry.get(3, 0), entry.get(7, b'').decode()


def installed_files(steam):
    steamapps = steam.parent.parent
    app = vdf((steamapps / 'appmanifest_220200.acf').read_text())['AppState']
    if app.get('StateFlags') != '4':
        raise ValueError('Steam installation is not fully installed and idle; finish verification first.')
    depots = app['InstalledDepots']
    files = {}
    for depot, info in depots.items():
        manifest = steamapps.parent / 'depotcache' / f'{depot}_{info["manifest"]}.manifest'
        for name, sha1, size, flags, link in manifest_files(manifest):
            value = {'sha1': sha1, 'size': size, 'flags': flags, 'link': link}
            if name in files and files[name] != value:
                raise ValueError(f'Conflicting depot entries for {name}')
            files[name] = value
    return files, {'appid': '220200', 'buildid': app['buildid'],
                   'depots': {key: value['manifest'] for key, value in depots.items()}}
