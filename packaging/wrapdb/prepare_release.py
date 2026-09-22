#!/usr/bin/env python3
"""Prepare the WrapDB submission metadata for an EUI-NEO release.

Downloads the release tarball, verifies that the archive is actually
submittable, computes its SHA-256, writes the wrap file that belongs in the
wrapdb repository (subprojects/eui-neo.wrap), and prints the releases.json and
ci_config.json snippets.

Usage:
    python packaging/wrapdb/prepare_release.py --version 0.6.1
    python packaging/wrapdb/prepare_release.py --version 0.6.1 --write
    python packaging/wrapdb/prepare_release.py v0.6.1 --write

The version must match `project(version:)` in meson.build and the tag name
(`v<version>`), because WrapDB checks both. The archive must already contain
meson.build, meson_options.txt, and subprojects/*.wrap; otherwise submit with a
`patch_directory` instead, as packaging/wrapdb/README.md describes.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import urllib.request

DEFAULT_REPO = 'sudoevolve/EUI-NEO'
DEFAULT_WRAP_DIR = 'packaging/wrapdb'
WRAP_NAME = 'eui-neo'
REQUIRED_FILES = ('meson.build', 'meson_options.txt', 'meson/copy_assets.py')
REQUIRED_WRAPS = ('glfw.wrap', 'freetype2.wrap', 'libpng.wrap', 'zlib.wrap', 'curl.wrap')

# Linux packages the wrap needs on WrapDB CI runners.  X11 and OpenGL are not
# available as wraps, everything else (glfw, freetype, zlib, libpng, curl) is
# resolved from other wrapdb wraps.
DEBIAN_PACKAGES = [
    'libx11-dev',
    'libxrandr-dev',
    'libxinerama-dev',
    'libxcursor-dev',
    'libxi-dev',
    'libxkbcommon-dev',
    'libgl1-mesa-dev',
]
ALPINE_PACKAGES = [
    'libxi-dev',
    'libxkbcommon-dev',
    'mesa-dev',
]


def fail(message: str):
    print(f'error: {message}', file=sys.stderr)
    raise SystemExit(1)


def fetch(url: str) -> bytes:
    print(f'downloading {url}')
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - fixed https URL
        return response.read()


def inspect_archive(data: bytes, version: str) -> str:
    """Verify the release can be wrapped and return its top level directory."""
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        names = archive.getnames()
        roots = {name.split('/', 1)[0] for name in names if name}
        if len(roots) != 1:
            fail(f'archive does not contain exactly one top level directory: {sorted(roots)}')
        root = roots.pop()

        for required in REQUIRED_FILES:
            if f'{root}/{required}' not in names:
                fail(
                    f'the release tarball has no {required}. The tag must contain the Meson '
                    'build before it can be submitted to WrapDB. Commit meson.build and '
                    'meson_options.txt, then tag a new release, or submit a patch-based wrap.',
                )

        for required in REQUIRED_WRAPS:
            if f'{root}/subprojects/{required}' not in names:
                fail(f'the release tarball has no subprojects/{required}')

        meson_build = archive.extractfile(f'{root}/meson.build')
        assert meson_build is not None
        meson_build_text = meson_build.read().decode('utf-8', 'replace')
        if f"'{WRAP_NAME}'" not in meson_build_text:
            fail(f'meson.build does not declare the project name {WRAP_NAME!r}')

    match = re.search(r"version\s*:\s*'([^']+)'", meson_build_text)
    if not match:
        fail('meson.build does not declare a project version')
    if match.group(1) != version:
        fail(
            f'meson.build declares version {match.group(1)!r} but the requested version is '
            f'{version!r}. WrapDB requires them to match.',
        )
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag', nargs='?', help='release tag, for example v0.6.1')
    parser.add_argument('--version', help='release version, for example 0.6.1')
    parser.add_argument('--repo', default=DEFAULT_REPO, help=f'GitHub repository (default: {DEFAULT_REPO})')
    parser.add_argument('--write', action='store_true', help='write eui-neo.wrap into the wrap directory')
    parser.add_argument(
        '--wrap-dir',
        default=DEFAULT_WRAP_DIR,
        help=f'output directory for --write (default: {DEFAULT_WRAP_DIR})',
    )
    args = parser.parse_args()

    if args.version is None and args.tag is None:
        parser.error('provide --version or a release tag')
    version = (args.version or args.tag).lstrip('v')
    tag = f'v{version}'
    url = f'https://github.com/{args.repo}/archive/refs/tags/{tag}.tar.gz'

    data = fetch(url)
    digest = hashlib.sha256(data).hexdigest()
    root = inspect_archive(data, version)
    print(f'sha256: {digest}')
    print(f'tarball root: {root}')

    wrap = (
        f'[wrap-file]\n'
        f'directory = {root}\n'
        '\n'
        f'source_url = {url}\n'
        f'source_filename = {root}.tar.gz\n'
        f'source_hash = {digest}\n'
        '\n'
        '[provide]\n'
        f'dependency_names = {WRAP_NAME}\n'
    )
    release_entry = {'versions': [f'{version}-1'], 'dependency_names': [WRAP_NAME]}
    ci_entry = {'debian_packages': DEBIAN_PACKAGES, 'alpine_packages': ALPINE_PACKAGES}

    print('\n--- subprojects/eui-neo.wrap ---')
    print(wrap)
    print('--- releases.json entry ---')
    print(json.dumps({WRAP_NAME: release_entry}, indent=2))
    print('--- ci_config.json entry ---')
    print(json.dumps({WRAP_NAME: ci_entry}, indent=2))

    if args.write:
        os.makedirs(args.wrap_dir, exist_ok=True)
        path = os.path.join(args.wrap_dir, f'{WRAP_NAME}.wrap')
        with open(path, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(wrap)
        print(f'\nwrote {path}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
