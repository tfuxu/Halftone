project('halftone',
          version: '0.7.0',
    meson_version: '>= 0.59.0',
  default_options: ['warning_level=2',
                    'werror=false',
                   ],
)

# Import modules
i18n = import('i18n')
gnome = import('gnome')
python = import('python')

# Project information
PROJECT_URL = 'https://github.com/tfuxu/halftone'
BUGTRACKER_URL = 'https://github.com/tfuxu/halftone/issues'
HELP_URL = 'https://github.com/tfuxu/halftone/discussions'
#TRANSLATE_URL = 'https://hosted.weblate.org/projects/tfuxu/halftone'

# Constants
PROJECT_RDNN_NAME = 'io.github.tfuxu.Halftone'
ROOT_PATH = '/io/github/tfuxu/Halftone'
PKGDATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
MODULE_DIR = join_paths(PKGDATA_DIR, 'halftone')

git_bin = find_program('git', required: false)

# Set APPLICATION_ID and VERSION_SUFFIX
if get_option('buildtype') == 'debug'
  if git_bin.found()
    VCS_TAG = run_command('git', 'rev-parse', '--short', 'HEAD', check: true).stdout().strip()
  else
    VCS_TAG = ''
  endif
  if VCS_TAG == ''
    VERSION_SUFFIX = '-devel'
  else
    VERSION_SUFFIX = '-@0@'.format(VCS_TAG)
  endif
  APPLICATION_ID = '@0@.Devel'.format(PROJECT_RDNN_NAME)
else
  VERSION_SUFFIX = ''
  APPLICATION_ID = PROJECT_RDNN_NAME
endif

# Required dependencies
dependency('glib-2.0')
dependency('gtk4', version: '>= 4.12.0')
dependency('libadwaita-1', version: '>= 1.5.0')
dependency('pygobject-3.0', version: '>= 3.48.0')

# Python installation directory
PY_INSTALLDIR = python.find_installation('python3')

# Check if python3 is installed
if not PY_INSTALLDIR.found()
  error('No valid python3 binary found!')
endif

# Install configuration data
conf = configuration_data()
conf.set('APP_ID', APPLICATION_ID)
conf.set('ROOT_PATH', ROOT_PATH)
conf.set('PKGDATA_DIR', PKGDATA_DIR)
conf.set('DATA_DIR', join_paths(get_option('prefix'), get_option('datadir')))
conf.set('LOCALE_DIR', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('PYTHON', PY_INSTALLDIR.full_path())
conf.set('VERSION', meson.project_version() + VERSION_SUFFIX)
conf.set('BUILD_TYPE', get_option('buildtype'))
conf.set('SCHEMAS_DIR', PKGDATA_DIR)
conf.set('SOURCE_DIR', meson.current_source_dir())
conf.set('BUILD_DIR', meson.current_build_dir())

# Subdirs
subdir('halftone')
subdir('data')
subdir('po')

# Execute post-installation GTK/GNOME scripts
gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
