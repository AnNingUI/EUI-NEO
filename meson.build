project(
  'eui-neo',
  'c',
  'cpp',
  version: '0.6.0',
  license: 'Apache-2.0',
  meson_version: '>=0.60.0',
  default_options: [
    'c_std=c99',
    'cpp_std=c++17',
    'warning_level=2',
    # Match the CMake build: EUI-NEO and its bundled dependencies are static
    # libraries by default.  Override with -Ddefault_library=shared.
    'default_library=static',
  ],
)

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------

is_subproject = meson.is_subproject()

requested_render_backend = get_option('render_backend')
window_backend = get_option('window_backend')
enable_markdown = get_option('enable_markdown')
enable_modules = get_option('enable_modules')
enable_tray = get_option('enable_tray')
low_latency_present = get_option('low_latency_present')
ffmpeg_video_example = get_option('ffmpeg_video_example')
build_apps = get_option('build_apps') and not is_subproject
build_user_apps = get_option('build_user_apps') and not is_subproject
build_tests = get_option('build_tests') and not is_subproject

if requested_render_backend == 'auto'
  vulkan_probe = dependency('vulkan', required: false)
  if vulkan_probe.found()
    render_backend = 'vulkan'
  else
    render_backend = 'opengl'
  endif
else
  render_backend = requested_render_backend
endif

cc = meson.get_compiler('c')
cpp = meson.get_compiler('cpp')
is_windows = host_machine.system() == 'windows'
is_darwin = host_machine.system() == 'darwin'

if cc.get_id() == 'msvc'
  add_project_arguments('/utf-8', language: ['c', 'cpp'])
elif is_windows
  # MinGW headers default to an older _WIN32_WINNT that hides Windows 10 APIs
  # used by the application entry points (GetDpiForWindow).
  add_project_arguments('-D_WIN32_WINNT=0x0A00', '-DWINVER=0x0A00', language: ['c', 'cpp'])
endif

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
#
# GLFW, FreeType, libpng, zlib, and curl resolve to a system package when one
# is available and otherwise fall back to the pinned wrap files under
# subprojects/ via their [provide] sections.  md4c, glad, yyjson, stb_image,
# nanosvg, miniaudio, and tray are single file libraries that are compiled
# from the vendored sources under 3rd/.

thread_dep = dependency('threads')

if window_backend == 'glfw'
  # install=true makes the GLFW subproject generate glfw3.pc so the
  # eui-neo.pc file can declare the dependency for pkg-config consumers.
  window_dep = dependency('glfw3', default_options: ['install=true'])
else
  # SDL2's bundled test programs are not needed and may fail to link.
  window_dep = dependency('sdl2', default_options: ['test=false'])
endif

freetype_dep = dependency(
  'freetype2',
  # Only the core FreeType modules are needed; keep the dependency tree small.
  default_options: [
    'harfbuzz=disabled',
    'bzip2=disabled',
    'brotli=disabled',
    'tests=disabled',
  ],
)

# Pinned so the FreeType subproject can resolve its own zlib/libpng fallbacks.
zlib_dep = dependency('zlib')
dependency('libpng')

# curl is optional on Windows (URLDownloadToFile fallback) and required
# everywhere else, mirroring the CMake configuration.
if is_windows
  libcurl_dep = dependency('libcurl', required: false)
else
  libcurl_dep = dependency('libcurl')
endif

if render_backend == 'vulkan'
  # Requires a system Vulkan SDK (headers + loader); not available as a wrap.
  vulkan_dep = dependency('vulkan', required: true)
endif

# glad: OpenGL loader used by the OpenGL render backend (vendored).
glad_inc = include_directories('3rd/glad/include')
if render_backend == 'opengl'
  glad_lib = static_library(
    'glad',
    '3rd/glad/src/glad.c',
    include_directories: glad_inc,
    override_options: ['warning_level=0'],
    install: false,
  )
  glad_dep = declare_dependency(
    link_with: glad_lib,
    include_directories: glad_inc,
  )
  if is_windows
    gl_dep = cc.find_library('opengl32')
  elif is_darwin
    gl_dep = dependency('appleframeworks', modules: ['OpenGL'])
  else
    gl_dep = dependency('gl')
  endif
endif

# yyjson: JSON library used by core/platform/json.cpp (vendored).
yyjson_inc = include_directories('3rd/yyjson-0.12.0/src')
yyjson_lib = static_library(
  'yyjson',
  '3rd/yyjson-0.12.0/src/yyjson.c',
  include_directories: yyjson_inc,
  c_args: ['-DYYJSON_DISABLE_WRITER=1'],
  override_options: ['warning_level=0'],
  install: false,
)
yyjson_dep = declare_dependency(
  link_with: yyjson_lib,
  include_directories: yyjson_inc,
)

# md4c: Markdown parser used by components/markdown.h (vendored).
if enable_markdown
  md4c_inc = include_directories('3rd/md4c/src')
  md4c_lib = static_library(
    'md4c',
    '3rd/md4c/src/md4c.c',
    include_directories: md4c_inc,
    override_options: ['warning_level=0'],
    install: false,
  )
  md4c_dep = declare_dependency(
    link_with: md4c_lib,
    include_directories: md4c_inc,
  )
endif

# ---------------------------------------------------------------------------
# Platform capabilities
# ---------------------------------------------------------------------------

platform_deps = []
platform_defs = []
if is_windows
  foreach lib : ['winmm', 'urlmon', 'shell32', 'user32', 'imm32', 'pdh']
    platform_deps += cc.find_library(lib)
  endforeach
  platform_defs += ['EUI_TRAY_WINAPI=1', 'NOMINMAX']
elif is_darwin
  add_languages('objc', native: false)
  platform_deps += dependency(
    'appleframeworks',
    modules: ['Cocoa', 'CoreAudio', 'AudioToolbox', 'CoreFoundation'],
  )
  platform_defs += ['EUI_TRAY_APPKIT=1']
else
  platform_deps += [
    cc.find_library('dl', required: false),
    cc.find_library('m', required: false),
  ]
  # Tray backends: StatusNotifierItem over GDBus only needs glib/gio, the
  # GTK3 + libappindicator chain is the maintained-fork fallback.
  gio_dep = dependency('gio-2.0', required: false)
  appindicator_dep = dependency('appindicator3-0.1', required: false)
  gtk_dep = dependency('gtk+-3.0', required: false)
  if enable_tray
    if gio_dep.found()
      platform_defs += ['EUI_TRAY_SNI=1']
      platform_deps += gio_dep
    elif appindicator_dep.found() and gtk_dep.found()
      platform_defs += ['EUI_TRAY_APPINDICATOR=1']
      platform_deps += [appindicator_dep, gtk_dep]
    elif not is_subproject
      # Fail loudly instead of silently building a tray-less library, like the
      # CMake build does.  As a subproject (wrap) this degrades to the tray
      # stub so parents and distro builds are never blocked by the tray.
      error(
        'Linux tray support requires glib/gio (gio-2.0, SNI backend) or ' +
        'GTK3 + libappindicator. Install one, or configure with ' +
        '-Denable_tray=false to build without tray support.',
      )
    endif
  endif
endif

# Public compile definitions: consumers must see the same backend macros the
# library was built with, so they are propagated through eui_neo_dep.
eui_public_defs = []
eui_private_defs = []
if render_backend == 'opengl'
  eui_public_defs += 'EUI_RENDER_BACKEND_OPENGL=1'
else
  eui_public_defs += 'EUI_RENDER_BACKEND_VULKAN=1'
  if low_latency_present
    eui_private_defs += 'EUI_VULKAN_LOW_LATENCY_PRESENT=1'
  endif
endif
if window_backend == 'sdl2'
  eui_public_defs += 'EUI_WINDOW_BACKEND_SDL2=1'
endif
if libcurl_dep.found()
  eui_public_defs += 'EUI_HAS_CURL=1'
endif
if enable_markdown
  eui_public_defs += 'EUI_HAS_MD4C=1'
endif
if get_option('debug')
  eui_public_defs += 'EUI_DEBUG_BUILD=1'
endif
eui_public_defs += platform_defs

# Meson passes these strings verbatim to the compiler driver, so each define
# needs its -D (or /D) prefix.  cl.exe accepts -D as well, keeping the lists
# portable across gcc, clang, and MSVC.
eui_public_args = []
foreach define : eui_public_defs
  eui_public_args += '-D' + define
endforeach
eui_private_args = []
foreach define : eui_private_defs
  eui_private_args += '-D' + define
endforeach

# ---------------------------------------------------------------------------
# Core library
# ---------------------------------------------------------------------------

eui_core_sources = files(
  'core/audio/audio.cpp',
  'core/platform/async.cpp',
  'core/platform/json.cpp',
  'core/platform/network.cpp',
  'core/platform/performance_stats.cpp',
  'core/platform/platform.cpp',
  'core/render/image.cpp',
  'core/render/image_facade.cpp',
  'core/render/image_source.cpp',
  'core/render/image_stream.cpp',
  'core/render/primitive.cpp',
  'core/render/render_backend.cpp',
  'core/render/shadertoy.cpp',
  'core/render/shadertoy_json.cpp',
  'core/render/shadertoy_primitive.cpp',
  'core/render/stb_image_impl.cpp',
  'core/render/text.cpp',
  'core/window/window_backend.cpp',
  'core/window/window_input_backend.cpp',
)

if render_backend == 'opengl'
  eui_core_sources += files(
    'core/render/opengl/opengl_backend.cpp',
    'core/render/opengl/opengl_image.cpp',
    'core/render/opengl/opengl_primitives.cpp',
    'core/render/opengl/opengl_shadertoy.cpp',
    'core/render/opengl/opengl_text.cpp',
  )
else
  eui_core_sources += files(
    'core/render/vulkan/vulkan_backend.cpp',
    'core/render/vulkan/vulkan_cache.cpp',
    'core/render/vulkan/vulkan_image.cpp',
    'core/render/vulkan/vulkan_polygon.cpp',
    'core/render/vulkan/vulkan_primitives.cpp',
    'core/render/vulkan/vulkan_shadertoy.cpp',
    'core/render/vulkan/vulkan_text.cpp',
  )
endif

if window_backend == 'glfw'
  eui_core_sources += files('core/platform/ime_bridge.c')
endif

if is_darwin
  # CMake compiles these two bridges as Objective-C.  Meson picks the language
  # from the file extension, so copy them to .m for the Apple build.
  tray_bridge_m = custom_target(
    'tray_bridge.m',
    input: 'core/platform/tray_bridge.c',
    output: 'tray_bridge.m',
    command: [find_program('cp'), '@INPUT@', '@OUTPUT@'],
  )
  native_bridge_m = custom_target(
    'native_bridge.m',
    input: 'core/platform/native_bridge.c',
    output: 'native_bridge.m',
    command: [find_program('cp'), '@INPUT@', '@OUTPUT@'],
  )
  eui_core_sources += [tray_bridge_m, native_bridge_m]
else
  eui_core_sources += files(
    'core/platform/native_bridge.c',
    'core/platform/tray_bridge.c',
  )
endif

eui_public_incs = include_directories('include', '.', '3rd/tray')
# 3rd/ is private: audio.cpp includes the vendored miniaudio.h directly.
eui_private_incs = [yyjson_inc, include_directories('3rd')]
if render_backend == 'opengl'
  eui_private_incs += glad_inc
endif
if enable_markdown
  eui_private_incs += md4c_inc
endif

eui_neo_link_deps = [thread_dep, window_dep, freetype_dep, yyjson_dep]
if libcurl_dep.found()
  eui_neo_link_deps += libcurl_dep
endif
if render_backend == 'opengl'
  eui_neo_link_deps += [glad_dep, gl_dep]
else
  eui_neo_link_deps += vulkan_dep
endif
if enable_markdown
  eui_neo_link_deps += md4c_dep
endif
eui_neo_link_deps += platform_deps

eui_neo_lib = library(
  'eui_neo',
  eui_core_sources,
  include_directories: [eui_public_incs, eui_private_incs],
  dependencies: eui_neo_link_deps,
  c_args: eui_public_args + eui_private_args,
  cpp_args: eui_public_args + eui_private_args,
  version: meson.project_version(),
  install: not is_subproject,
)

eui_neo_dep = declare_dependency(
  link_with: eui_neo_lib,
  include_directories: eui_public_incs,
  compile_args: eui_public_args,
  dependencies: eui_neo_link_deps,
)

# Allows `dependency('eui-neo')` to resolve when EUI-NEO is used as a wrap.
meson.override_dependency('eui-neo', eui_neo_dep)

# ---------------------------------------------------------------------------
# Optional modules
# ---------------------------------------------------------------------------

fs = import('fs')

eui_neo_module_keyboard_dep = disabler()
eui_neo_module_serial_dep = disabler()

if enable_modules
  if fs.is_dir('modules/keyboard')
    eui_neo_module_keyboard_dep = declare_dependency(dependencies: eui_neo_dep)
  endif
  if fs.is_dir('modules/serial')
    eui_neo_module_serial = library(
      'eui_neo_module_serial',
      'modules/serial/serial.cpp',
      'modules/serial/serial.h',
      dependencies: eui_neo_dep,
      version: meson.project_version(),
      install: not is_subproject,
    )
    eui_neo_module_serial_dep = declare_dependency(
      link_with: eui_neo_module_serial,
      dependencies: eui_neo_dep,
    )
  endif
endif

# ---------------------------------------------------------------------------
# Bundled examples and user applications
# ---------------------------------------------------------------------------

if window_backend == 'glfw'
  app_main_source = 'core/app/glfw_app_main.cpp'
else
  app_main_source = 'core/app/sdl2_app_main.cpp'
endif

if build_apps or build_user_apps
  win_app_link_args = []
  if is_windows and cc.get_id() == 'msvc'
    win_app_link_args = ['/ENTRY:mainCRTStartup', '/SUBSYSTEM:WINDOWS']
  endif

  # Compile definitions the bundled UI demos expect, mirroring CMake's
  # eui_neo_configure_named_app().
  shadertoy_args = [
    '-DEUI_SHADERTOY_DEMO_SOURCE="assets/shaders/shadertoy/demo.frag"',
    '-DEUI_SHADERTOY_DEMO_SPIRV="assets/shaders/shadertoy/demo.frag.spv"',
    '-DEUI_SHADERTOY_PRESETS_DIR="assets/shaders/shadertoy"',
  ]
  gallery_args = [
    '-DEUI_GALLERY_SHADERTOY_SOURCE="assets/shaders/shadertoy/demo.frag"',
    '-DEUI_GALLERY_SHADERTOY_NOISE="assets/shaders/shadertoy/blackhole/color_noise.png"',
    '-DEUI_GALLERY_SHADERTOY_SPIRV="assets/shaders/shadertoy/gallery_demo.frag.spv"',
  ]
endif

if build_apps
  foreach example_name : [
    'animated_card',
    'dynamic_texture',
    'eui_demo',
    'keyboard',
    'magic_wand',
    'multipage_table',
    'shadertoy',
  ]
    if example_name == 'keyboard' and not fs.is_dir('modules/keyboard')
      continue
    endif
    example_args = []
    if example_name == 'shadertoy'
      example_args = shadertoy_args
    endif
    executable(
      example_name,
      app_main_source,
      'examples' / (example_name + '.cpp'),
      dependencies: eui_neo_dep,
      cpp_args: example_args,
      link_args: win_app_link_args,
    )
  endforeach

  if ffmpeg_video_example
    # Optional: the FFmpeg video playback demo is off by default.
    ffmpeg_deps = [eui_neo_dep]
    foreach ffmpeg_dep_name : ['libavformat', 'libavcodec', 'libavutil', 'libswscale']
      ffmpeg_deps += dependency(ffmpeg_dep_name)
    endforeach
    executable(
      'ffmpeg_video_player',
      app_main_source,
      'examples/ffmpeg_video_player.cpp',
      dependencies: ffmpeg_deps,
      link_args: win_app_link_args,
    )
  endif
endif

if build_user_apps
  # Longer, multi-page applications under apps/<name>/app.cpp.  Sources are
  # listed explicitly because Meson has no build-time globbing.
  user_apps = {
    'calculator': [],
    'calgary_gallery': [],
    'card_slider': [],
    'clock': [],
    'gallery': [],
    'promo': [],
    'serial_tool': [],
    'sidebar_starter': [],
    'vcd_viewer': ['apps/vcd_viewer/vcd_model.cpp'],
  }
  foreach app_name, app_local_sources : user_apps
    app_entry = 'apps' / app_name / 'app.cpp'
    if not fs.is_file(app_entry)
      continue
    endif
    if app_name == 'serial_tool' and not fs.is_dir('modules/serial')
      continue
    endif
    app_sources = [app_main_source, app_entry]
    app_sources += files(app_local_sources)
    app_deps = [eui_neo_dep]
    app_args = []
    if app_name == 'gallery'
      app_args = gallery_args
    elif app_name == 'promo'
      app_args = shadertoy_args
    elif app_name == 'serial_tool'
      app_deps += eui_neo_module_serial_dep
    elif app_name == 'vcd_viewer'
      app_deps += zlib_dep
    endif
    executable(
      app_name,
      app_sources,
      include_directories: include_directories('apps' / app_name),
      dependencies: app_deps,
      cpp_args: app_args,
      link_args: win_app_link_args,
    )
  endforeach
endif

# Copy runtime assets next to the built applications after configuration.
if (build_apps or build_user_apps) and fs.is_dir('assets')
  app_asset_dirs = [meson.project_source_root() / 'assets']
  foreach app_name : ['calgary_gallery']
    if fs.is_dir('apps' / app_name / 'assets')
      app_asset_dirs += meson.project_source_root() / 'apps' / app_name / 'assets'
    endif
  endforeach
  meson.add_postconf_script(
    'meson/copy_assets.py',
    meson.project_build_root() / 'assets',
    app_asset_dirs,
  )
endif

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

if build_tests
  unit_tests = [
    'audio_api',
    'color_hex',
    'dirty_rects',
    'dsl_app_config',
    'gpu_image',
    'image_cache',
    'image_path_resolution',
    'image_stream',
    'image_stream_primitive',
    'image_theme_color',
    'ime_rect',
    'input_editing',
    'input_model',
    'input_scrollbar',
    'json',
    'layout_numeric',
    'pointer_input',
    'shadertoy_graph',
    'shadertoy_primitive',
    'signal',
    'svg_source',
    'ui_state',
  ]
  if enable_modules and fs.is_dir('modules/keyboard')
    unit_tests += 'keyboard_module'
  endif
  foreach test_name : unit_tests
    test_exe = executable(
      'unit_' + test_name,
      'tests/unit' / (test_name + '.cpp'),
      dependencies: eui_neo_dep,
    )
    test(test_name, test_exe, suite: 'eui-neo')
  endforeach
endif

# ---------------------------------------------------------------------------
# Install rules and pkg-config
# ---------------------------------------------------------------------------

if not is_subproject
  install_headers('include/eui_neo.h')
  install_subdir('include/eui', install_dir: get_option('includedir'))

  eui_core_non_headers = [
    'core/app/glfw_app_main.cpp',
    'core/app/sdl2_app_main.cpp',
    'core/audio/audio.cpp',
    'core/platform/async.cpp',
    'core/platform/ime_bridge.c',
    'core/platform/json.cpp',
    'core/platform/native_bridge.c',
    'core/platform/network.cpp',
    'core/platform/performance_stats.cpp',
    'core/platform/platform.cpp',
    'core/platform/tray_bridge.c',
    'core/render/image.cpp',
    'core/render/image_facade.cpp',
    'core/render/image_source.cpp',
    'core/render/image_stream.cpp',
    'core/render/opengl/opengl_backend.cpp',
    'core/render/opengl/opengl_image.cpp',
    'core/render/opengl/opengl_primitives.cpp',
    'core/render/opengl/opengl_shadertoy.cpp',
    'core/render/opengl/opengl_text.cpp',
    'core/render/primitive.cpp',
    'core/render/render_backend.cpp',
    'core/render/shadertoy.cpp',
    'core/render/shadertoy_json.cpp',
    'core/render/shadertoy_primitive.cpp',
    'core/render/stb_image_impl.cpp',
    'core/render/text.cpp',
    'core/render/vulkan/vulkan_backend.cpp',
    'core/render/vulkan/vulkan_cache.cpp',
    'core/render/vulkan/vulkan_image.cpp',
    'core/render/vulkan/vulkan_polygon.cpp',
    'core/render/vulkan/vulkan_primitives.cpp',
    'core/render/vulkan/vulkan_shadertoy.cpp',
    'core/render/vulkan/vulkan_text.cpp',
    'core/window/window_backend.cpp',
    'core/window/window_input_backend.cpp',
  ]
  install_subdir(
    'core',
    install_dir: get_option('includedir') / 'eui-neo',
    exclude_files: eui_core_non_headers,
  )
  install_subdir(
    'components',
    install_dir: get_option('includedir') / 'eui-neo',
    exclude_files: ['SKILL.md'],
  )
  if fs.is_dir('modules')
    install_subdir(
      'modules',
      install_dir: get_option('includedir') / 'eui-neo',
      exclude_files: ['CMakeLists.txt', 'README.md', 'serial.cpp'],
    )
  endif

  install_data(
    '3rd/stb_image.h',
    '3rd/nanosvg.h',
    '3rd/nanosvgrast.h',
    install_dir: get_option('includedir') / 'eui-neo' / '3rd',
  )
  install_data(
    '3rd/miniaudio.h',
    install_dir: get_option('includedir') / 'eui-neo' / '3rd',
  )
  install_data(
    '3rd/tray/tray.h',
    install_dir: get_option('includedir') / 'eui-neo' / '3rd' / 'tray',
  )

  # Application entry point and shared runtime assets, as the CMake package
  # installs them for downstream consumers.
  install_data(
    app_main_source,
    install_dir: get_option('datadir') / 'eui-neo' / 'app',
    rename: 'app_main.cpp',
  )
  if fs.is_dir('assets')
    install_subdir('assets', install_dir: get_option('datadir') / 'eui-neo')
  endif

  pkg = import('pkgconfig')
  pkg.generate(
    eui_neo_lib,
    name: 'eui-neo',
    description: 'EUI-NEO is a cross-platform, high-performance C++17 UI framework',
    url: 'https://github.com/sudoevolve/EUI-NEO',
    filebase: 'eui-neo',
    subdirs: ['eui-neo'],
    extra_cflags: ['-I${includedir}'],
  )
endif
