# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import threading

import logging


class KillableThread(threading.Thread):
  def __init__(self, *args, **kwargs):
    threading.Thread.__init__(self, *args, **kwargs)
    self.killed = False

  def start(self):
    self._run_backup = self.run
    self.run = self._run
    threading.Thread.start(self)

  def _run(self):
    sys.settrace(self.globaltrace)
    self._run_backup()
    self.run = self._run_backup

  def globaltrace(self, frame, event, *args):
    if event == 'call':
      return self.localtrace
    else:
      return None

  def localtrace(self, frame, event, *args):
    if self.killed:
      if event == 'line':
        raise SystemExit()
    return self.localtrace

  def kill(self):
    logging.debug(f"Killing {threading.get_ident()}")
    self.killed = True
