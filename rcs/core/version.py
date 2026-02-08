"""RCS - version constants.

Keep this module tiny and dependency-free. It is imported by many places
(core models, UI, tools) and must not have side effects.
"""

APP_NAME = "RusticCreadorSvg"
APP_SHORT = "RCS"

# App semantic version (must match patch notes / docs).
APP_VERSION = "0.3.10.2.77"
# Project schema version used for .RCS project files.
# NOTE: must be int because `rcs.core.models.Project` compares it as integer.
SCHEMA_VERSION = 1

# Defaults (in millimeters)
# NOTE: keep these stable; changing impacts new project defaults.
DEFAULT_CANVAS_MM = (160.0, 100.0)
DEFAULT_GRID_MM = 5.0
