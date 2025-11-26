"""
Category Form Dialog
Diálogo para crear y editar categorías
FASE 6: Operaciones CRUD completas
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QTextEdit, QColorDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
import logging

# Get logger
logger = logging.getLogger(__name__)


class CategoryFormDialog(QDialog):
    """
    Dialog for creating and editing categories.

    Modes:
    - 'create': Create new category
    - 'edit': Edit existing category
    - 'duplicate': Duplicate existing category
    """

    def __init__(self, mode='create', category=None, db=None, parent=None):
        """
        Initialize category form dialog

        Args:
            mode: 'create', 'edit', or 'duplicate'
            category: Category dictionary (for edit/duplicate mode)
            db: DBManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.mode = mode
        self.category = category
        self.db = db
        self.selected_color = None

        # Set dialog properties
        self.setModal(True)
        self.setFixedSize(500, 400)

        # Set title based on mode
        titles = {
            'create': 'Nueva Categoría',
            'edit': 'Editar Categoría',
            'duplicate': 'Duplicar Categoría'
        }
        self.setWindowTitle(titles.get(mode, 'Categoría'))

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Initialize the UI"""
        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #cccccc;
            }
            QLabel {
                color: #cccccc;
                font-size: 10pt;
            }
            QLineEdit, QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-size: 10pt;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #007acc;
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
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
            QPushButton#primaryButton {
                background-color: #007acc;
                color: #ffffff;
                border: 1px solid #005a9e;
            }
            QPushButton#primaryButton:hover {
                background-color: #0088dd;
            }
            QPushButton#primaryButton:pressed {
                background-color: #006bb3;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # Name field
        name_label = QLabel("Nombre de la categoría:")
        name_label.setStyleSheet("font-weight: 500;")
        main_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Git, Docker, Python...")
        self.name_input.setMaxLength(100)
        main_layout.addWidget(self.name_input)

        # Icon field
        icon_label = QLabel("Icono (emoji):")
        icon_label.setStyleSheet("font-weight: 500;")
        main_layout.addWidget(icon_label)

        icon_layout = QHBoxLayout()
        icon_layout.setSpacing(10)

        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("Ej: 📁 🐍 💻 🌐")
        self.icon_input.setMaxLength(10)
        icon_layout.addWidget(self.icon_input, 1)

        # Icon preview
        self.icon_preview = QLabel("📁")
        self.icon_preview.setStyleSheet("""
            QLabel {
                font-size: 32px;
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                min-width: 50px;
            }
        """)
        self.icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self.icon_preview)

        self.icon_input.textChanged.connect(self._update_icon_preview)

        main_layout.addLayout(icon_layout)

        # Color field (optional)
        color_label = QLabel("Color (opcional):")
        color_label.setStyleSheet("font-weight: 500;")
        main_layout.addWidget(color_label)

        color_layout = QHBoxLayout()
        color_layout.setSpacing(10)

        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("Ej: #007acc")
        self.color_input.setMaxLength(7)
        color_layout.addWidget(self.color_input, 1)

        # Color picker button
        self.color_picker_btn = QPushButton("Elegir Color")
        self.color_picker_btn.clicked.connect(self._pick_color)
        color_layout.addWidget(self.color_picker_btn)

        # Color preview
        self.color_preview = QLabel("")
        self.color_preview.setFixedSize(50, 30)
        self.color_preview.setStyleSheet("""
            QLabel {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
            }
        """)
        color_layout.addWidget(self.color_preview)

        self.color_input.textChanged.connect(self._update_color_preview)

        main_layout.addLayout(color_layout)

        # Spacer
        main_layout.addStretch()

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Guardar")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._on_save)
        buttons_layout.addWidget(save_btn)

        main_layout.addLayout(buttons_layout)

    def load_data(self):
        """Load category data if in edit or duplicate mode"""
        if self.mode in ['edit', 'duplicate'] and self.category:
            # Load name
            name = self.category.get('name', '')
            if self.mode == 'duplicate':
                name = f"Copia de {name}"
            self.name_input.setText(name)

            # Load icon
            icon = self.category.get('icon', '📁')
            self.icon_input.setText(icon)

            # Load color
            color = self.category.get('color')
            if color:
                self.color_input.setText(color)

    def _update_icon_preview(self, text):
        """Update icon preview"""
        if text.strip():
            self.icon_preview.setText(text.strip()[:2])  # Max 2 characters
        else:
            self.icon_preview.setText("📁")

    def _update_color_preview(self, text):
        """Update color preview"""
        text = text.strip()
        if text and text.startswith('#') and len(text) == 7:
            try:
                # Validate hex color
                int(text[1:], 16)
                self.color_preview.setStyleSheet(f"""
                    QLabel {{
                        background-color: {text};
                        border: 1px solid #4d4d4d;
                        border-radius: 4px;
                    }}
                """)
                self.selected_color = text
            except ValueError:
                self._reset_color_preview()
        else:
            self._reset_color_preview()

    def _reset_color_preview(self):
        """Reset color preview to default"""
        self.color_preview.setStyleSheet("""
            QLabel {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
            }
        """)
        self.selected_color = None

    def _pick_color(self):
        """Open color picker dialog"""
        # Initial color
        initial = QColor(self.selected_color) if self.selected_color else QColor("#007acc")

        color = QColorDialog.getColor(initial, self, "Seleccionar Color")

        if color.isValid():
            hex_color = color.name()
            self.color_input.setText(hex_color)

    def _on_save(self):
        """Handle save button click"""
        # Validate name
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                "Campo Requerido",
                "El nombre de la categoría es obligatorio."
            )
            self.name_input.setFocus()
            return

        # Validate name length
        if len(name) > 100:
            QMessageBox.warning(
                self,
                "Nombre Muy Largo",
                "El nombre no puede exceder 100 caracteres."
            )
            self.name_input.setFocus()
            return

        # Check for duplicate name (except in edit mode with same name)
        if self.db:
            all_categories = self.db.get_categories(include_inactive=True)
            for cat in all_categories:
                # Skip current category in edit mode
                if self.mode == 'edit' and self.category and cat['id'] == self.category['id']:
                    continue

                if cat['name'].lower() == name.lower():
                    reply = QMessageBox.question(
                        self,
                        "Nombre Duplicado",
                        f"Ya existe una categoría con el nombre '{cat['name']}'.\n\n"
                        f"¿Deseas continuar de todas formas?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        self.name_input.setFocus()
                        return

        # Validate icon
        icon = self.icon_input.text().strip()
        if not icon:
            icon = "📁"  # Default icon

        # Get color
        color = self.color_input.text().strip() if self.color_input.text().strip() else None

        # All validations passed
        self.accept()

    def get_data(self):
        """Get form data as dictionary"""
        return {
            'name': self.name_input.text().strip(),
            'icon': self.icon_input.text().strip() or "📁",
            'color': self.color_input.text().strip() or None
        }
