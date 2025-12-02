"""
Component Editor Dialog - Diálogo para agregar/editar componentes con tags
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.core.project_element_tag_manager import ProjectElementTagManager
from src.views.widgets.project_tag_selector import ProjectTagSelector


class ComponentEditorDialog(QDialog):
    """
    Diálogo para agregar/editar componentes con soporte de tags
    """

    def __init__(self, tag_manager: ProjectElementTagManager,
                 component_type: str = 'comment',
                 initial_content: str = '',
                 initial_tags: list = None,
                 parent=None):
        """
        Inicializa el diálogo

        Args:
            tag_manager: Manager de tags del proyecto
            component_type: Tipo de componente (comment, alert, note)
            initial_content: Contenido inicial (para edición)
            initial_tags: Tags iniciales (para edición)
            parent: Widget padre
        """
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.component_type = component_type
        self.initial_content = initial_content
        self.initial_tags = initial_tags or []

        self.content = ''
        self.selected_tag_ids = []

        self._setup_ui()

    def _setup_ui(self):
        """Configura la interfaz del diálogo"""
        # Configuración de ventana
        self.setWindowTitle(f"Agregar {self.component_type.title()}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Título con emoji según tipo
        icons = {
            'comment': '💬',
            'alert': '⚠️',
            'note': '📌'
        }
        icon = icons.get(self.component_type, '💬')

        title = QLabel(f"{icon} {self.component_type.title()}")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #ecf0f1;")
        main_layout.addWidget(title)

        # Campo de contenido
        content_group = QGroupBox("Contenido")
        content_group.setStyleSheet("""
            QGroupBox {
                color: #ecf0f1;
                font-weight: bold;
                border: 2px solid #34495e;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        content_layout = QVBoxLayout(content_group)

        self.content_edit = QTextEdit()
        self.content_edit.setPlainText(self.initial_content)
        self.content_edit.setPlaceholderText(f"Escribe el contenido del {self.component_type}...")
        self.content_edit.setMinimumHeight(100)
        self.content_edit.setMaximumHeight(150)
        self.content_edit.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 4px;
                padding: 8px;
                font-size: 10pt;
            }
        """)
        content_layout.addWidget(self.content_edit)

        main_layout.addWidget(content_group)

        # Selector de tags
        tags_group = QGroupBox("Tags (Opcional)")
        tags_group.setStyleSheet("""
            QGroupBox {
                color: #ecf0f1;
                font-weight: bold;
                border: 2px solid #34495e;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        tags_layout = QVBoxLayout(tags_group)

        self.tag_selector = ProjectTagSelector(self.tag_manager)

        # Establecer tags iniciales si existen
        if self.initial_tags:
            initial_tag_ids = [tag.id if hasattr(tag, 'id') else tag for tag in self.initial_tags]
            self.tag_selector.set_selected_tags(initial_tag_ids)

        tags_layout.addWidget(self.tag_selector)

        main_layout.addWidget(tags_group)

        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setFixedSize(100, 35)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
            QPushButton:pressed {
                background-color: #5d6d7e;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Agregar")
        ok_btn.setFixedSize(100, 35)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        ok_btn.clicked.connect(self._on_accept)
        ok_btn.setDefault(True)
        buttons_layout.addWidget(ok_btn)

        main_layout.addLayout(buttons_layout)

        # Aplicar estilos generales
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
            }
        """)

    def _on_accept(self):
        """Maneja el clic en aceptar"""
        self.content = self.content_edit.toPlainText().strip()
        self.selected_tag_ids = self.tag_selector.get_selected_tags()
        self.accept()

    def get_content(self) -> str:
        """Retorna el contenido ingresado"""
        return self.content

    def get_selected_tag_ids(self) -> list:
        """Retorna los IDs de tags seleccionados"""
        return self.selected_tag_ids
