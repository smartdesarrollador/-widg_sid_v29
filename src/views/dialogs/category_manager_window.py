"""
Category Manager Window - CRUD interface for managing categories
FASE 3: Ventana de gestión con búsqueda, checkboxes y acciones
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QSizePolicy, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QCursor, QIcon
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models.category import Category
from views.widgets.category_list_item import CategoryListItem
from views.dialogs.category_form_dialog import CategoryFormDialog

# Get logger
logger = logging.getLogger(__name__)


class CustomTitleBar(QWidget):
    """Custom title bar with minimize, maximize, and close buttons"""

    # Signals
    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, title="Gestión de Categorías", parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.title = title
        self.is_maximized = False
        self.drag_position = None

        self.init_ui()

    def init_ui(self):
        """Initialize the title bar UI"""
        self.setFixedHeight(40)
        self.setStyleSheet("""
            CustomTitleBar {
                background-color: #1e1e1e;
                border-bottom: 1px solid #3d3d3d;
            }
        """)

        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)
        layout.setSpacing(10)

        # Title label
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 12pt;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.title_label)

        # Spacer
        layout.addStretch()

        # Window control buttons
        button_style = """
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #4d4d4d;
            }
        """

        close_button_style = """
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e81123;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #c50b18;
            }
        """

        # Minimize button
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setFixedSize(40, 30)
        self.minimize_btn.setStyleSheet(button_style)
        self.minimize_btn.clicked.connect(self.minimize_clicked.emit)
        self.minimize_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout.addWidget(self.minimize_btn)

        # Maximize/Restore button
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setFixedSize(40, 30)
        self.maximize_btn.setStyleSheet(button_style)
        self.maximize_btn.clicked.connect(self._on_maximize_clicked)
        self.maximize_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout.addWidget(self.maximize_btn)

        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(40, 30)
        self.close_btn.setStyleSheet(close_button_style)
        self.close_btn.clicked.connect(self.close_clicked.emit)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout.addWidget(self.close_btn)

    def _on_maximize_clicked(self):
        """Handle maximize button click and update icon"""
        self.is_maximized = not self.is_maximized
        self.maximize_btn.setText("❐" if self.is_maximized else "□")
        self.maximize_clicked.emit()

    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.drag_position = None

    def mouseDoubleClickEvent(self, event):
        """Handle double click to maximize/restore"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_maximize_clicked()


class CategoryManagerWindow(QWidget):
    """
    Window for managing categories with CRUD operations.

    Features:
    - Search bar with real-time filtering
    - Checkbox to activate/deactivate categories
    - Custom title bar with window controls
    - Footer with action buttons
    """

    # Signals
    categories_changed = pyqtSignal()  # Emitted when categories are modified

    def __init__(self, controller=None, parent=None):
        """
        Initialize category manager window

        Args:
            controller: MainController instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.controller = controller
        self.db = controller.config_manager.db if controller else None

        # Data
        self.all_categories = []
        self.filtered_categories = []

        # Search debouncing
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)  # 300ms debounce
        self.search_timer.timeout.connect(self._perform_search)

        # Window state
        self.normal_geometry = None

        self.init_ui()
        self.load_categories()

    def init_ui(self):
        """Initialize the UI"""
        # Window properties
        self.setWindowTitle("Gestión de Categorías")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint
        )

        # Set default size and position
        self.resize(900, 600)
        self._center_on_screen()

        # Apply dark theme
        self.setStyleSheet("""
            CategoryManagerWindow {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        self.title_bar = CustomTitleBar("Gestión de Categorías", self)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        self.title_bar.maximize_clicked.connect(self._toggle_maximize)
        self.title_bar.close_clicked.connect(self.hide)  # Hide instead of close
        main_layout.addWidget(self.title_bar)

        # Content area
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Search bar
        self._create_search_bar(content_layout)

        # Category list area
        self._create_category_list_area(content_layout)

        # Footer with action buttons
        self._create_footer(content_layout)

        main_layout.addWidget(content_widget)

    def _create_search_bar(self, parent_layout):
        """Create the search bar"""
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)

        # Search icon label
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #888888;
            }
        """)
        search_layout.addWidget(search_icon)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar categorías...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px 15px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input, 1)

        # Clear button
        self.clear_btn = QPushButton("×")
        self.clear_btn.setFixedSize(35, 35)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                border-radius: 17px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                color: #cccccc;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_search)
        self.clear_btn.hide()  # Hidden by default
        self.clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        search_layout.addWidget(self.clear_btn)

        # Select All button
        self.select_all_btn = QPushButton("☑ Todos")
        self.select_all_btn.setFixedHeight(35)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 0 15px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #007acc;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
        """)
        self.select_all_btn.clicked.connect(self._select_all_categories)
        self.select_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.select_all_btn.setToolTip("Activar todas las categorías")
        search_layout.addWidget(self.select_all_btn)

        # Deselect All button
        self.deselect_all_btn = QPushButton("☐ Ninguno")
        self.deselect_all_btn.setFixedHeight(35)
        self.deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 0 15px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #007acc;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
        """)
        self.deselect_all_btn.clicked.connect(self._deselect_all_categories)
        self.deselect_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.deselect_all_btn.setToolTip("Desactivar todas las categorías")
        search_layout.addWidget(self.deselect_all_btn)

        parent_layout.addWidget(search_container)

    def _create_category_list_area(self, parent_layout):
        """Create the scrollable category list area"""
        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4d4d4d;
            }
        """)

        # Container for category list
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(10, 10, 10, 10)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state label
        self.empty_label = QLabel("No se encontraron categorías")
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12pt;
                padding: 50px;
            }
        """)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()
        self.list_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.list_container)
        parent_layout.addWidget(self.scroll_area, 1)

    def _create_footer(self, parent_layout):
        """Create the footer with action buttons"""
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 15, 0, 0)
        footer_layout.setSpacing(10)

        # Category count label
        self.count_label = QLabel("0 categorías (0 activas)")
        self.count_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 10pt;
            }
        """)
        footer_layout.addWidget(self.count_label)

        # Spacer
        footer_layout.addStretch()

        # Action buttons style
        button_style = """
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 10pt;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """

        primary_button_style = """
            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: 1px solid #005a9e;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 10pt;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #0088dd;
                border: 1px solid #006bb3;
            }
            QPushButton:pressed {
                background-color: #006bb3;
            }
        """

        # Nueva Categoría button (primary)
        self.new_category_btn = QPushButton("+ Nueva Categoría")
        self.new_category_btn.setStyleSheet(primary_button_style)
        self.new_category_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.new_category_btn.clicked.connect(self._on_create_category)
        footer_layout.addWidget(self.new_category_btn)

        parent_layout.addWidget(footer_widget)

    def _center_on_screen(self):
        """Center the window on screen"""
        from PyQt6.QtGui import QScreen
        screen = QScreen.availableGeometry(self.screen())
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _toggle_maximize(self):
        """Toggle between maximized and normal state"""
        if self.isMaximized():
            self.showNormal()
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
        else:
            self.normal_geometry = self.geometry()
            self.showMaximized()

    def _on_search_text_changed(self, text):
        """Handle search text changes with debouncing"""
        # Show/hide clear button
        if text:
            self.clear_btn.show()
        else:
            self.clear_btn.hide()

        # Restart debounce timer
        self.search_timer.stop()
        self.search_timer.start()

    def _clear_search(self):
        """Clear search input"""
        self.search_input.clear()

    def _select_all_categories(self):
        """Activate all categories"""
        try:
            logger.info("Selecting all categories")

            # Get all category IDs
            category_ids = [cat['id'] for cat in self.all_categories]

            # Update database for all categories
            for cat_id in category_ids:
                self.db.set_category_active(cat_id, True)

            # Reload categories to reflect changes
            self.load_categories()

            # Emit signal to update sidebar
            self.categories_changed.emit()

            logger.info(f"Activated {len(category_ids)} categories")

        except Exception as e:
            logger.error(f"Error selecting all categories: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudieron activar todas las categorías:\n{str(e)}"
            )

    def _deselect_all_categories(self):
        """Deactivate all categories"""
        try:
            logger.info("Deselecting all categories")

            # Confirm action
            reply = QMessageBox.question(
                self,
                "Confirmar",
                "¿Desactivar todas las categorías?\n\nEsto ocultará todas las categorías del sidebar.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

            # Get all category IDs
            category_ids = [cat['id'] for cat in self.all_categories]

            # Update database for all categories
            for cat_id in category_ids:
                self.db.set_category_active(cat_id, False)

            # Reload categories to reflect changes
            self.load_categories()

            # Emit signal to update sidebar
            self.categories_changed.emit()

            logger.info(f"Deactivated {len(category_ids)} categories")

        except Exception as e:
            logger.error(f"Error deselecting all categories: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudieron desactivar todas las categorías:\n{str(e)}"
            )

    def _perform_search(self):
        """Perform the search and update the list"""
        search_text = self.search_input.text().strip().lower()

        if not search_text:
            # Show all categories
            self.filtered_categories = self.all_categories
        else:
            # Filter categories by name
            self.filtered_categories = [
                cat for cat in self.all_categories
                if search_text in cat['name'].lower()
            ]

        self.update_category_list()

    def load_categories(self):
        """Load all categories from database"""
        if not self.db:
            logger.error("Database not available")
            return

        try:
            # Load all categories (including inactive)
            self.all_categories = self.db.get_categories(include_inactive=True)
            self.filtered_categories = self.all_categories
            self.update_category_list()
            self.update_count_label()

            logger.info(f"Loaded {len(self.all_categories)} categories")
        except Exception as e:
            logger.error(f"Error loading categories: {e}")

    def update_category_list(self):
        """Update the category list display"""
        # Clear existing items (except empty label)
        for i in reversed(range(self.list_layout.count())):
            widget = self.list_layout.itemAt(i).widget()
            if widget and widget != self.empty_label:
                widget.deleteLater()

        # Show empty state if no categories
        if not self.filtered_categories:
            self.empty_label.show()
            return

        self.empty_label.hide()

        # Add category items with CategoryListItem widget
        for category in self.filtered_categories:
            item_widget = CategoryListItem(category, db=self.db, parent=self)

            # Connect signals
            item_widget.active_toggled.connect(self._on_category_active_toggled)
            item_widget.edit_requested.connect(self._on_edit_category)
            item_widget.delete_requested.connect(self._on_delete_category)
            item_widget.duplicate_requested.connect(self._on_duplicate_category)
            item_widget.pin_toggled.connect(self._on_pin_category)

            self.list_layout.addWidget(item_widget)

        self.update_count_label()

    def update_count_label(self):
        """Update the category count label"""
        total = len(self.all_categories)
        active = sum(1 for cat in self.all_categories if cat.get('is_active', 1))
        self.count_label.setText(f"{total} categorías ({active} activas)")

    def _on_create_category(self):
        """Handle create category button click"""
        dialog = CategoryFormDialog(mode='create', db=self.db, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            try:
                # Create category in database
                category_id = self.db.add_category(
                    name=data['name'],
                    icon=data['icon'],
                    is_predefined=False
                )

                # Update color if provided
                if data.get('color'):
                    self.db.execute_update(
                        "UPDATE categories SET color = ? WHERE id = ?",
                        (data['color'], category_id)
                    )

                logger.info(f"Category created: {data['name']} (ID: {category_id})")

                # Reload categories
                self.load_categories()

                # Invalidate cache
                if self.controller:
                    try:
                        self.controller.invalidate_filter_cache()
                    except AttributeError:
                        pass

                # Show success message
                QMessageBox.information(
                    self,
                    "Categoría Creada",
                    f"La categoría '{data['name']}' ha sido creada exitosamente."
                )
            except Exception as e:
                logger.error(f"Error creating category: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo crear la categoría: {str(e)}"
                )

    def _on_category_active_toggled(self, category_id, is_active):
        """Handle category active state toggle"""
        logger.info(f"Category {category_id} active state toggled to: {is_active}")

        # Update count label
        self.load_categories()

        # Invalidate filter cache
        if self.controller:
            try:
                self.controller.invalidate_filter_cache()
            except AttributeError:
                logger.warning("Controller does not have invalidate_filter_cache method")

    def _on_edit_category(self, category_id):
        """Handle edit category request"""
        # Get category data
        category = next((cat for cat in self.all_categories if cat['id'] == category_id), None)
        if not category:
            QMessageBox.warning(self, "Error", "Categoría no encontrada.")
            return

        # Open edit dialog
        dialog = CategoryFormDialog(mode='edit', category=category, db=self.db, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            try:
                # Update category in database
                self.db.execute_update(
                    """UPDATE categories
                       SET name = ?, icon = ?, color = ?, updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (data['name'], data['icon'], data.get('color'), category_id)
                )

                logger.info(f"Category {category_id} updated: {data['name']}")

                # Reload categories
                self.load_categories()

                # Invalidate cache
                if self.controller:
                    try:
                        self.controller.invalidate_filter_cache()
                    except AttributeError:
                        pass

                # Show success message
                QMessageBox.information(
                    self,
                    "Categoría Actualizada",
                    f"La categoría '{data['name']}' ha sido actualizada exitosamente."
                )
            except Exception as e:
                logger.error(f"Error updating category: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo actualizar la categoría: {str(e)}"
                )

    def _on_delete_category(self, category_id):
        """Handle delete category request"""
        # Get category name
        category = next((cat for cat in self.all_categories if cat['id'] == category_id), None)
        if not category:
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Eliminar Categoría",
            f"¿Estás seguro de que deseas eliminar la categoría '{category['name']}'?\n\n"
            f"Esta acción eliminará la categoría y todos sus items asociados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete category
                self.db.delete_category(category_id)
                logger.info(f"Category {category_id} deleted successfully")

                # Reload categories
                self.load_categories()

                # Invalidate cache
                if self.controller:
                    try:
                        self.controller.invalidate_filter_cache()
                    except AttributeError:
                        pass

                # Show success message
                QMessageBox.information(
                    self,
                    "Categoría Eliminada",
                    f"La categoría '{category['name']}' ha sido eliminada exitosamente."
                )
            except Exception as e:
                logger.error(f"Error deleting category: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo eliminar la categoría: {str(e)}"
                )

    def _on_duplicate_category(self, category_id):
        """Handle duplicate category request"""
        # Get category data
        category = next((cat for cat in self.all_categories if cat['id'] == category_id), None)
        if not category:
            QMessageBox.warning(self, "Error", "Categoría no encontrada.")
            return

        # Open duplicate dialog (with "Copia de" prefix)
        dialog = CategoryFormDialog(mode='duplicate', category=category, db=self.db, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            try:
                # Create new category (duplicate)
                new_category_id = self.db.add_category(
                    name=data['name'],
                    icon=data['icon'],
                    is_predefined=False
                )

                # Update color if provided
                if data.get('color'):
                    self.db.execute_update(
                        "UPDATE categories SET color = ? WHERE id = ?",
                        (data['color'], new_category_id)
                    )

                logger.info(f"Category duplicated: {data['name']} (new ID: {new_category_id})")

                # Ask if user wants to duplicate items too
                reply = QMessageBox.question(
                    self,
                    "Duplicar Items",
                    f"Categoría '{data['name']}' creada.\n\n"
                    f"¿Deseas también duplicar los items de la categoría original?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # Get items from original category
                    original_items = self.db.get_items_by_category(category_id)

                    for item in original_items:
                        self.db.add_item(
                            category_id=new_category_id,
                            label=item['label'],
                            content=item['content'],
                            item_type=item.get('item_type', 'TEXT'),
                            is_sensitive=item.get('is_sensitive', 0),
                            description=item.get('description'),
                            tags=item.get('tags', [])
                        )

                    logger.info(f"Duplicated {len(original_items)} items to category {new_category_id}")

                # Reload categories
                self.load_categories()

                # Invalidate cache
                if self.controller:
                    try:
                        self.controller.invalidate_filter_cache()
                    except AttributeError:
                        pass

                # Show success message
                items_msg = f" con {len(original_items)} items" if reply == QMessageBox.StandardButton.Yes else ""
                QMessageBox.information(
                    self,
                    "Categoría Duplicada",
                    f"La categoría '{data['name']}' ha sido duplicada exitosamente{items_msg}."
                )
            except Exception as e:
                logger.error(f"Error duplicating category: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo duplicar la categoría: {str(e)}"
                )

    def _on_pin_category(self, category_id):
        """Handle pin/unpin category request"""
        # Get category
        category = next((cat for cat in self.all_categories if cat['id'] == category_id), None)
        if not category:
            return

        current_pinned = category.get('is_pinned', 0)
        new_pinned = not current_pinned

        try:
            # Update pinned status
            # Note: This assumes DBManager has an update method that accepts is_pinned
            # If not, we'll need to add it or use update_category
            if hasattr(self.db, 'update_category'):
                self.db.execute_update(
                    "UPDATE categories SET is_pinned = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_pinned, category_id)
                )
                logger.info(f"Category {category_id} pinned state changed to: {new_pinned}")

                # Reload categories
                self.load_categories()

                # Show feedback
                action = "anclada" if new_pinned else "desanclada"
                QMessageBox.information(
                    self,
                    "Categoría Actualizada",
                    f"La categoría '{category['name']}' ha sido {action} exitosamente."
                )
            else:
                logger.warning("Database does not support pinned status update")
        except Exception as e:
            logger.error(f"Error updating pinned status: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo actualizar el estado de anclaje: {str(e)}"
            )

    def closeEvent(self, event):
        """Handle window close event"""
        self.categories_changed.emit()
        super().closeEvent(event)
