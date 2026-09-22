# Building EUI-NEO With Meson

EUI-NEO ships a Meson build alongside the CMake one. It produces the same
`eui_neo` library, the optional modules, the bundled examples, the longer
applications under `apps/`, the headless unit test suite, and a pkg-config
file for installed consumers.

## Requirements

- Meson 0.60 or newer
- Ninja
- A C++17 compiler (MSVC 2019+, GCC 9+, or Clang 10+)
- OpenGL development files for the default render backend
- Vulkan SDK when `render_backend=vulkan` is selected
- Linux: X11 development packages for GLFW, plus glib/gio or GTK3 +
  libappindicator when tray support is wanted

## Quick start

```sh
meson setup build
meson compile -C build
meson test -C build --suite eui-neo   # only when configured with -Dbuild_tests=true
./build/eui_demo
```

Runtime assets are copied next to the built programs after configuration, so
the examples and apps find their fonts, icons, and shaders without extra
steps.

## Options

| Option | Values | Default | Meaning |
| --- | --- | --- | --- |
| `render_backend` | `auto`, `opengl`, `vulkan` | `auto` | `auto` picks Vulkan when a Vulkan SDK is found, otherwise OpenGL. |
| `window_backend` | `glfw`, `sdl2` | `glfw` | Window/input backend. |
| `build_apps` | boolean | `true` | Build `examples/*.cpp` (top-level builds only). |
| `build_user_apps` | boolean | `true` | Build the longer applications in `apps/` (top-level builds only). |
| `build_tests` | boolean | `false` | Build and register the headless unit tests. |
| `ffmpeg_video_example` | boolean | `false` | Build the optional FFmpeg playback demo (needs FFmpeg dev files). |
| `enable_modules` | boolean | `true` | Build the optional modules under `modules/`. |
| `enable_markdown` | boolean | `true` | Link MD4C for `components/markdown.h`. |
| `enable_tray` | boolean | `true` | Use the platform tray backend when one is available. |
| `low_latency_present` | boolean | `false` | Prefer low-latency Vulkan presentation. |

Example configurations:

```sh
# Vulkan renderer
meson setup build-vk -Drender_backend=vulkan

# SDL2 window backend
meson setup build-sdl2 -Dwindow_backend=sdl2

# Library only, with the unit tests
meson setup build-lib -Dbuild_apps=false -Dbuild_user_apps=false -Dbuild_tests=true
```

## Dependencies

The Meson build prefers an installed dependency and otherwise uses the pinned
wrap files in `subprojects/`, which point at [Meson's WrapDB](https://wrapdb.mesonbuild.com/):

| Dependency | Wrap | Notes |
| --- | --- | --- |
| GLFW | `subprojects/glfw.wrap` | Window backend (default). |
| SDL2 | `subprojects/sdl2.wrap` | Only when `window_backend=sdl2`. |
| FreeType | `subprojects/freetype2.wrap` | Text rendering. |
| zlib, libpng | `subprojects/zlib.wrap`, `subprojects/libpng.wrap` | Used by FreeType. |
| curl | `subprojects/curl.wrap` | Networking; optional on Windows. |
| Vulkan | system only | Loader + headers are not available as a wrap. |

`subprojects/` only contains the wrap files; Meson downloads and builds the
sources on demand. Use `meson subprojects download` to pre-populate them for
offline builds, and `--wrap-mode=forcefallback` to ignore system packages
entirely.

glad, yyjson, md4c, `stb_image.h`, `nanosvg.h`, `nanosvgrast.h`,
`miniaudio.h`, and `tray.h` are vendored under `3rd/` and compiled from that
tree, exactly like the CMake build.

## Using EUI-NEO from another Meson project

A complete consumer project looks like this:

```
my_project/
├── meson.build
├── src/main.cpp
└── subprojects/
    └── eui-neo/            # this repository (or a WrapDB wrap)
        └── subprojects/    # the dependency wraps EUI-NEO itself uses
```

Once the wrap is available in WrapDB, `meson wrap install eui-neo` fetches it
into `subprojects/`. Until then, place a checkout there directly;
`meson.override_dependency()` makes `dependency('eui-neo')` resolve to it either
way.

`meson.build`:

```meson
project('my_app', 'c', 'cpp', version: '0.1.0',
  default_options: ['cpp_std=c++17', 'default_library=static'])

eui = subproject('eui-neo')
eui_dep = dependency('eui-neo')

executable('my_app', 'src/main.cpp',
  # The second dependency carries the application entry point that matches the
  # window backend EUI-NEO was configured with.
  dependencies: [eui_dep, eui.get_variable('eui_neo_app_dep')])

# Copy EUI-NEO's runtime assets (fonts, icons, shaders) next to the program.
meson.add_postconf_script(
  eui.get_variable('eui_neo_copy_assets_script'),
  meson.project_build_root() / 'assets',
  eui.get_variable('eui_neo_assets_dir'))
```

`src/main.cpp` only defines `app::dslAppConfig()` and `app::compose(...)`; see
the minimal example in the top-level README. EUI-NEO owns the window, the event
loop, the render backend, and resource resolution.

```sh
meson setup build
meson compile -C build
./build/my_app
```

### Exported subproject variables

| Variable | Type | Purpose |
| --- | --- | --- |
| `eui_neo_app_dep` | dependency | Application entry point for the configured window backend (carries the source plus `eui_neo_dep`). Meson forbids parents from taking subproject files by path, so it travels as a dependency. |
| `eui_neo_assets_dir` | string | Absolute path to the bundled runtime assets. |
| `eui_neo_copy_assets_script` | string | `meson/copy_assets.py`, which copies asset directories into a destination. |

### Notes

- The **parent** project must request C++17 itself (`default_options:
  ['cpp_std=c++17']`); dependency objects do not propagate the language
  standard.
- As a subproject EUI-NEO builds only the library and modules, never the
  examples, apps, or tests, and registers no install rules.
- Subproject options are set from the parent, for example
  `-Deui-neo:window_backend=sdl2`, `-Deui-neo:render_backend=vulkan`, or
  `-Deui-neo:enable_tray=false`.

## Installing

```sh
meson setup build --prefix=/usr/local
meson compile -C build
meson install -C build
```

This installs headers, `libeui_neo`, the pkg-config file `eui-neo.pc`, the
application entry point (`share/eui-neo/app/app_main.cpp`), and the runtime
assets (`share/eui-neo/assets`), mirroring the CMake install layout.

## Platform notes

- **Windows / MSVC**: `/utf-8` is added automatically. Examples link with
  `/SUBSYSTEM:WINDOWS` and `mainCRTStartup`, like the CMake build.
- **Windows / MinGW**: `_WIN32_WINNT`/`WINVER` are raised to `0x0A00` so the
  Windows 10 APIs used by the app entry points are declared.
- **macOS**: the two Objective-C bridges (`native_bridge.c`, `tray_bridge.c`)
  are copied to `.m` so that Meson compiles them as Objective-C. Cocoa,
  CoreAudio, AudioToolbox, and CoreFoundation are linked.
- **Linux tray**: glib/gio (StatusNotifierItem) is preferred, then GTK3 +
  libappindicator. A top-level configure fails when neither is present, unless
  `-Denable_tray=false` is given. As a subproject the tray backend is simply
  disabled instead of failing, so parents and distro builds are never blocked.

## Differences from the CMake build

- Vulkan builds do not compile `.frag` sources into SPIR-V at build time
  (`eui_compile_shadertoy` / `eui_shadertoy_wrap` are CMake-only helpers).
  Pre-generated SPIR-V headers under `core/render/vulkan/` are used, and the
  demos expect their SPIR-V files in the runtime asset directory.
- The `eui_check_vulkan_shaders` and asset-copy targets are CMake-specific;
  Meson copies assets once after configuration instead of per target.
- Tests are registered as the `eui-neo` suite and are off by default, matching
  `EUI_BUILD_TEST_FIXTURES=OFF`. Several unit tests are `assert()`-based, so a
  `--buildtype=release` run (like the project's `ctest -C Release`) is what the
  upstream CI exercises; debug runs enable stricter assertions.
