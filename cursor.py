"""Pinned Kitty cursor download; archive data is never executed."""
import hashlib
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request
import xml.etree.ElementTree as ET

API = 'https://api.opendesktop.org/ocs/v1/content/download/2275753/1'
SHA256 = 'd1f934f99ab78c1bb5ef30b74c35929d061e3b1747a02c833998a0683008d74b'
MAX_DOWNLOAD = 4 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024


def fetch(url, limit):
    if not url.startswith('https://'):
        raise ValueError('Cursor downloads require HTTPS.')
    with urllib.request.urlopen(url, timeout=30) as response:
        if not response.geturl().startswith('https://'):
            raise ValueError('Insecure cursor download redirect.')
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Cursor download exceeds size limit.')
    return data


def download(destination):
    metadata = ET.fromstring(fetch(API, 128 * 1024))
    link = metadata.findtext('.//downloadlink')
    if not link:
        raise ValueError('The cursor source did not return a download link.')
    data = fetch(link, MAX_DOWNLOAD)
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('Kitty download changed: checksum mismatch. Nothing installed; review the new release first.')
    destination.write_bytes(data)


def unpack(archive, staging):
    """Validate all entries before writing, never using extractall."""
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        if len(members) > 256 or sum(m.size for m in members) > MAX_EXPANDED:
            raise ValueError('Cursor archive exceeds limits.')
        names = set()
        for member in members:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or '..' in path.parts or not path.parts
                    or path.parts[0] != 'Kitty' or member.name in names
                    or not (member.isdir() or member.isfile())):
                raise ValueError('Unsafe cursor archive entry: ' + member.name)
            names.add(member.name)
        if 'Kitty/index.theme' not in names or 'Kitty/cursors/left_ptr' not in names:
            raise ValueError('Incomplete Kitty cursor archive.')
        result = []
        for member in members:
            if not member.isfile():
                continue
            # Only install theme metadata and actual cursors, not previews.
            relative = PurePosixPath(member.name)
            if str(relative) != 'Kitty/index.theme' and relative.parts[1:2] != ('cursors',):
                continue
            target = staging / Path(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.extractfile(member) as source:
                target.write_bytes(source.read())
            target.chmod(0o644)
            result.append((target, Path.home() / '.icons' / Path(*relative.parts)))
    return result
