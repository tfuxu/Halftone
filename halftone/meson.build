# Generate Python executable
configure_file(
  input: 'halftone.in',
  output: 'halftone',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

# Generate constants module
configure_file(
  input: 'constants.in',
  output: 'constants.py',
  configuration: configuration_data({
    'APP_ID': APPLICATION_ID,
    'ROOT_PATH': ROOT_PATH,
    'RELEASE_VER': meson.project_version(),
    'VERSION': meson.project_version() + VERSION_SUFFIX,
    'BUILD_TYPE': get_option('buildtype'),
    'PROJECT_URL': PROJECT_URL,
    'BUGTRACKER_URL': BUGTRACKER_URL,
    'HELP_URL': HELP_URL,
    #'TRANSLATE_URL': TRANSLATE_URL,
    'DATA_DIR': conf.get('DATA_DIR'),
    'PKGDATA_DIR': PKGDATA_DIR,
    'LOCALE_DIR': conf.get('LOCALE_DIR'),
  }),
  install: true,
  install_dir: MODULE_DIR
)

# Local build launcher
launcher = join_paths(meson.project_build_root(), 'halftone', meson.project_name())
run_target('run',
  command: [launcher]
)

# Python sources
sources = [
  '__init__.py',
  'main.py',
]

# Install sources
install_data(sources, install_dir: MODULE_DIR)

# Install backend modules
install_subdir('backend', install_dir: MODULE_DIR)

# Install frontend utils
install_subdir('utils', install_dir: MODULE_DIR)

# Install custom views
install_subdir('views', install_dir: MODULE_DIR)
