"""
Project Component Widget - Widgets para componentes estructurales

Componentes soportados:
- Divider: Línea divisoria horizontal
- Comment: Comentario informativo
- Alert: Alerta importante
- Note: Nota destacada
"""

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                             QLabel, QFrame, QTextEdit, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont
import logging

logger = logging.getLogger(__name__)


class ProjectComponentWidget(QWidget):
    """Widget base para componentes estructurales"""

    # Señales
    delete_requested = pyqtSignal(int)  # component_id
    edit_content_requested = pyqtSignal(int, str)  # component_id, new_content
    move_up_requested = pyqtSignal(int)  # component_id
    move_down_requested = pyqtSignal(int)  # component_id
    checkbox_changed = pyqtSignal(int, bool)  # component_id, checked

    def __init__(self, component_data: dict, view_mode: str = 'edit', parent=None):
        """
        Args:
            component_data: Diccionario con datos del componente (id, project_id, component_type, content, order_index)
            view_mode: 'edit' o 'clean'
        """
        super().__init__(parent)

        self.component_data = component_data
        self.view_mode = view_mode
        self.component_type = component_data['component_type']

        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz según el tipo de componente"""
        # Layout principal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        if self.component_type == 'divider':
            self._create_divider_widget(main_layout)
        elif self.component_type == 'comment':
            self._create_comment_widget(main_layout)
        elif self.component_type == 'alert':
            self._create_alert_widget(main_layout)
        elif self.component_type == 'note':
            self._create_note_widget(main_layout)

    def _create_divider_widget(self, parent_layout):
        """Crea el widget de divisor"""
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(5)

        # Línea divisoria
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        divider.setFixedHeight(3)  # Altura fija de 3px
        divider.setStyleSheet("""
            QFrame {
                background-color: #555555;
                border: none;
                margin: 12px 0;
            }
        """)
        container_layout.addWidget(divider, 1)

        # Controles de edición (solo en modo edición)
        if self.view_mode == 'edit':
            controls = self._create_control_buttons()
            container_layout.addWidget(controls)

        parent_layout.addWidget(container)

    def _create_comment_widget(self, parent_layout):
        """Crea el widget de comentario"""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #1e2a3a;
                border-left: 3px solid #00ccff;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(5)

        # Fila superior: Icono + Contenido + Controles
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Icono
        icon_label = QLabel("💬")
        icon_label.setStyleSheet("font-size: 14pt;")
        top_row.addWidget(icon_label)

        # Contenido
        content = self.component_data.get('content', '')
        if self.view_mode == 'edit':
            self.content_edit = QTextEdit()
            self.content_edit.setPlainText(content)
            self.content_edit.setMaximumHeight(60)
            self.content_edit.setPlaceholderText("Escribe tu comentario...")
            self.content_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #152130;
                    color: #00ccff;
                    border: 1px solid #2d3d4d;
                    border-radius: 3px;
                    padding: 6px;
                    font-size: 10pt;
                    font-style: italic;
                }
            """)
            self.content_edit.textChanged.connect(self.on_content_changed)
            top_row.addWidget(self.content_edit, 1)

            # Controles
            controls = self._create_control_buttons()
            top_row.addWidget(controls)
        else:
            # Modo clean: solo mostrar texto
            content_label = QLabel(content)
            content_label.setWordWrap(True)
            content_label.setStyleSheet("""
                QLabel {
                    color: #00ccff;
                    font-size: 10pt;
                    font-style: italic;
                }
            """)
            top_row.addWidget(content_label, 1)

        container_layout.addLayout(top_row)

        # Agregar tags si existen
        self._add_tags_display(container_layout)

        parent_layout.addWidget(container)

    def _create_alert_widget(self, parent_layout):
        """Crea el widget de alerta"""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #3d2d00;
                border: 2px solid #ffaa00;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(5)

        # Fila superior: Icono + Contenido + Controles
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Icono
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 16pt;")
        top_row.addWidget(icon_label)

        # Contenido
        content = self.component_data.get('content', '')
        if self.view_mode == 'edit':
            self.content_edit = QTextEdit()
            self.content_edit.setPlainText(content)
            self.content_edit.setMaximumHeight(60)
            self.content_edit.setPlaceholderText("Texto de la alerta...")
            self.content_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #2d1d00;
                    color: #ffaa00;
                    border: 1px solid #4d3d00;
                    border-radius: 3px;
                    padding: 6px;
                    font-size: 10pt;
                    font-weight: bold;
                }
            """)
            self.content_edit.textChanged.connect(self.on_content_changed)
            top_row.addWidget(self.content_edit, 1)

            # Controles
            controls = self._create_control_buttons()
            top_row.addWidget(controls)
        else:
            # Modo clean: solo mostrar texto
            content_label = QLabel(content)
            content_label.setWordWrap(True)
            content_label.setStyleSheet("""
                QLabel {
                    color: #ffaa00;
                    font-size: 10pt;
                    font-weight: bold;
                }
            """)
            top_row.addWidget(content_label, 1)

        container_layout.addLayout(top_row)

        # Agregar tags si existen
        self._add_tags_display(container_layout)

        parent_layout.addWidget(container)

    def _create_note_widget(self, parent_layout):
        """Crea el widget de nota"""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #002d1e;
                border-left: 4px solid #00ff88;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)
        container_layout.setSpacing(5)

        # Fila superior: Icono + Contenido + Controles
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Icono
        icon_label = QLabel("📌")
        icon_label.setStyleSheet("font-size: 14pt;")
        top_row.addWidget(icon_label)

        # Contenido
        content = self.component_data.get('content', '')
        if self.view_mode == 'edit':
            self.content_edit = QTextEdit()
            self.content_edit.setPlainText(content)
            self.content_edit.setMaximumHeight(60)
            self.content_edit.setPlaceholderText("Escribe tu nota...")
            self.content_edit.setStyleSheet("""
                QTextEdit {
                    background-color: #001d0e;
                    color: #00ff88;
                    border: 1px solid #003d2e;
                    border-radius: 3px;
                    padding: 6px;
                    font-size: 10pt;
                }
            """)
            self.content_edit.textChanged.connect(self.on_content_changed)
            top_row.addWidget(self.content_edit, 1)

            # Controles
            controls = self._create_control_buttons()
            top_row.addWidget(controls)
        else:
            # Modo clean: solo mostrar texto
            content_label = QLabel(content)
            content_label.setWordWrap(True)
            content_label.setStyleSheet("""
                QLabel {
                    color: #00ff88;
                    font-size: 10pt;
                }
            """)
            top_row.addWidget(content_label, 1)

        container_layout.addLayout(top_row)

        # Agregar tags si existen
        self._add_tags_display(container_layout)

        parent_layout.addWidget(container)

    def _create_control_buttons(self) -> QWidget:
        """Crea el widget con botones de control"""
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(3)

        # Checkbox para seleccionar posición de inserción
        self.checkbox = QCheckBox()
        self.checkbox.setToolTip("Marcar para insertar nuevos elementos debajo de este")
        self.checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4d4d4d;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:hover {
                border-color: #00ff88;
            }
            QCheckBox::indicator:checked {
                background-color: #00ff88;
                border-color: #00ff88;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #00ccff;
                border-color: #00ccff;
            }
        """)
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        controls_layout.addWidget(self.checkbox)

        # Botón mover arriba
        move_up_btn = QPushButton("▲")
        move_up_btn.setFixedSize(24, 24)
        move_up_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        move_up_btn.setStyleSheet(self._get_control_button_style())
        move_up_btn.setToolTip("Mover arriba")
        move_up_btn.clicked.connect(self.on_move_up)
        controls_layout.addWidget(move_up_btn)

        # Botón mover abajo
        move_down_btn = QPushButton("▼")
        move_down_btn.setFixedSize(24, 24)
        move_down_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        move_down_btn.setStyleSheet(self._get_control_button_style())
        move_down_btn.setToolTip("Mover abajo")
        move_down_btn.clicked.connect(self.on_move_down)
        controls_layout.addWidget(move_down_btn)

        # Botón eliminar
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 3px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #e4475b;
                border-color: #e4475b;
            }
        """)
        delete_btn.setToolTip("Eliminar componente")
        delete_btn.clicked.connect(self.on_delete)
        controls_layout.addWidget(delete_btn)

        return controls

    def _get_control_button_style(self) -> str:
        """Estilo para botones de control"""
        return """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 3px;
                font-size: 8pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00ff88;
                border-color: #00ff88;
                color: #000000;
            }
        """

    def _add_tags_display(self, layout):
        """Agrega la visualización de tags al componente"""
        # Obtener tags del component_data
        tags = self.component_data.get('tags', [])

        if not tags:
            return

        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(4)
        tags_layout.setContentsMargins(0, 4, 0, 0)

        # Mostrar máximo 5 tags
        max_visible_tags = 5
        visible_tags = tags[:max_visible_tags]

        for tag in visible_tags:
            chip = self._create_simple_tag_chip(tag)
            tags_layout.addWidget(chip)

        # Si hay más tags, mostrar indicador "+X más"
        if len(tags) > max_visible_tags:
            remaining = len(tags) - max_visible_tags
            more_label = QLabel(f"+{remaining}")
            more_label.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 7pt;
                    font-style: italic;
                    padding: 2px 6px;
                }
            """)
            tags_layout.addWidget(more_label)

        tags_layout.addStretch()
        layout.addLayout(tags_layout)

    def _create_simple_tag_chip(self, tag):
        """Crea un chip simple para mostrar un tag"""
        chip = QLabel(tag.name)
        chip.setFixedHeight(16)
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setStyleSheet(f"""
            QLabel {{
                background-color: {tag.color};
                color: #000000;
                font-size: 7pt;
                font-weight: bold;
                border-radius: 8px;
                padding: 2px 6px;
                border: 1px solid {tag.color};
            }}
        """)
        return chip

    def on_content_changed(self):
        """Al cambiar el contenido"""
        if self.view_mode == 'edit' and hasattr(self, 'content_edit'):
            new_content = self.content_edit.toPlainText()
            component_id = self.component_data['id']
            self.edit_content_requested.emit(component_id, new_content)

    def on_delete(self):
        """Al hacer clic en eliminar"""
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar este componente {self.component_type}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            component_id = self.component_data['id']
            self.delete_requested.emit(component_id)
            logger.info(f"Delete requested for component: {component_id}")

    def on_move_up(self):
        """Al hacer clic en mover arriba"""
        component_id = self.component_data['id']
        self.move_up_requested.emit(component_id)
        logger.info(f"Move up requested for component: {component_id}")

    def on_move_down(self):
        """Al hacer clic en mover abajo"""
        component_id = self.component_data['id']
        self.move_down_requested.emit(component_id)
        logger.info(f"Move down requested for component: {component_id}")

    def on_checkbox_changed(self, state):
        """Al cambiar el estado del checkbox"""
        if self.view_mode == 'edit' and hasattr(self, 'checkbox'):
            component_id = self.component_data['id']
            is_checked = state == Qt.CheckState.Checked.value
            self.checkbox_changed.emit(component_id, is_checked)
            logger.info(f"Checkbox changed for component {component_id}: {is_checked}")

    def set_view_mode(self, mode: str):
        """Cambia el modo de vista"""
        if mode != self.view_mode:
            self.view_mode = mode
            # Recrear el widget con el nuevo modo
            self.clear_layout()
            self.init_ui()

    def clear_layout(self):
        """Limpia el layout actual"""
        layout = self.layout()
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
