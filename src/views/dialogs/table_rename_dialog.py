"""
Table Rename Dialog - Diálogo para renombrar tabla
"""

import sys
from pathlib import Path
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_manager import DBManager
from core.table_validator import TableValidator

logger = logging.getLogger(__name__)


class TableRenameDialog(QDialog):
    """
    Diálogo para renombrar tabla.

    Señales:
        table_renamed(str, str): Emitida cuando se renombra (old_name, new_name)
    """

    table_renamed = pyqtSignal(str, str)  # old_name, new_name

    def __init__(self, db_manager: DBManager, current_name: str, parent=None):
        """
        Inicializa el diálogo.

        Args:
            db_manager: Instancia de DBManager
            current_name: Nombre actual de la tabla
            parent: Widget padre
        """
        super().__init__(parent)
        self.db = db_manager
        self.current_name = current_name

        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz."""
        self.setWindowTitle(f"Renombrar Tabla")
        self.setMinimumWidth(500)
        self.setModal(True)

        # Aplicar tema oscuro
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #cccccc;
            }
            QLabel {
                color: #cccccc;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #007acc;
            }
            QPushButton#rename_button {
                background-color: #007acc;
                color: #ffffff;
                border: none;
            }
            QPushButton#rename_button:hover {
                background-color: #005a9e;
            }
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                color: #cccccc;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
        """)

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título
        title = QLabel("✏️ Renombrar Tabla")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #00d4ff;")
        layout.addWidget(title)

        # Formulario
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # Nombre actual (read-only)
        self.current_input = QLineEdit(self.current_name)
        self.current_input.setReadOnly(True)
        self.current_input.setStyleSheet("""
            QLineEdit {
                background-color: #252525;
                color: #858585;
            }
        """)
        form_layout.addRow("Nombre actual:", self.current_input)

        # Nuevo nombre
        self.new_name_input = QLineEdit()
        self.new_name_input.setPlaceholderText("Ej: NUEVA_TABLA")
        self.new_name_input.setText(self.current_name)  # Pre-fill con nombre actual
        self.new_name_input.selectAll()  # Seleccionar todo para fácil edición
        form_layout.addRow("Nuevo nombre:", self.new_name_input)

        layout.addLayout(form_layout)

        # Reglas de validación
        rules = QLabel(
            "📋 Reglas para nombres de tabla:\n"
            "• Letras (mayúsculas o minúsculas), números, guiones (-) y guiones bajos (_)\n"
            "• Máximo 100 caracteres\n"
            "• No puede ser una palabra reservada SQL\n"
            "• Debe ser único"
        )
        rules.setWordWrap(True)
        rules.setStyleSheet("color: #aaaaaa; font-size: 9pt; padding: 10px; background-color: #252525; border-radius: 4px;")
        layout.addWidget(rules)

        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        buttons_layout.addStretch()

        self.rename_button = QPushButton("✏️ Renombrar")
        self.rename_button.setObjectName("rename_button")
        self.rename_button.clicked.connect(self.rename_table)
        buttons_layout.addWidget(self.rename_button)

        layout.addLayout(buttons_layout)

        # Focus en input de nuevo nombre
        self.new_name_input.setFocus()

    def rename_table(self):
        """Ejecuta el renombrado."""
        new_name = self.new_name_input.text().strip()

        # Validar que no esté vacío
        if not new_name:
            QMessageBox.warning(
                self,
                "Nombre Requerido",
                "Por favor ingresa un nuevo nombre para la tabla."
            )
            return

        # Validar que sea diferente
        if new_name == self.current_name:
            QMessageBox.information(
                self,
                "Sin Cambios",
                "El nuevo nombre es igual al actual."
            )
            return

        # Obtener lista de tablas existentes
        try:
            tables = self.db.get_all_tables()
            existing_tables = [table['name'] for table in tables]

        except Exception as e:
            logger.error(f"Error getting existing tables: {e}")
            existing_tables = []

        # Validar nombre usando TableValidator
        is_valid, error_msg = TableValidator.validate_table_name(
            new_name,
            existing_tables=existing_tables,
            exclude_table=self.current_name
        )

        if not is_valid:
            QMessageBox.warning(
                self,
                "Nombre Inválido",
                f"El nombre no es válido:\n\n{error_msg}"
            )
            return

        # Confirmar renombrado
        response = QMessageBox.question(
            self,
            "Confirmar Renombrado",
            f"¿Estás seguro de que deseas renombrar la tabla?\n\n"
            f"De: {self.current_name}\n"
            f"A: {new_name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        # Ejecutar renombrado en BD
        try:
            # Get table by current name and update it
            table = self.db.get_table_by_name(self.current_name)
            if not table:
                raise Exception(f"Table '{self.current_name}' not found")

            self.db.update_table(table['id'], name=new_name)

            QMessageBox.information(
                self,
                "Tabla Renombrada",
                f"Tabla renombrada exitosamente."
            )

            # Emitir señal
            self.table_renamed.emit(self.current_name, new_name)

            logger.info(f"Table renamed: {self.current_name} -> {new_name}")

            # Cerrar diálogo
            self.accept()

        except Exception as e:
            logger.error(f"Error renaming table: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Error al renombrar tabla:\n{str(e)}"
            )
