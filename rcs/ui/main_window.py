# HOTFIX v0.3.10.2.78
# Improved GMPR import error handling

from PySide6.QtWidgets import QMessageBox

def handle_gmpr_import_error(self, error):
    self.logger.error(f"GMPR import failed due to missing symbol: {error}")
    QMessageBox.critical(
        self,
        "GMPR Import Error",
        "Error interno al importar GMPR.\nRevisar logs."
    )
