blueprints = custom_target('blueprints',
  input: files(
    'dither_page.blp',
    'error_page.blp',
    'image_options_view.blp',
    'image_view.blp',
    'main_window.blp',
    'preferences_window.blp',
    'report_page.blp',
    'shortcuts_dialog.blp'
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@']
)
