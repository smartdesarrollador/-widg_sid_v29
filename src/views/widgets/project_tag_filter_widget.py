"""
Project Tag Filter Widget - Widget para filtrar elementos por tags

Widget estilo Dashboard con lista de checkboxes de tags para filtrar
elementos de proyecto en tiempo real.
"""

from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QScrollArea, QPushButton, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from src.core.project_element_tag_manager import ProjectElementTagManager


class ProjectTagFilterWidget(QWidget):
    """
    Widget para filtrar elementos por tags - Estilo Dashboard

    Muestra lista de tags disponibles con checkboxes para
    filtrar elementos del proyecto.
    """

    # Señales
    filter_changed = pyqtSignal(list, bool)  # tag_ids, match_all

    def __init__(self, tag_manager: ProjectElementTagManager, project_id: int = None, parent=None):
        """
        Inicializa el widget

        Args:
            tag_manager: Manager de tags
            project_id: ID del proyecto (None = mostrar todos los tags)
            parent: Widget padre
        """
        super().__init__(parent)
        self.tag_manager = tag_manager
        self.project_id = project_id
        self.tag_checkboxes = {}  # {tag_id: QCheckBox}
        self.match_all = False  # False = OR logic, True = AND logic
        self._setup_ui()
        self._load_tags()

        # Conectar señal de cache invalidado para refrescar
        self.tag_manager.cache_invalidated.connect(self._load_tags)

    def _setup_ui(self):
        """Configura la UI del widget"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(4)

        # Título
        title = QLabel("🏷️ Filtro por Tags")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #ecf0f1; background: transparent; border: none;")
        header_layout.addWidget(title)

        # Contador
        self.count_label = QLabel("(0 tags)")
        self.count_label.setFont(QFont("Segoe UI", 9))
        self.count_label.setStyleSheet("color: #95a5a6; background: transparent; border: none;")
        header_layout.addWidget(self.count_label)

        layout.addWidget(header_frame)

        # Área scrolleable de tags
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #34495e;
                border: 1px solid #2c3e50;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                background-color: #2c3e50;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #7f8c8d;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #95a5a6;
            }
        """)

        # Container de checkboxes
        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(8, 8, 8, 8)
        self.tags_layout.setSpacing(4)
        self.tags_layout.addStretch()

        scroll.setWidget(self.tags_container)
        layout.addWidget(scroll, 1)  # Expandir

        # Checkbox "Coincidir todos"
        self.match_all_checkbox = QCheckBox("Coincidir todos (AND)")
        self.match_all_checkbox.setFont(QFont("Segoe UI", 9))
        self.match_all_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ecf0f1;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #7f8c8d;
                border-radius: 3px;
                background-color: #34495e;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border-color: #3498db;
            }
            QCheckBox::indicator:hover {
                border-color: #5dade2;
            }
        """)
        self.match_all_checkbox.stateChanged.connect(self._on_match_all_changed)
        layout.addWidget(self.match_all_checkbox)

        # Botones de control
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self.select_all_btn = QPushButton("✓ Todos")
        self.select_all_btn.setFont(QFont("Segoe UI", 9))
        self.select_all_btn.clicked.connect(self._select_all)
        buttons_layout.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("✗ Ninguno")
        self.select_none_btn.setFont(QFont("Segoe UI", 9))
        self.select_none_btn.clicked.connect(self._select_none)
        buttons_layout.addWidget(self.select_none_btn)

        layout.addLayout(buttons_layout)

        self._apply_button_styles()

    def _apply_button_styles(self):
        """Aplica estilos a los botones"""
        button_style = """
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5dade2;
            }
            QPushButton:pressed {
                background-color: #2980b9;
            }
        """
        self.select_all_btn.setStyleSheet(button_style)
        self.select_none_btn.setStyleSheet(button_style)

    def _load_tags(self):
        """Carga los tags disponibles"""
        # Limpiar checkboxes existentes
        for checkbox in self.tag_checkboxes.values():
            checkbox.deleteLater()
        self.tag_checkboxes.clear()

        # Remover widgets del layout (excepto el stretch)
        while self.tags_layout.count() > 1:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Obtener tags según el proyecto
        if self.project_id is not None:
            # Solo tags del proyecto específico
            tags_sorted = self.tag_manager.get_tags_for_project(self.project_id)
        else:
            # Todos los tags
            tags = self.tag_manager.get_all_tags(refresh=True)
            tags_sorted = self.tag_manager.get_tags_sorted()

        # Actualizar contador
        self.count_label.setText(f"({len(tags_sorted)} tags)")

        # Crear checkboxes
        for tag in tags_sorted:
            checkbox = QCheckBox(tag.name)
            checkbox.setFont(QFont("Segoe UI", 9))
            # Estilo con color de fondo que cambia al seleccionar
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: #ecf0f1;
                    spacing: 8px;
                    padding: 6px 10px;
                    border-radius: 4px;
                    background-color: transparent;
                }}
                QCheckBox:checked {{
                    background-color: {tag.color}33;
                    border: 1px solid {tag.color};
                }}
                QCheckBox:hover {{
                    background-color: {tag.color}22;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid {tag.color};
                    border-radius: 4px;
                    background-color: transparent;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {tag.color};
                    border: 2px solid {tag.color};
                }}
                QCheckBox::indicator:unchecked {{
                    background-color: #2c3e50;
                    border: 2px solid {tag.color};
                }}
                QCheckBox::indicator:hover {{
                    border-width: 3px;
                }}
            """)
            checkbox.stateChanged.connect(self._on_filter_changed)

            self.tag_checkboxes[tag.id] = checkbox
            # Insertar antes del stretch
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, checkbox)

    def _on_filter_changed(self):
        """Maneja cambio en filtros"""
        selected_tag_ids = self.get_selected_tag_ids()
        self.filter_changed.emit(selected_tag_ids, self.match_all)

    def _on_match_all_changed(self, state):
        """Maneja cambio en checkbox de match_all"""
        self.match_all = state == Qt.CheckState.Checked.value
        self._on_filter_changed()

    def _select_all(self):
        """Selecciona todos los tags"""
        # Crear lista de checkboxes antes de iterar para evitar RuntimeError
        checkboxes = list(self.tag_checkboxes.values())
        for checkbox in checkboxes:
            checkbox.setChecked(True)

    def _select_none(self):
        """Deselecciona todos los tags"""
        # Crear lista de checkboxes antes de iterar para evitar RuntimeError
        checkboxes = list(self.tag_checkboxes.values())
        for checkbox in checkboxes:
            checkbox.setChecked(False)

    def get_selected_tag_ids(self) -> List[int]:
        """
        Obtiene los IDs de tags seleccionados

        Returns:
            Lista de IDs de tags seleccionados
        """
        return [
            tag_id for tag_id, checkbox in self.tag_checkboxes.items()
            if checkbox.isChecked()
        ]

    def set_selected_tag_ids(self, tag_ids: List[int]):
        """
        Establece los tags seleccionados

        Args:
            tag_ids: Lista de IDs de tags a seleccionar
        """
        for tag_id, checkbox in self.tag_checkboxes.items():
            checkbox.setChecked(tag_id in tag_ids)

    def clear_filters(self):
        """Limpia todos los filtros"""
        self._select_none()
        self.match_all_checkbox.setChecked(False)

    def refresh(self):
        """Refresca la lista de tags"""
        self._load_tags()

    def set_project(self, project_id: int = None):
        """
        Cambia el proyecto y recarga los tags

        Args:
            project_id: ID del proyecto a mostrar (None = limpiar filtro)
        """
        self.project_id = project_id
        self.clear_filters()  # Limpiar selección
        self._load_tags()
