"""
Projects Window - Ventana de gestión de proyectos

MVP Features:
- Lista de proyectos con búsqueda
- Panel de detalles con información básica
- Modo Edición y Modo Vista Amigable
- Canvas con elementos y componentes ordenados
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QTextEdit, QScrollArea, QFrame,
                             QMessageBox, QColorDialog, QApplication, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
import logging

from src.core.project_manager import ProjectManager
from src.core.project_export_manager import ProjectExportManager
from src.database.db_manager import DBManager
from src.views.widgets.project_relation_widget import ProjectRelationWidget
from src.views.widgets.project_component_widget import ProjectComponentWidget
from src.views.widgets.project_card_widget import ProjectCardWidget
from src.views.widgets.responsive_card_grid import ResponsiveCardGrid

logger = logging.getLogger(__name__)


class ProjectsWindow(QMainWindow):
    """Ventana principal de gestión de proyectos"""

    closed = pyqtSignal()

    def __init__(self, db_manager: DBManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_manager = ProjectManager(db_manager)
        self.export_manager = ProjectExportManager(db_manager)
        self.current_project_id = None
        self._view_mode = 'edit'  # 'edit' o 'clean'
        self._selected_insert_position = None  # (item_type, item_id, order_index) del elemento seleccionado

        self.init_ui()
        self.load_projects()

        logger.info("ProjectsWindow initialized")

    def init_ui(self):
        """Inicializa la interfaz"""
        self.setWindowTitle("📁 Gestión de Proyectos")
        self.showMaximized()  # Maximizada por defecto

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal horizontal
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Panel izquierdo: Lista de proyectos (20%)
        left_panel = self._create_projects_list_panel()
        left_panel.setMaximumWidth(300)
        main_layout.addWidget(left_panel, 1)

        # Panel central: Espacio del proyecto (60%)
        center_panel = self._create_project_space_panel()
        main_layout.addWidget(center_panel, 3)

        # Panel derecho: Filtros por tags (20%)
        right_panel = self._create_tag_filter_panel()
        right_panel.setMaximumWidth(250)
        main_layout.addWidget(right_panel, 1)

        # Styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #00ff88;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                padding: 8px;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                padding: 8px;
                border-radius: 4px;
            }
            QLabel {
                color: #ffffff;
            }
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #00ff88;
                color: #000000;
            }
        """)

    def _create_projects_list_panel(self) -> QWidget:
        """Crea el panel izquierdo con lista de proyectos"""
        panel = QWidget()
        panel.setStyleSheet("background-color: #252525; border-right: 2px solid #3d3d3d;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("📁 Mis Proyectos")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Búsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar proyectos...")
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)

        # Botón nuevo proyecto
        new_btn = QPushButton("+ Nuevo Proyecto")
        new_btn.clicked.connect(self.on_new_project)
        layout.addWidget(new_btn)

        # Botones de importar/exportar
        import_export_layout = QHBoxLayout()

        import_btn = QPushButton("📥 Importar")
        import_btn.setToolTip("Importar proyecto desde JSON")
        import_btn.clicked.connect(self.on_import_project)
        import_export_layout.addWidget(import_btn)

        export_btn = QPushButton("📤 Exportar")
        export_btn.setToolTip("Exportar proyecto seleccionado a JSON")
        export_btn.clicked.connect(self.on_export_project)
        import_export_layout.addWidget(export_btn)

        layout.addLayout(import_export_layout)

        # Lista de proyectos
        self.projects_list = QListWidget()
        self.projects_list.itemClicked.connect(self.on_project_selected)
        layout.addWidget(self.projects_list)

        return panel

    def _create_project_space_panel(self) -> QWidget:
        """Crea el panel derecho con espacio del proyecto"""
        panel = QWidget()
        panel.setStyleSheet("background-color: #1e1e1e;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header con info del proyecto y toggle de modo
        header_layout = QHBoxLayout()

        self.project_name_label = QLabel("Selecciona un proyecto")
        self.project_name_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(self.project_name_label)

        header_layout.addStretch()

        # Botón refrescar proyecto
        self.refresh_btn = QPushButton("🔄 Actualizar")
        self.refresh_btn.setVisible(False)  # Oculto hasta seleccionar proyecto
        self.refresh_btn.clicked.connect(self.on_refresh_project)
        self.refresh_btn.setToolTip("Actualizar la vista del proyecto")
        header_layout.addWidget(self.refresh_btn)

        # Botón editar proyecto
        self.edit_project_btn = QPushButton("✏️ Editar")
        self.edit_project_btn.setVisible(False)  # Oculto hasta seleccionar proyecto
        self.edit_project_btn.clicked.connect(self.on_edit_project)
        header_layout.addWidget(self.edit_project_btn)

        # Toggle modo vista
        self.mode_toggle_btn = QPushButton("👁️ Vista Limpia")
        self.mode_toggle_btn.clicked.connect(self.toggle_view_mode)
        header_layout.addWidget(self.mode_toggle_btn)

        layout.addLayout(header_layout)

        # Descripción
        self.project_desc_label = QLabel("")
        self.project_desc_label.setWordWrap(True)
        layout.addWidget(self.project_desc_label)

        # Toolbar (solo en modo edición)
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)

        # Canvas scrollable para modo edición (lista vertical)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        self.canvas_widget = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_widget)
        self.canvas_layout.setSpacing(5)
        self.canvas_layout.addStretch()

        scroll.setWidget(self.canvas_widget)
        self.edit_mode_container = scroll
        layout.addWidget(self.edit_mode_container)

        # Grid responsive para modo limpio (cards)
        self.clean_mode_grid = ResponsiveCardGrid()
        self.clean_mode_grid.setVisible(False)  # Oculto por defecto
        layout.addWidget(self.clean_mode_grid)

        # Botones inferiores (solo en modo edición)
        self.bottom_buttons = QWidget()
        bottom_layout = QHBoxLayout(self.bottom_buttons)

        save_btn = QPushButton("💾 Guardar")
        save_btn.clicked.connect(self.on_save)
        bottom_layout.addWidget(save_btn)

        close_btn = QPushButton("❌ Cerrar")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)

        layout.addWidget(self.bottom_buttons)

        return panel

    def _create_tag_filter_panel(self) -> QWidget:
        """Crea el panel derecho con filtros por tags"""
        panel = QWidget()
        panel.setStyleSheet("background-color: #252525; border-left: 2px solid #3d3d3d;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(0)

        # Importar widget de filtro
        from src.core.project_element_tag_manager import ProjectElementTagManager
        from src.views.widgets.project_tag_filter_widget import ProjectTagFilterWidget

        # Crear tag manager
        self.tag_manager = ProjectElementTagManager(self.db)

        # Crear widget de filtro
        self.tag_filter_widget = ProjectTagFilterWidget(self.tag_manager)
        self.tag_filter_widget.filter_changed.connect(self._on_tag_filter_changed)
        layout.addWidget(self.tag_filter_widget)

        # Estado de filtros
        self.active_tag_filters = []
        self.tag_filter_match_all = False

        return panel

    def _create_toolbar(self) -> QWidget:
        """Crea el toolbar con botones para agregar elementos"""
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 10, 0, 10)

        # Botones para agregar elementos
        add_tag_btn = QPushButton("🏷️ Tag")
        add_tag_btn.clicked.connect(lambda: self.add_element_to_project('tag'))
        toolbar_layout.addWidget(add_tag_btn)

        add_item_btn = QPushButton("📄 Item")
        add_item_btn.clicked.connect(lambda: self.add_element_to_project('item'))
        toolbar_layout.addWidget(add_item_btn)

        add_category_btn = QPushButton("📂 Categoría")
        add_category_btn.clicked.connect(lambda: self.add_element_to_project('category'))
        toolbar_layout.addWidget(add_category_btn)

        add_list_btn = QPushButton("📋 Lista")
        add_list_btn.clicked.connect(lambda: self.add_element_to_project('list'))
        toolbar_layout.addWidget(add_list_btn)

        add_table_btn = QPushButton("📊 Tabla")
        add_table_btn.clicked.connect(lambda: self.add_element_to_project('table'))
        toolbar_layout.addWidget(add_table_btn)

        add_process_btn = QPushButton("⚙️ Proceso")
        add_process_btn.clicked.connect(lambda: self.add_element_to_project('process'))
        toolbar_layout.addWidget(add_process_btn)

        # Separador
        sep = QLabel("|")
        sep.setStyleSheet("color: #555555; font-size: 16pt;")
        toolbar_layout.addWidget(sep)

        # Componentes estructurales
        add_comment_btn = QPushButton("💬 Comentario")
        add_comment_btn.clicked.connect(lambda: self.add_component('comment'))
        toolbar_layout.addWidget(add_comment_btn)

        add_note_btn = QPushButton("📌 Nota")
        add_note_btn.clicked.connect(lambda: self.add_component('note'))
        toolbar_layout.addWidget(add_note_btn)

        add_alert_btn = QPushButton("⚠️ Alerta")
        add_alert_btn.clicked.connect(lambda: self.add_component('alert'))
        toolbar_layout.addWidget(add_alert_btn)

        add_divider_btn = QPushButton("─ Divisor")
        add_divider_btn.clicked.connect(lambda: self.add_component('divider'))
        toolbar_layout.addWidget(add_divider_btn)

        toolbar_layout.addStretch()

        return toolbar

    # ==================== EVENTOS ====================

    def load_projects(self):
        """Carga todos los proyectos en la lista"""
        self.projects_list.clear()
        projects = self.project_manager.get_all_projects(active_only=True)

        for project in projects:
            item = QListWidgetItem(f"{project['icon']} {project['name']}")
            item.setData(Qt.ItemDataRole.UserRole, project['id'])
            self.projects_list.addItem(item)

    def on_search_changed(self, text):
        """Filtra proyectos por búsqueda"""
        if not text:
            self.load_projects()
            return

        results = self.project_manager.search_projects(text)
        self.projects_list.clear()

        for project in results:
            item = QListWidgetItem(f"{project['icon']} {project['name']}")
            item.setData(Qt.ItemDataRole.UserRole, project['id'])
            self.projects_list.addItem(item)

    def on_new_project(self):
        """Crea un nuevo proyecto"""
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "Nuevo Proyecto", "Nombre del proyecto:")
        if ok and name:
            project = self.project_manager.create_project(name)
            if project:
                self.load_projects()
                QMessageBox.information(self, "Éxito", f"Proyecto '{name}' creado")
            else:
                QMessageBox.warning(self, "Error", "No se pudo crear el proyecto")

    def on_project_selected(self, item):
        """Cuando se selecciona un proyecto de la lista"""
        project_id = item.data(Qt.ItemDataRole.UserRole)
        self.load_project(project_id)

    def load_project(self, project_id: int):
        """Carga un proyecto y muestra su contenido"""
        self.current_project_id = project_id
        project = self.project_manager.get_project(project_id)

        if not project:
            return

        # Actualizar header
        self.project_name_label.setText(f"{project['icon']} {project['name']}")
        self.project_desc_label.setText(project['description'])
        self.refresh_btn.setVisible(True)  # Mostrar botón refrescar
        self.edit_project_btn.setVisible(True)  # Mostrar botón editar

        # Actualizar filtro de tags para mostrar solo tags de este proyecto
        if hasattr(self, 'tag_filter_widget'):
            self.tag_filter_widget.set_project(project_id)

        # Limpiar canvas y grid
        self._clear_canvas()
        self.clean_mode_grid.clear_cards()

        # Cargar contenido ordenado
        content = self.db.get_project_content_ordered(project_id)

        # Aplicar filtros de tags si están activos
        if self.active_tag_filters:
            content = self._filter_content_by_tags(content)

        # Cargar según el modo actual
        if self._view_mode == 'edit':
            # Modo edición: usar widgets verticales
            for item in content:
                if item['type'] == 'relation':
                    self._add_relation_widget(item)
                else:  # component
                    self._add_component_widget(item)
        else:
            # Modo limpio: usar cards en grid
            for item in content:
                self._add_card_widget(item)

    def _clear_canvas(self):
        """Limpia el canvas eliminando todos los widgets"""
        while self.canvas_layout.count() > 1:  # Mantener el stretch
            child = self.canvas_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _add_relation_widget(self, relation):
        """Agrega un widget de relación al canvas"""
        # Obtener metadata
        metadata = self.project_manager.get_entity_metadata(
            relation['entity_type'],
            relation['entity_id']
        )

        # Crear widget especializado
        widget = ProjectRelationWidget(
            relation_data=relation,
            metadata=metadata,
            view_mode=self._view_mode,
            parent=self.canvas_widget
        )

        # Conectar señales
        widget.copy_requested.connect(self._copy_to_clipboard)
        widget.delete_requested.connect(self._on_relation_delete)
        widget.edit_description_requested.connect(self._on_relation_description_edit)
        widget.move_up_requested.connect(self._on_move_up)
        widget.move_down_requested.connect(self._on_move_down)
        widget.checkbox_changed.connect(lambda relation_id, checked: self._on_checkbox_changed('relation', relation_id, relation, checked))

        self.canvas_layout.insertWidget(self.canvas_layout.count() - 1, widget)

    def _add_component_widget(self, component):
        """Agrega un widget de componente al canvas"""
        # Obtener y agregar tags del componente
        component_id = component.get('id')
        if component_id:
            tags_data = self.db.get_tags_for_project_component(component_id)
            # Convertir a objetos ProjectElementTag
            from src.models.project_element_tag import create_tag_from_db_row
            tags = [create_tag_from_db_row(tag_data) for tag_data in tags_data]
            component['tags'] = tags

        # Crear widget especializado
        widget = ProjectComponentWidget(
            component_data=component,
            view_mode=self._view_mode,
            parent=self.canvas_widget
        )

        # Conectar señales
        widget.delete_requested.connect(self._on_component_delete)
        widget.edit_content_requested.connect(self._on_component_content_edit)
        widget.move_up_requested.connect(self._on_move_up)
        widget.move_down_requested.connect(self._on_move_down)
        widget.checkbox_changed.connect(lambda component_id, checked: self._on_checkbox_changed('component', component_id, component, checked))

        self.canvas_layout.insertWidget(self.canvas_layout.count() - 1, widget)

    def _add_card_widget(self, item):
        """Agrega una card al grid (modo limpio)"""
        # Determinar tipo de elemento
        if item.get('entity_type'):
            # Es una relación (tag, item, category, list, table, process)
            entity_type = item['entity_type']

            # Obtener metadata del elemento
            metadata = self.project_manager.get_entity_metadata(
                entity_type,
                item['entity_id']
            )

            # Agregar descripción de la relación a la metadata
            metadata['description'] = item.get('description', '')

            # Obtener y agregar tags de la relación
            relation_id = item.get('id')
            if relation_id:
                tags_data = self.db.get_tags_for_project_relation(relation_id)
                # Convertir a objetos ProjectElementTag
                from src.models.project_element_tag import create_tag_from_db_row
                tags = [create_tag_from_db_row(tag_data) for tag_data in tags_data]
                metadata['tags'] = tags

            # Crear card
            card = ProjectCardWidget(
                item_data=metadata,
                item_type=entity_type,
                parent=self.clean_mode_grid
            )

        else:
            # Es un componente (comment, alert, note, divider)
            component_type = item['component_type']

            # Saltar divisores en modo limpio (no tienen sentido en grid)
            if component_type == 'divider':
                return

            # Preparar datos para la card
            card_data = {
                'name': f"{component_type.title()}",
                'content': item.get('content', ''),
                'icon': ProjectCardWidget.TYPE_ICONS.get(component_type, '💬')
            }

            # Obtener y agregar tags del componente
            component_id = item.get('id')
            if component_id:
                tags_data = self.db.get_tags_for_project_component(component_id)
                # Convertir a objetos ProjectElementTag
                from src.models.project_element_tag import create_tag_from_db_row
                tags = [create_tag_from_db_row(tag_data) for tag_data in tags_data]
                card_data['tags'] = tags

            # Crear card
            card = ProjectCardWidget(
                item_data=card_data,
                item_type=component_type,
                parent=self.clean_mode_grid
            )

        # Conectar señal de click para copiar
        card.clicked.connect(self._copy_to_clipboard)

        # Agregar card al grid
        self.clean_mode_grid.add_card(card)

    def _on_relation_delete(self, relation_id: int):
        """Maneja eliminación de relación"""
        try:
            success = self.db.remove_project_relation(relation_id)
            if success:
                logger.info(f"Relation {relation_id} deleted")
                self.load_project(self.current_project_id)
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar la relación")
        except Exception as e:
            logger.error(f"Error deleting relation: {e}")
            QMessageBox.critical(self, "Error", f"Error al eliminar: {str(e)}")

    def _on_relation_description_edit(self, relation_id: int, new_description: str):
        """Maneja edición de descripción de relación"""
        try:
            success = self.db.update_relation_description(relation_id, new_description)
            if success:
                logger.info(f"Relation {relation_id} description updated")
        except Exception as e:
            logger.error(f"Error updating relation description: {e}")

    def _on_component_delete(self, component_id: int):
        """Maneja eliminación de componente"""
        try:
            success = self.db.remove_project_component(component_id)
            if success:
                logger.info(f"Component {component_id} deleted")
                self.load_project(self.current_project_id)
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el componente")
        except Exception as e:
            logger.error(f"Error deleting component: {e}")
            QMessageBox.critical(self, "Error", f"Error al eliminar: {str(e)}")

    def _on_component_content_edit(self, component_id: int, new_content: str):
        """Maneja edición de contenido de componente"""
        try:
            success = self.db.update_component_content(component_id, new_content)
            if success:
                logger.info(f"Component {component_id} content updated")
        except Exception as e:
            logger.error(f"Error updating component content: {e}")

    def _on_checkbox_changed(self, item_type: str, item_id: int, item_data: dict, checked: bool):
        """Maneja cambio de checkbox para seleccionar posición de inserción"""
        if checked:
            # Guardar posición seleccionada
            self._selected_insert_position = (item_type, item_id, item_data.get('order_index'))
            logger.info(f"Insert position selected: {item_type} #{item_id} (order_index: {item_data.get('order_index')})")

            # Desmarcar todos los demás checkboxes
            self._uncheck_all_except(item_type, item_id)
        else:
            # Si se desmarca, limpiar posición seleccionada
            if self._selected_insert_position and self._selected_insert_position[1] == item_id:
                self._selected_insert_position = None
                logger.info("Insert position cleared")

    def _uncheck_all_except(self, except_type: str, except_id: int):
        """Desmarca todos los checkboxes excepto el especificado"""
        # Iterar sobre todos los widgets en el canvas
        for i in range(self.canvas_layout.count() - 1):  # -1 para excluir el stretch
            widget = self.canvas_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'checkbox'):
                # Determinar el ID del widget
                widget_id = None
                widget_type = None

                if isinstance(widget, ProjectRelationWidget):
                    widget_id = widget.relation_data.get('id')
                    widget_type = 'relation'
                elif isinstance(widget, ProjectComponentWidget):
                    widget_id = widget.component_data.get('id')
                    widget_type = 'component'

                # Si no es el widget excepto, desmarcar
                if widget_id and (widget_type != except_type or widget_id != except_id):
                    widget.checkbox.blockSignals(True)  # Bloquear señales para evitar recursión
                    widget.checkbox.setChecked(False)
                    widget.checkbox.blockSignals(False)

    def _shift_order_indices_down(self, from_order: int):
        """Incrementa el order_index de todos los elementos >= from_order"""
        if not self.current_project_id:
            return

        try:
            # Obtener todo el contenido
            content = self.db.get_project_content_ordered(self.current_project_id)

            # Incrementar order_index de elementos >= from_order
            for item in content:
                current_order = item.get('order_index')
                if current_order is not None and current_order >= from_order:
                    new_order = current_order + 1

                    # Determinar tipo y actualizar
                    if item.get('entity_type') is not None:
                        self.db.update_relation_order(item['id'], new_order)
                        logger.info(f"Shifted relation {item['id']} from {current_order} to {new_order}")
                    elif item.get('component_type') is not None:
                        self.db.update_component_order(item['id'], new_order)
                        logger.info(f"Shifted component {item['id']} from {current_order} to {new_order}")

        except Exception as e:
            logger.error(f"Error shifting order indices: {e}")

    def _on_move_up(self, item_id: int):
        """Maneja mover elemento hacia arriba"""
        if not self.current_project_id:
            return

        try:
            logger.info(f"Move up requested for item_id: {item_id}")

            # Obtener todo el contenido ordenado
            content = self.db.get_project_content_ordered(self.current_project_id)
            logger.info(f"Total content items: {len(content)}")

            # Encontrar el índice del item
            current_index = None
            for i, item in enumerate(content):
                # Verificar si es relación o componente
                # Un item es relación si entity_type NO es NULL
                # Un item es componente si component_type NO es NULL
                if item.get('id') == item_id:
                    current_index = i
                    if item.get('entity_type') is not None:
                        logger.info(f"Found relation at index {i}, entity_type: {item.get('entity_type')}")
                    elif item.get('component_type') is not None:
                        logger.info(f"Found component at index {i}, type: {item.get('component_type')}")
                    break

            if current_index is None:
                logger.warning(f"Item {item_id} not found in content")
                return

            if current_index == 0:
                logger.info("Item already at top")
                return  # Ya está al inicio

            # Intercambiar order_index con el elemento anterior
            current_item = content[current_index]
            prev_item = content[current_index - 1]

            logger.info(f"Swapping: current order_index={current_item['order_index']}, prev order_index={prev_item['order_index']}")

            # Actualizar order_index
            # Determinar tipo del item actual
            if current_item.get('entity_type') is not None:
                logger.info(f"Updating relation {current_item['id']} (type: {current_item['entity_type']}) to order {prev_item['order_index']}")
                self.db.update_relation_order(current_item['id'], prev_item['order_index'])
            elif current_item.get('component_type') is not None:
                logger.info(f"Updating component {current_item['id']} (type: {current_item['component_type']}) to order {prev_item['order_index']}")
                self.db.update_component_order(current_item['id'], prev_item['order_index'])

            # Determinar tipo del item anterior
            if prev_item.get('entity_type') is not None:
                logger.info(f"Updating relation {prev_item['id']} (type: {prev_item['entity_type']}) to order {current_item['order_index']}")
                self.db.update_relation_order(prev_item['id'], current_item['order_index'])
            elif prev_item.get('component_type') is not None:
                logger.info(f"Updating component {prev_item['id']} (type: {prev_item['component_type']}) to order {current_item['order_index']}")
                self.db.update_component_order(prev_item['id'], current_item['order_index'])

            # Recargar proyecto
            logger.info("Reloading project after move")
            self.load_project(self.current_project_id)

        except Exception as e:
            logger.error(f"Error moving item up: {e}")

    def _on_move_down(self, item_id: int):
        """Maneja mover elemento hacia abajo"""
        if not self.current_project_id:
            return

        try:
            logger.info(f"Move down requested for item_id: {item_id}")

            # Obtener todo el contenido ordenado
            content = self.db.get_project_content_ordered(self.current_project_id)
            logger.info(f"Total content items: {len(content)}")

            # Encontrar el índice del item
            current_index = None
            for i, item in enumerate(content):
                # Verificar si es relación o componente
                # Un item es relación si entity_type NO es NULL
                # Un item es componente si component_type NO es NULL
                if item.get('id') == item_id:
                    current_index = i
                    if item.get('entity_type') is not None:
                        logger.info(f"Found relation at index {i}, entity_type: {item.get('entity_type')}")
                    elif item.get('component_type') is not None:
                        logger.info(f"Found component at index {i}, type: {item.get('component_type')}")
                    break

            if current_index is None:
                logger.warning(f"Item {item_id} not found in content")
                return

            if current_index >= len(content) - 1:
                logger.info("Item already at bottom")
                return  # Ya está al final

            # Intercambiar order_index con el elemento siguiente
            current_item = content[current_index]
            next_item = content[current_index + 1]

            logger.info(f"Swapping: current order_index={current_item['order_index']}, next order_index={next_item['order_index']}")

            # Actualizar order_index
            # Determinar tipo del item actual
            if current_item.get('entity_type') is not None:
                logger.info(f"Updating relation {current_item['id']} (type: {current_item['entity_type']}) to order {next_item['order_index']}")
                self.db.update_relation_order(current_item['id'], next_item['order_index'])
            elif current_item.get('component_type') is not None:
                logger.info(f"Updating component {current_item['id']} (type: {current_item['component_type']}) to order {next_item['order_index']}")
                self.db.update_component_order(current_item['id'], next_item['order_index'])

            # Determinar tipo del item siguiente
            if next_item.get('entity_type') is not None:
                logger.info(f"Updating relation {next_item['id']} (type: {next_item['entity_type']}) to order {current_item['order_index']}")
                self.db.update_relation_order(next_item['id'], current_item['order_index'])
            elif next_item.get('component_type') is not None:
                logger.info(f"Updating component {next_item['id']} (type: {next_item['component_type']}) to order {current_item['order_index']}")
                self.db.update_component_order(next_item['id'], current_item['order_index'])

            # Recargar proyecto
            logger.info("Reloading project after move")
            self.load_project(self.current_project_id)

        except Exception as e:
            logger.error(f"Error moving item down: {e}")

    def _copy_to_clipboard(self, text: str):
        """Copia texto al portapapeles"""
        QApplication.clipboard().setText(text)
        logger.info(f"Copied to clipboard: {text[:50]}...")

    def toggle_view_mode(self):
        """Alterna entre Modo Edición y Modo Vista Amigable"""
        if self._view_mode == 'edit':
            self._view_mode = 'clean'
            self._apply_clean_view_mode()
        else:
            self._view_mode = 'edit'
            self._apply_edit_view_mode()

    def _apply_edit_view_mode(self):
        """Aplica estilo de Modo Edición"""
        self.toolbar.setVisible(True)
        self.bottom_buttons.setVisible(True)
        self.mode_toggle_btn.setText("👁️ Vista Limpia")

        # Mostrar container de modo edición, ocultar grid
        self.edit_mode_container.setVisible(True)
        self.clean_mode_grid.setVisible(False)

        if self.current_project_id:
            self.load_project(self.current_project_id)

    def _apply_clean_view_mode(self):
        """Aplica estilo de Modo Vista Amigable (Grid de Cards)"""
        self.toolbar.setVisible(False)
        self.bottom_buttons.setVisible(False)
        self.mode_toggle_btn.setText("📝 Modo Edición")

        # Ocultar container de modo edición, mostrar grid
        self.edit_mode_container.setVisible(False)
        self.clean_mode_grid.setVisible(True)

        if self.current_project_id:
            self.load_project(self.current_project_id)

    def add_element_to_project(self, entity_type: str):
        """Agrega un elemento al proyecto"""
        if not self.current_project_id:
            QMessageBox.warning(self, "Error", "Selecciona un proyecto primero")
            return

        try:
            # Abrir selector de entidad
            from src.views.dialogs.project_entity_selector import ProjectEntitySelector

            selector = ProjectEntitySelector(
                entity_type=entity_type,
                db_manager=self.db,
                project_id=self.current_project_id,  # Pasar project_id
                parent=self
            )

            # Conectar señal
            selector.entity_selected.connect(self._on_entity_selected)

            selector.exec()

        except Exception as e:
            logger.error(f"Error opening entity selector: {e}")
            QMessageBox.critical(self, "Error", f"Error al abrir selector:\n{str(e)}")

    def _on_entity_selected(self, entity_type: str, entity_id: int, description: str, tag_ids: list = None):
        """Maneja la selección de una entidad desde el selector"""
        try:
            if tag_ids is None:
                tag_ids = []

            # Calcular order_index basado en posición seleccionada
            order_index = None
            if self._selected_insert_position:
                # Insertar debajo del elemento seleccionado
                # order_index = order_index_seleccionado + 1
                selected_order = self._selected_insert_position[2]
                if selected_order is not None:
                    order_index = selected_order + 1
                    logger.info(f"Inserting below position {selected_order}, new order_index: {order_index}")

                    # Incrementar order_index de todos los elementos posteriores
                    self._shift_order_indices_down(selected_order + 1)

            success = self.project_manager.add_entity_to_project(
                self.current_project_id, entity_type, entity_id, description, order_index
            )

            if success:
                # Obtener el relation_id recién creado para asociar tags
                relations = self.db.get_project_relations(self.current_project_id)
                if relations:
                    # El último creado debería ser el nuestro
                    new_relation = max(relations, key=lambda r: r['id'])
                    relation_id = new_relation['id']

                    # Asociar tags si hay
                    if tag_ids:
                        from src.core.project_element_tag_manager import ProjectElementTagManager
                        tag_manager = ProjectElementTagManager(self.db)
                        tag_manager.assign_tags_to_relation(relation_id, tag_ids)
                        logger.info(f"Assigned {len(tag_ids)} tags to relation {relation_id}")

                logger.info(f"Added {entity_type} #{entity_id} to project {self.current_project_id}")
                self.load_project(self.current_project_id)
                QMessageBox.information(self, "Éxito", f"{entity_type.title()} agregado al proyecto")
            else:
                QMessageBox.warning(self, "Error", "No se pudo agregar el elemento")

        except Exception as e:
            logger.error(f"Error adding entity to project: {e}")
            QMessageBox.critical(self, "Error", f"Error al agregar:\n{str(e)}")

    def add_component(self, component_type: str):
        """Agrega un componente estructural"""
        if not self.current_project_id:
            QMessageBox.warning(self, "Error", "Selecciona un proyecto primero")
            return

        content = ""
        tag_ids = []

        if component_type != 'divider':
            # Usar diálogo personalizado con selector de tags
            from src.views.dialogs.component_editor_dialog import ComponentEditorDialog

            dialog = ComponentEditorDialog(
                tag_manager=self.tag_manager,
                component_type=component_type,
                parent=self
            )

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            content = dialog.get_content()
            tag_ids = dialog.get_selected_tag_ids()

        # Calcular order_index basado en posición seleccionada
        order_index = None
        if self._selected_insert_position:
            # Insertar debajo del elemento seleccionado
            selected_order = self._selected_insert_position[2]
            if selected_order is not None:
                order_index = selected_order + 1
                logger.info(f"Inserting component below position {selected_order}, new order_index: {order_index}")

                # Incrementar order_index de todos los elementos posteriores
                self._shift_order_indices_down(selected_order + 1)

        # Agregar componente
        success = self.project_manager.add_component_to_project(
            self.current_project_id, component_type, content, order_index
        )

        if success:
            # Si se agregó exitosamente y hay tags, asociarlos al componente
            if tag_ids:
                # Obtener el ID del componente recién creado
                # Necesitamos obtener el último componente agregado
                components = self.db.get_project_components(self.current_project_id)
                if components:
                    # El último componente es el recién agregado
                    new_component = components[-1]
                    component_id = new_component['id']

                    # Asociar tags al componente
                    self.tag_manager.assign_tags_to_component(component_id, tag_ids)
                    logger.info(f"Tags asignados al componente {component_id}: {tag_ids}")

            self.load_project(self.current_project_id)

    def _filter_content_by_tags(self, content: list) -> list:
        """
        Filtra el contenido por tags seleccionados

        Args:
            content: Lista de elementos del proyecto

        Returns:
            Lista filtrada de elementos
        """
        if not self.active_tag_filters:
            return content

        filtered = []

        for item in content:
            item_tags_ids = []

            # Obtener tags según el tipo de elemento
            if item['type'] == 'relation':
                # Obtener tags de la relación
                relation_id = item.get('id')
                relation_tags = self.tag_manager.get_relation_tags(relation_id)
                item_tags_ids = [tag.id for tag in relation_tags]
            elif item['type'] == 'component':
                # Obtener tags del componente
                component_id = item.get('id')
                component_tags = self.tag_manager.get_tags_for_component(component_id)
                item_tags_ids = [tag.id for tag in component_tags]

            # Aplicar lógica de filtro
            if self.tag_filter_match_all:
                # AND: debe tener TODOS los tags
                if all(tag_id in item_tags_ids for tag_id in self.active_tag_filters):
                    filtered.append(item)
            else:
                # OR: debe tener AL MENOS uno
                if any(tag_id in item_tags_ids for tag_id in self.active_tag_filters):
                    filtered.append(item)

        logger.debug(f"Filtered {len(content)} items to {len(filtered)} items")
        return filtered

    def _on_tag_filter_changed(self, tag_ids: list, match_all: bool):
        """Maneja cambio en filtros de tags"""
        self.active_tag_filters = tag_ids
        self.tag_filter_match_all = match_all

        logger.info(f"Tag filters changed: {len(tag_ids)} tags, match_all={match_all}")

        # Recargar proyecto con filtros
        if self.current_project_id:
            self.load_project(self.current_project_id)

    def on_refresh_project(self):
        """Recarga el proyecto actual sin cerrar la ventana"""
        if not self.current_project_id:
            return

        logger.info(f"Refreshing project {self.current_project_id}")
        self.load_project(self.current_project_id)

    def on_edit_project(self):
        """Abre el diálogo de edición de proyecto"""
        if not self.current_project_id:
            return

        try:
            from src.views.dialogs.project_editor_dialog import ProjectEditorDialog

            # Obtener datos del proyecto
            project = self.project_manager.get_project(self.current_project_id)
            if not project:
                QMessageBox.warning(self, "Error", "No se pudo cargar el proyecto")
                return

            # Abrir diálogo
            dialog = ProjectEditorDialog(
                project_data=project,
                db_manager=self.db,
                parent=self
            )

            # Conectar señal
            dialog.project_updated.connect(self._on_project_updated)

            result = dialog.exec()

            # Si se eliminó el proyecto, limpiar vista
            if result == QDialog.DialogCode.Accepted:
                # Verificar si el proyecto todavía existe
                updated_project = self.project_manager.get_project(self.current_project_id)
                if not updated_project:
                    # Proyecto eliminado
                    self.current_project_id = None
                    self.project_name_label.setText("Selecciona un proyecto")
                    self.project_desc_label.setText("")
                    self.refresh_btn.setVisible(False)
                    self.edit_project_btn.setVisible(False)
                    self._clear_canvas()

                    # Limpiar filtro de tags
                    if hasattr(self, 'tag_filter_widget'):
                        self.tag_filter_widget.set_project(None)

                    self.load_projects()

        except Exception as e:
            logger.error(f"Error opening project editor: {e}")
            QMessageBox.critical(self, "Error", f"Error al abrir editor:\n{str(e)}")

    def _on_project_updated(self, project_id: int):
        """Maneja la actualización de un proyecto"""
        # Recargar proyectos en la lista
        self.load_projects()

        # Recargar proyecto actual si es el mismo
        if project_id == self.current_project_id:
            self.load_project(project_id)

    def on_export_project(self):
        """Maneja la exportación del proyecto actual"""
        if not self.current_project_id:
            QMessageBox.warning(self, "Error", "Selecciona un proyecto primero")
            return

        try:
            from src.views.dialogs.project_export_dialog import ProjectExportDialog

            project = self.project_manager.get_project(self.current_project_id)
            if not project:
                QMessageBox.warning(self, "Error", "No se pudo cargar el proyecto")
                return

            dialog = ProjectExportDialog(
                project_data=project,
                export_manager=self.export_manager,
                parent=self
            )

            dialog.export_completed.connect(self._on_export_completed)
            dialog.exec()

        except Exception as e:
            logger.error(f"Error abriendo diálogo de exportación: {e}")
            QMessageBox.critical(self, "Error", f"Error:\n{str(e)}")

    def _on_export_completed(self, file_path: str):
        """Maneja la finalización de la exportación"""
        logger.info(f"Exportación completada: {file_path}")

    def on_import_project(self):
        """Maneja la importación de un proyecto"""
        try:
            from src.views.dialogs.project_import_dialog import ProjectImportDialog

            dialog = ProjectImportDialog(
                export_manager=self.export_manager,
                parent=self
            )

            dialog.import_completed.connect(self._on_import_completed)
            dialog.exec()

        except Exception as e:
            logger.error(f"Error abriendo diálogo de importación: {e}")
            QMessageBox.critical(self, "Error", f"Error:\n{str(e)}")

    def _on_import_completed(self, project_id: int):
        """Maneja la finalización de la importación"""
        logger.info(f"Importación completada: Proyecto ID {project_id}")

        # Recargar lista de proyectos
        self.load_projects()

        # Seleccionar el proyecto importado
        self.load_project(project_id)

    def on_save(self):
        """Guarda cambios (placeholder)"""
        QMessageBox.information(self, "Info", "Los cambios se guardan automáticamente")

    def closeEvent(self, event):
        """Al cerrar la ventana"""
        logger.info("ProjectsWindow closed")
        self.closed.emit()
        event.accept()
