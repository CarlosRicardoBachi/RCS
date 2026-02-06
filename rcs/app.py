# File: rcs/app.py
# Project: RusticCreadorSvg (RCS)
# Version: 0.2.1
# Status: stable
# Date: 2026-01-15
# Purpose: Entry-point de la aplicación.
# Notes: Cambios incrementales, no romper funcionalidades probadas.
from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from rcs.core.settings import apply_project_settings
from rcs.core.version import APP_VERSION

from rcs.ui.main_window import MainWindow
from rcs.utils.log import setup_logging, get_logger

log = get_logger(__name__)


def main() -> int:
    setup_logging()
    # Project-level defaults (repo-local): rcs_settings.json
    apply_project_settings(logger=log, prefer_env=True)
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    log.info("RCS iniciado (v%s)", APP_VERSION)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
