blueprints = custom_target('blueprints',
  input: files(
    'dither_page.blp',
    'help_overlay.blp',
    'main_window.blp',
    'preferences_window.blp',
    'report_page.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)
