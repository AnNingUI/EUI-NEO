#!/usr/bin/env python3
"""Copy runtime assets next to the built applications.

Meson runs this script after configuration (meson.add_postconf_script) for
top-level builds so that the bundled examples and apps can resolve their
fonts, icons, and shader assets at run time, mirroring the asset copy the
CMake build performs after each app target.

Usage: copy_assets.py <destination> <source-dir> [<source-dir> ...]

Each source directory is merged into the destination directory.
"""

import os
import shutil
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print('copy_assets.py: expected <destination> <source>...', file=sys.stderr)
        return 2
    destination = sys.argv[1]
    sources = sys.argv[2:]
    missing = [source for source in sources if not os.path.isdir(source)]
    if missing:
        print(f'copy_assets.py: source directory not found: {missing[0]}', file=sys.stderr)
        return 1
    if os.path.isdir(destination):
        shutil.rmtree(destination)
    for source in sources:
        shutil.copytree(source, destination, dirs_exist_ok=True)
    print(f'copy_assets.py: copied {len(sources)} asset directory(ies) into {destination}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
