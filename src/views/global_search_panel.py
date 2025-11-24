"""
Global Search Panel Window - Independent window for searching all items across all categories
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton, QSizePolicy, QComboBox
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QEvent, QTimer
from PyQt6.QtGui import QFont, QCursor
import sys
import logging
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.item import Item, ItemType
from views.widgets.item_widget import ItemButton
from views.widgets.search_bar import SearchBar
from views.advanced_filters_window import AdvancedFiltersWindow
from core.search_engine import SearchEngine
from core.advanced_filter_engine import AdvancedFilterEngine
from core.pinned_panels_manager import PinnedPanelsManager
from styles.panel_styles import PanelStyles
from utils.panel_resizer import PanelResizer

# Get logger
logger = logging.getLogger(__name__)


class GlobalSearchPanel(QWidget):
    """Floating window for global search across all items"""

    # Signal emitted when an item is clicked
    item_clicked = pyqtSignal(object)

    # Signal emitted when window is closed
    window_closed = pyqtSignal()

    # Signal emitted when pin state changes
    pin_state_changed = pyqtSignal(bool)  # True = pinned, False = unpinned

    # Signal emitted when URL should be opened in embedded browser
    url_open_requested = pyqtSignal(str)

    def __init__(self, db_manager=None, config_manager=None, list_controller=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.list_controller = list_controller
        self.search_engine = SearchEngine()
        self.filter_engine = AdvancedFilterEngine()  # Motor de filtrado avanzado
        self.all_items = []  # Store all items before filtering
        self.current_filters = {}  # Filtros activos actuales
        self.current_state_filter = "normal"  # Filtro de estado actual: normal, archived, inactive, all

        # Timer para debouncing de búsqueda
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        self.pending_search_query = ""

        # Timer para auto-guardado (similar a FloatingPanel)
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._save_panel_state_to_db)
        self.update_delay_ms = 1000  # 1 second delay after changes

        # Pinned panel properties
        self.is_pinned = False
        self.panel_id = None
        self.panel_name = "Búsqueda Global"
        self.panel_color = "#ff6b00"  # Color naranja por defecto

        # Minimized state (similar a FloatingPanel)
        self.is_minimized = False
        self.normal_height = None  # Altura normal antes de minimizar
        self.normal_width = None  # Ancho normal antes de minimizar
        self.normal_position = None  # Posición normal antes de minimizar

        # Pinned panels manager
        self.panels_manager = None
        if self.db_manager:
            self.panels_manager = PinnedPanelsManager(self.db_manager)

        # Get panel width from config (or use new default)
        if config_manager:
            self.panel_width = config_manager.get_setting('panel_width', PanelStyles.PANEL_WIDTH_DEFAULT)
        else:
            self.panel_width = PanelStyles.PANEL_WIDTH_DEFAULT

        # Panel resizer (will be initialized in init_ui)
        self.panel_resizer = None

        # Flag para animación de entrada (primera vez)
        self._first_show = True

        self.init_ui()

    def init_ui(self):
        """Initialize the floating panel UI with new optimized design"""
        # Window properties
        self.setWindowTitle("Widget Sidebar - Búsqueda Global")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )

        # Set window size with new optimized dimensions
        self.setMinimumWidth(PanelStyles.PANEL_WIDTH_MIN)
        self.setMaximumWidth(PanelStyles.PANEL_WIDTH_MAX)
        self.setMinimumHeight(PanelStyles.PANEL_HEIGHT_MIN)
        self.setMaximumHeight(PanelStyles.PANEL_HEIGHT_MAX)
        self.resize(self.panel_width, PanelStyles.PANEL_HEIGHT_DEFAULT)

        # Enable mouse tracking for resizer
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # Set window opacity
        self.setWindowOpacity(0.98)

        # No cerrar la aplicación al cerrar esta ventana
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)

        # Apply new panel styles
        self.setStyleSheet(PanelStyles.get_panel_style())

        # Initialize panel resizer
        self.panel_resizer = PanelResizer(
            widget=self,
            min_width=PanelStyles.PANEL_WIDTH_MIN,
            max_width=PanelStyles.PANEL_WIDTH_MAX,
            min_height=PanelStyles.PANEL_HEIGHT_MIN,
            max_height=PanelStyles.PANEL_HEIGHT_MAX,
            handle_size=PanelStyles.RESIZE_HANDLE_SIZE
        )
        # Connect resize signal
        self.panel_resizer.resized.connect(self.on_panel_resized)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with title and close button
        self.header_widget = QWidget()
        self.header_widget.setStyleSheet(PanelStyles.get_header_style())
        self.header_widget.setFixedHeight(PanelStyles.HEADER_HEIGHT)
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(
            PanelStyles.HEADER_PADDING_H,
            PanelStyles.HEADER_PADDING_V,
            PanelStyles.HEADER_PADDING_H,
            PanelStyles.HEADER_PADDING_V
        )
        self.header_layout.setSpacing(6)

        # Title
        self.header_label = QLabel("🔍 Búsqueda Global")
        self.header_label.setStyleSheet(PanelStyles.get_header_title_style())
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.header_layout.addWidget(self.header_label, 1)  # Stretch factor 1

        # Filter badge (shows number of active filters)
        self.filter_badge = QLabel()
        self.filter_badge.setVisible(False)
        self.filter_badge.setStyleSheet("""
            QLabel {
                background-color: #ff6b00;
                color: white;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 9pt;
                font-weight: bold;
            }
        """)
        self.filter_badge.setToolTip("Filtros activos")
        self.header_layout.addWidget(self.filter_badge)

        # Pin button
        self.pin_button = QPushButton("📌")
        self.pin_button.setFixedSize(PanelStyles.CLOSE_BUTTON_SIZE, PanelStyles.CLOSE_BUTTON_SIZE)
        self.pin_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pin_button.setStyleSheet(PanelStyles.get_close_button_style())
        self.pin_button.setToolTip("Anclar panel")
        self.pin_button.clicked.connect(self.toggle_pin)
        self.header_layout.addWidget(self.pin_button)

        # Minimize button (solo visible cuando está anclado)
        self.minimize_button = QPushButton("−")
        self.minimize_button.setFixedSize(PanelStyles.CLOSE_BUTTON_SIZE, PanelStyles.CLOSE_BUTTON_SIZE)
        self.minimize_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.minimize_button.setStyleSheet(PanelStyles.get_close_button_style())
        self.minimize_button.setToolTip("Minimizar panel")
        self.minimize_button.clicked.connect(self.toggle_minimize)
        self.minimize_button.setVisible(False)  # Solo visible cuando está anclado
        self.header_layout.addWidget(self.minimize_button)

        # Config button (solo visible cuando está anclado)
        self.config_button = QPushButton("⚙")
        self.config_button.setFixedSize(PanelStyles.CLOSE_BUTTON_SIZE, PanelStyles.CLOSE_BUTTON_SIZE)
        self.config_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.config_button.setStyleSheet(PanelStyles.get_close_button_style())
        self.config_button.setToolTip("Configurar panel")
        self.config_button.clicked.connect(self.show_panel_configuration)
        self.config_button.setVisible(False)  # Solo visible cuando está anclado
        self.header_layout.addWidget(self.config_button)

        # Close button
        close_button = QPushButton("✕")
        close_button.setFixedSize(PanelStyles.CLOSE_BUTTON_SIZE, PanelStyles.CLOSE_BUTTON_SIZE)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.setStyleSheet(PanelStyles.get_close_button_style())
        close_button.clicked.connect(self.hide)
        self.header_layout.addWidget(close_button)

        main_layout.addWidget(self.header_widget)

        # Botón para abrir ventana de filtros avanzados
        self.filters_button_widget = QWidget()
        self.filters_button_widget.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        filters_button_layout = QHBoxLayout(self.filters_button_widget)
        filters_button_layout.setContentsMargins(8, 5, 8, 5)
        filters_button_layout.setSpacing(0)

        self.open_filters_button = QPushButton("🔍 Filtros Avanzados")
        self.open_filters_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_filters_button.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #df83eb,
                    stop:1 #e4475b
                );
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        self.open_filters_button.clicked.connect(self.toggle_filters_window)
        filters_button_layout.addWidget(self.open_filters_button)

        # Botón "Copiar Todos los Visibles"
        self.copy_all_button = QPushButton("📋 Copiar Todos")
        self.copy_all_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_all_button.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ff88,
                    stop:1 #00ccff
                );
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        self.copy_all_button.setToolTip("Copiar el contenido de todos los items visibles actualmente")
        self.copy_all_button.clicked.connect(self.on_copy_all_visible)
        filters_button_layout.addWidget(self.copy_all_button)

        # ComboBox para filtro de estado
        self.state_filter_combo = QComboBox()
        self.state_filter_combo.addItem("📄 Normal", "normal")
        self.state_filter_combo.addItem("📦 Archivados", "archived")
        self.state_filter_combo.addItem("⏸️ Inactivos", "inactive")
        self.state_filter_combo.addItem("📋 Todos", "all")
        self.state_filter_combo.setCurrentIndex(0)  # Default: Normal
        self.state_filter_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.state_filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #252525;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
                min-width: 120px;
            }
            QComboBox:hover {
                border: 1px solid #f093fb;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                selection-background-color: #f093fb;
            }
        """)
        self.state_filter_combo.setToolTip("Filtrar items por estado")
        self.state_filter_combo.currentIndexChanged.connect(self.on_state_filter_changed)
        filters_button_layout.addWidget(self.state_filter_combo)

        # Botón "Crear Lista"
        self.create_list_button = QPushButton("➕ Crear Lista")
        self.create_list_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.create_list_button.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff6ec7,
                    stop:1 #7873f5
                );
            }
            QPushButton:pressed {
                background-color: #252525;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666666;
            }
        """)
        self.create_list_button.setToolTip("Crear lista avanzada desde los items visibles")
        self.create_list_button.clicked.connect(self.on_create_list_clicked)
        filters_button_layout.addWidget(self.create_list_button)

        main_layout.addWidget(self.filters_button_widget)

        # Crear ventana flotante de filtros (oculta inicialmente)
        self.filters_window = AdvancedFiltersWindow(self)
        self.filters_window.filters_changed.connect(self.on_filters_changed)
        self.filters_window.filters_cleared.connect(self.on_filters_cleared)
        self.filters_window.hide()

        # Search bar
        self.search_bar = SearchBar()
        self.search_bar.search_changed.connect(self.on_search_changed)
        main_layout.addWidget(self.search_bar)

        # Scroll area for items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            {PanelStyles.get_scroll_area_style()}
            {PanelStyles.get_scrollbar_style()}
        """)

        # Container for items
        self.items_container = QWidget()
        self.items_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        self.items_container.setStyleSheet(PanelStyles.get_body_style())

        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(
            PanelStyles.BODY_PADDING,
            PanelStyles.BODY_PADDING,
            PanelStyles.BODY_PADDING,
            PanelStyles.BODY_PADDING
        )
        self.items_layout.setSpacing(PanelStyles.ITEM_SPACING)
        self.items_layout.addStretch()

        self.scroll_area.setWidget(self.items_container)
        main_layout.addWidget(self.scroll_area)

    def load_all_items(self):
        """Load and display ALL items from ALL categories"""
        if not self.db_manager:
            logger.error("No database manager available")
            return

        logger.info("Loading all items for global search")

        # Get all items from database
        items_data = self.db_manager.get_all_items(include_inactive=False)

        # Convert dict items to Item objects
        self.all_items = []
        for item_dict in items_data:
            try:
                # Convert type string to ItemType enum (handle both uppercase and lowercase)
                type_str = item_dict['type'].lower() if item_dict['type'] else 'text'
                item_type = ItemType(type_str)

                item = Item(
                    item_id=str(item_dict['id']),
                    label=item_dict['label'],
                    content=item_dict['content'],
                    item_type=item_type,
                    icon=item_dict.get('icon'),
                    is_sensitive=bool(item_dict.get('is_sensitive', False)),
                    is_favorite=bool(item_dict.get('is_favorite', False)),
                    tags=item_dict.get('tags', []),
                    description=item_dict.get('description')
                )

                # Store category info for display
                item.category_name = item_dict.get('category_name', '')
                item.category_icon = item_dict.get('category_icon', '')
                item.category_color = item_dict.get('category_color', '')

                # Parse date fields from database (SQLite returns strings)
                from datetime import datetime
                if item_dict.get('created_at'):
                    try:
                        # SQLite datetime format: 'YYYY-MM-DD HH:MM:SS' or ISO format
                        created_at_str = item_dict['created_at']
                        if 'T' in created_at_str:
                            # ISO format
                            item.created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        else:
                            # SQLite format
                            item.created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                        logger.debug(f"Parsed created_at for '{item.label}': {item.created_at}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse created_at '{item_dict.get('created_at')}': {e}")
                        item.created_at = datetime.now()
                else:
                    logger.debug(f"Item '{item.label}' has no created_at in database")

                if item_dict.get('last_used'):
                    try:
                        last_used_str = item_dict['last_used']
                        if 'T' in last_used_str:
                            # ISO format
                            item.last_used = datetime.fromisoformat(last_used_str.replace('Z', '+00:00'))
                        else:
                            # SQLite format
                            item.last_used = datetime.strptime(last_used_str, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Could not parse last_used '{item_dict.get('last_used')}': {e}")
                        item.last_used = datetime.now()

                # Parse use_count
                item.use_count = item_dict.get('use_count', 0)

                self.all_items.append(item)
            except Exception as e:
                logger.error(f"Error converting item {item_dict.get('id')}: {e}")
                continue

        logger.info(f"Loaded {len(self.all_items)} items from database")

        # Update available tags in filters window
        self.filters_window.update_available_tags(self.all_items)
        logger.debug(f"Updated available tags from {len(self.all_items)} items")

        # Clear search bar
        self.search_bar.clear_search()

        # Display only first 100 items initially (for performance)
        # When user searches/filters, all matching items will be shown
        initial_display_limit = 100
        items_to_display = self.all_items[:initial_display_limit]
        self.display_items(items_to_display, total_count=len(self.all_items))

        # Show the window
        self.show()
        self.raise_()
        self.activateWindow()

    def display_items(self, items, total_count=None):
        """Display a list of items

        Args:
            items: List of items to display
            total_count: Total number of items available (if showing limited results)
        """
        logger.info(f"Displaying {len(items)} items")

        # Actualizar título con contador
        if total_count and total_count > len(items):
            # Showing limited results
            self.header_label.setText(f"🌐 Búsqueda Global ({len(items)} de {total_count} items)")
        else:
            # Showing all results
            self.header_label.setText(f"🌐 Búsqueda Global ({len(items)} items)")

        # Clear existing items
        self.clear_items()

        # Add items
        for idx, item in enumerate(items):
            logger.debug(f"Creating button {idx+1}/{len(items)}: {item.label}")
            item_button = ItemButton(item, show_category=True)  # show_category=True for global search
            item_button.item_clicked.connect(self.on_item_clicked)
            item_button.url_open_requested.connect(self.on_url_open_requested)
            self.items_layout.insertWidget(self.items_layout.count() - 1, item_button)

        # Add info message if showing limited results
        if total_count and total_count > len(items):
            info_widget = QWidget()
            info_widget.setStyleSheet("""
                QWidget {
                    background-color: #2d2d2d;
                    border: 1px solid #4d4d4d;
                    border-radius: 4px;
                    padding: 10px;
                    margin: 5px;
                }
            """)
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(10, 10, 10, 10)

            info_label = QLabel(
                f"ℹ️ Mostrando los primeros {len(items)} items de {total_count} totales.\n"
                f"💡 Usa la búsqueda o filtros para encontrar items específicos."
            )
            info_label.setWordWrap(True)
            info_label.setStyleSheet("""
                QLabel {
                    color: #aaaaaa;
                    font-size: 10pt;
                    background-color: transparent;
                    border: none;
                }
            """)
            info_layout.addWidget(info_label)

            self.items_layout.insertWidget(self.items_layout.count() - 1, info_widget)

        logger.info(f"Successfully added {len(items)} item buttons to layout")

    def clear_items(self):
        """Clear all item buttons"""
        while self.items_layout.count() > 1:  # Keep the stretch at the end
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def on_item_clicked(self, item: Item):
        """Handle item click"""
        # Emit signal to parent
        self.item_clicked.emit(item)

    def on_url_open_requested(self, url: str):
        """Handle URL open request from ItemButton"""
        logger.info(f"URL open requested: {url}")
        # Forward signal to parent (MainWindow)
        self.url_open_requested.emit(url)

    def on_item_state_changed(self, item_id: str):
        """Handle item state change (favorite/archived) from ItemDetailsDialog"""
        logger.info(f"Item {item_id} state changed, refreshing search results")
        # Reload all items and re-apply current search
        self.load_all_items()
        if self.search_bar.text():
            self.on_search_changed(self.search_bar.text())

    def on_search_changed(self, query: str):
        """Handle search query change with debouncing"""
        self.pending_search_query = query
        self.search_timer.start(300)  # 300ms debounce

        # Trigger auto-save after 1 second
        if self.is_pinned:
            self.update_timer.start(self.update_delay_ms)

    def _perform_search(self):
        """Perform the actual search after debounce"""
        query = self.pending_search_query
        logger.debug(f"_perform_search called with query='{query}'")
        logger.debug(f"Total items before filter: {len(self.all_items)}")
        logger.debug(f"Current filters: {self.current_filters}")

        # Aplicar filtros avanzados primero
        filtered_items = self.filter_engine.apply_filters(self.all_items, self.current_filters)
        logger.debug(f"Items after advanced filters: {len(filtered_items)}")

        # Aplicar filtro de estado
        filtered_items = self.filter_items_by_state(filtered_items)
        logger.debug(f"Items after state filter: {len(filtered_items)}")

        # Luego aplicar búsqueda si hay query
        if query and query.strip():
            # Search in labels, content, tags, description, and category name
            search_results = []
            query_lower = query.lower()

            for item in filtered_items:
                # Search in label
                if query_lower in item.label.lower():
                    search_results.append(item)
                    continue

                # Search in content (if not sensitive)
                if not item.is_sensitive and query_lower in item.content.lower():
                    search_results.append(item)
                    continue

                # Search in tags
                if any(query_lower in tag.lower() for tag in item.tags):
                    search_results.append(item)
                    continue

                # Search in description
                if item.description and query_lower in item.description.lower():
                    search_results.append(item)
                    continue

                # Search in category name
                if hasattr(item, 'category_name') and item.category_name:
                    if query_lower in item.category_name.lower():
                        search_results.append(item)
                        continue

            filtered_items = search_results

        # Apply initial display limit if no search/filters are active
        # (for performance with large datasets)
        if not query.strip() and not self.current_filters and self.current_state_filter == 'normal':
            # No search, no advanced filters, no state filter -> limit to 100 items
            initial_display_limit = 100
            if len(filtered_items) > initial_display_limit:
                self.display_items(filtered_items[:initial_display_limit], total_count=len(filtered_items))
            else:
                self.display_items(filtered_items)
        else:
            # Search or filters active -> show all results
            self.display_items(filtered_items)

        # Update filter badge when search changes
        self.update_filter_badge()

    def on_filters_changed(self, filters: dict):
        """Handle cuando cambian los filtros avanzados"""
        # Update filter badge
        self.update_filter_badge()

        logger.info(f"Filters changed: {filters}")
        self.current_filters = filters

        # Re-aplicar búsqueda y filtros
        current_query = self.search_bar.search_input.text()
        self.on_search_changed(current_query)

        # Trigger auto-save after 1 second (don't call on_search_changed again to avoid double save)
        if self.is_pinned:
            self.update_timer.start(self.update_delay_ms)

    def on_filters_cleared(self):
        """Handle cuando se limpian todos los filtros"""
        # Update filter badge
        self.update_filter_badge()

        logger.info("All filters cleared")
        self.current_filters = {}

        # Re-aplicar búsqueda sin filtros
        current_query = self.search_bar.search_input.text()
        self.on_search_changed(current_query)

        # Trigger auto-save after 1 second
        if self.is_pinned:
            self.update_timer.start(self.update_delay_ms)

    def update_filter_badge(self):
        """Actualizar badge de filtros activos en el header"""
        filter_count = 0

        # Contar filtros avanzados activos
        if self.current_filters:
            filter_count += len(self.current_filters)

        # Contar búsqueda activa
        if hasattr(self, 'search_bar') and self.search_bar:
            if hasattr(self.search_bar, 'search_input'):
                search_text = self.search_bar.search_input.text().strip()
                if search_text:
                    filter_count += 1

        # Contar filtro de estado (si no es 'normal')
        if self.current_state_filter != "normal":
            filter_count += 1

        # Mostrar/ocultar badge según la cantidad de filtros
        if filter_count > 0:
            self.filter_badge.setText(f"🔍 {filter_count}")
            self.filter_badge.setVisible(True)
            tooltip_parts = []
            if self.current_filters:
                tooltip_parts.append(f"{len(self.current_filters)} filtro(s) avanzado(s)")
            if hasattr(self, 'search_bar') and self.search_bar and self.search_bar.search_input.text().strip():
                tooltip_parts.append(f"Búsqueda activa")
            if self.current_state_filter != "normal":
                tooltip_parts.append(f"Estado: {self.current_state_filter}")
            self.filter_badge.setToolTip(" | ".join(tooltip_parts))
        else:
            self.filter_badge.setVisible(False)

    def update_pin_button_style(self):
        """Actualizar estilo del botón de pin según estado"""
        if self.is_pinned:
            # Cuando está anclado: pin inclinado con fondo verde (igual que FloatingPanel)
            icon = "📍"
            tooltip = "Panel anclado - Click para desanclar"
            bg_color = "rgba(0, 200, 0, 0.3)"
        else:
            # Cuando NO está anclado: pin recto con fondo gris (igual que FloatingPanel)
            icon = "📌"
            tooltip = "Anclar este panel - Guardar configuración actual"
            bg_color = "rgba(255, 255, 255, 0.1)"

        self.pin_button.setText(icon)
        self.pin_button.setToolTip(tooltip)
        self.pin_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 16px;
                font-size: 14pt;
            }}
            QPushButton:hover {{
                background-color: {'rgba(0, 200, 0, 0.5)' if self.is_pinned else 'rgba(255, 255, 255, 0.2)'};
            }}
            QPushButton:pressed {{
                background-color: {'rgba(0, 200, 0, 0.4)' if self.is_pinned else 'rgba(255, 255, 255, 0.3)'};
            }}
        """)

        # Mostrar/ocultar botón de minimizar según estado de anclado
        if hasattr(self, 'minimize_button'):
            self.minimize_button.setVisible(self.is_pinned)

        # Mostrar/ocultar botón de configuración según estado de anclado
        if hasattr(self, 'config_button'):
            self.config_button.setVisible(self.is_pinned)

    def toggle_pin(self):
        """Alternar estado de anclado del panel (igual que FloatingPanel)"""
        if self.is_pinned:
            # Desanclar panel
            self.unpin_panel()
        else:
            # Anclar panel directamente (sin diálogo, igual que FloatingPanel)
            self.pin_panel()

    def show_pin_configuration_dialog(self):
        """Mostrar diálogo para configurar panel antes de anclar"""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QColorDialog

        dialog = QDialog(self)
        dialog.setWindowTitle("Configurar Panel de Búsqueda")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        dialog.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)

        layout = QVBoxLayout(dialog)

        # Nombre del panel
        name_label = QLabel("Nombre del panel:")
        self.name_input = QLineEdit()
        self.name_input.setText(self.panel_name)
        self.name_input.setPlaceholderText("Ej: Búsqueda de APIs, Comandos Git, etc.")
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)

        # Color del panel
        color_label = QLabel("Color del panel:")
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setStyleSheet(f"background-color: {self.panel_color}; border: 1px solid white; border-radius: 4px;")

        color_button = QPushButton("Elegir color")
        color_button.clicked.connect(lambda: self.choose_panel_color(dialog))

        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(color_button)
        color_layout.addStretch()

        layout.addWidget(color_label)
        layout.addLayout(color_layout)

        # Información de filtros actuales
        info_label = QLabel("\nSe guardarán:")
        info_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(info_label)

        filters_info = self.get_current_filters_info()
        info_text = QLabel(filters_info)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #aaaaaa; margin-left: 10px;")
        layout.addWidget(info_text)

        # Botones
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Estilos del diálogo
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.panel_name = self.name_input.text() or "Búsqueda Global"
            self.pin_panel()

    def choose_panel_color(self, dialog):
        """Abrir selector de color"""
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QColorDialog

        color = QColorDialog.getColor(QColor(self.panel_color), dialog, "Elegir color del panel")
        if color.isValid():
            self.panel_color = color.name()
            self.color_preview.setStyleSheet(f"background-color: {self.panel_color}; border: 1px solid white; border-radius: 4px;")

    def get_current_filters_info(self):
        """Obtener información legible de los filtros actuales"""
        info_parts = []

        # Búsqueda de texto
        if hasattr(self, 'search_bar') and self.search_bar:
            search_text = self.search_bar.search_input.text().strip()
            if search_text:
                info_parts.append(f"• Búsqueda: '{search_text}'")

        # Filtros avanzados
        if hasattr(self, 'current_filters') and self.current_filters:
            info_parts.append(f"• {len(self.current_filters)} filtro(s) avanzado(s)")

        # Filtro de estado
        if hasattr(self, 'current_state_filter'):
            state_names = {
                "normal": "Items normales",
                "archived": "Items archivados",
                "inactive": "Items inactivos",
                "all": "Todos los items"
            }
            state_name = state_names.get(self.current_state_filter, self.current_state_filter)
            if self.current_state_filter != "normal":
                info_parts.append(f"• Estado: {state_name}")

        if not info_parts:
            return "• Todos los items (sin filtros)"

        return "\n".join(info_parts)

    def pin_panel(self):
        """Guardar panel anclado en base de datos"""
        if not self.panels_manager:
            logger.error("PinnedPanelsManager no disponible")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error",
                "No se puede anclar el panel: gestor de paneles no disponible"
            )
            return

        try:
            logger.info(f"Guardando panel anclado: {self.panel_name}")

            # Guardar panel en base de datos
            panel_id = self.panels_manager.save_global_search_panel(
                panel_widget=self,
                custom_name=self.panel_name,
                custom_color=self.panel_color
            )

            # Actualizar estado
            self.is_pinned = True
            self.panel_id = panel_id
            self.update_pin_button_style()

            logger.info(f"Panel anclado exitosamente (ID: {panel_id})")

            # Emitir señal de cambio de estado (mejor práctica PyQt6)
            self.pin_state_changed.emit(True)

            # También notificar directamente a MainWindow si está disponible (compatibilidad)
            main_window = self.parent() if self.parent() else None
            # Buscar MainWindow en la jerarquía
            widget = self
            while widget and not hasattr(widget, 'on_global_search_panel_pinned'):
                widget = widget.parent() if hasattr(widget, 'parent') and widget.parent() else None

            if widget and hasattr(widget, 'on_global_search_panel_pinned'):
                widget.on_global_search_panel_pinned(self)

            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Panel Anclado",
                f"Panel '{self.panel_name}' anclado exitosamente.\n\n"
                f"ID: {panel_id}\n"
                f"Configuración guardada:\n"
                f"- Búsqueda: '{self.pending_search_query or '(vacío)'}'\n"
                f"- Filtro de estado: {self.current_state_filter}\n"
                f"- Filtros avanzados: {'Sí' if self.current_filters else 'No'}"
            )

        except Exception as e:
            logger.error(f"Error al anclar panel: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo anclar el panel:\n{e}"
            )

    def unpin_panel(self):
        """Desanclar panel (archivar en base de datos)"""
        if not self.panels_manager:
            logger.error("PinnedPanelsManager no disponible")
            return

        if not self.panel_id:
            logger.warning("No hay panel_id para desanclar")
            self.is_pinned = False
            self.update_pin_button_style()
            return

        try:
            logger.info(f"Desanclando panel ID: {self.panel_id}")

            # Archivar panel en base de datos
            self.panels_manager.archive_panel(self.panel_id)

            # Actualizar estado
            self.is_pinned = False
            old_panel_id = self.panel_id
            self.panel_id = None
            self.update_pin_button_style()

            logger.info(f"Panel desanclado exitosamente (ID: {old_panel_id})")

            # Emitir señal de cambio de estado (mejor práctica PyQt6)
            self.pin_state_changed.emit(False)

            # También notificar directamente a MainWindow si está disponible (compatibilidad)
            widget = self
            while widget and not hasattr(widget, 'on_global_search_panel_unpinned'):
                widget = widget.parent() if hasattr(widget, 'parent') and widget.parent() else None

            if widget and hasattr(widget, 'on_global_search_panel_unpinned'):
                widget.on_global_search_panel_unpinned(self)

            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Panel Desanclado",
                f"Panel '{self.panel_name}' desanclado.\n\n"
                f"La configuración ha sido archivada."
            )

        except Exception as e:
            logger.error(f"Error al desanclar panel: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo desanclar el panel:\n{e}"
            )

    def toggle_minimize(self):
        """Toggle panel minimize state (only for pinned panels) - IGUAL QUE FloatingPanel"""
        if not self.is_pinned:
            logger.warning("Cannot minimize unpinned panel")
            return  # Only allow minimize for pinned panels

        self.is_minimized = not self.is_minimized

        if self.is_minimized:
            # Save current size and position
            self.normal_height = self.height()
            self.normal_width = self.width()
            self.normal_position = self.pos()
            logger.info(f"Minimizing panel - saving size: {self.normal_width}x{self.normal_height}, position: {self.normal_position}")

            # Hide content widgets
            self.filters_button_widget.setVisible(False)
            self.search_bar.setVisible(False)
            self.scroll_area.setVisible(False)

            # Reduce header margins for compact look
            self.header_layout.setContentsMargins(8, 3, 5, 3)

            # CRITICAL: Remove size constraints temporarily to allow small size
            self.setMinimumWidth(0)
            self.setMinimumHeight(0)

            # Resize to compact size (height: 32px, width: ~180px)
            minimized_height = 32
            minimized_width = 180
            self.resize(minimized_width, minimized_height)

            # Move to bottom of screen (al ras de la barra de tareas)
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                # Position al ras de la barra de tareas (5px margin)
                new_x = self.x()  # Keep same X position
                new_y = screen_geometry.bottom() - minimized_height - 5  # 5px margin - al ras de taskbar
                self.move(new_x, new_y)
                logger.info(f"Moved minimized panel to bottom: ({new_x}, {new_y})")

            # Update button
            self.minimize_button.setText("□")
            self.minimize_button.setToolTip("Maximizar panel")
            logger.info(f"Panel '{self.header_label.text()}' MINIMIZADO")
        else:
            # Restore content widgets
            self.filters_button_widget.setVisible(True)
            self.search_bar.setVisible(True)
            self.scroll_area.setVisible(True)

            # Restore header margins
            self.header_layout.setContentsMargins(15, 10, 10, 10)

            # CRITICAL: Restore size constraints
            self.setMinimumWidth(300)
            self.setMinimumHeight(400)

            # Restore original size
            if self.normal_height and self.normal_width:
                self.resize(self.normal_width, self.normal_height)
                logger.info(f"Restored panel size to: {self.normal_width}x{self.normal_height}")
            else:
                # Fallback: use default size
                from PyQt6.QtWidgets import QApplication
                screen = QApplication.primaryScreen()
                if screen:
                    screen_height = screen.availableGeometry().height()
                    window_height = int(screen_height * 0.8)
                    self.resize(self.panel_width, window_height)
                    logger.info(f"Restored panel size to default: {self.panel_width}x{window_height}")

            # Restore original position
            if self.normal_position:
                self.move(self.normal_position)
                logger.info(f"Restored panel position to: {self.normal_position}")

            # Update button
            self.minimize_button.setText("−")
            self.minimize_button.setToolTip("Minimizar panel")
            logger.info(f"Panel '{self.header_label.text()}' MAXIMIZADO")

        # Guardar estado en BD
        if self.panel_id and self.panels_manager:
            try:
                self.panels_manager.update_panel_minimize_state(self.panel_id, self.is_minimized)
            except Exception as e:
                logger.error(f"Failed to save minimize state: {e}")

    def show_panel_configuration(self):
        """Mostrar diálogo de configuración para panel ya anclado"""
        if not self.is_pinned:
            logger.warning("Cannot configure non-pinned panel")
            return

        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QColorDialog, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Configurar Panel")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Nombre del panel
        name_label = QLabel("Nombre del panel:")
        name_input = QLineEdit()
        name_input.setText(self.panel_name)
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        # Color del panel
        color_label = QLabel("Color del panel:")
        color_layout = QHBoxLayout()

        current_color = self.panel_color
        color_preview = QLabel()
        color_preview.setFixedSize(30, 30)
        color_preview.setStyleSheet(f"background-color: {current_color}; border: 1px solid white; border-radius: 4px;")

        def choose_color():
            nonlocal current_color
            from PyQt6.QtGui import QColor
            color = QColorDialog.getColor(QColor(current_color), dialog, "Elegir color del panel")
            if color.isValid():
                current_color = color.name()
                color_preview.setStyleSheet(f"background-color: {current_color}; border: 1px solid white; border-radius: 4px;")

        color_button = QPushButton("Elegir color")
        color_button.clicked.connect(choose_color)

        color_layout.addWidget(color_preview)
        color_layout.addWidget(color_button)
        color_layout.addStretch()

        layout.addWidget(color_label)
        layout.addLayout(color_layout)

        # Información actual
        info_label = QLabel("\nConfiguración actual:")
        info_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(info_label)

        filters_info = self.get_current_filters_info()
        info_text = QLabel(filters_info)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #aaaaaa; margin-left: 10px;")
        layout.addWidget(info_text)

        # Botones
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Actualizar propiedades
            old_name = self.panel_name
            old_color = self.panel_color

            self.panel_name = name_input.text() or "Búsqueda Global"
            self.panel_color = current_color

            # Actualizar en BD
            try:
                if self.panels_manager:
                    self.panels_manager.update_panel_customization(
                        self.panel_id,
                        custom_name=self.panel_name,
                        custom_color=self.panel_color
                    )

                # Actualizar UI
                self.setWindowTitle(f"🔍 {self.panel_name}")
                self.update_pin_button_style()

                logger.info(f"Updated panel {self.panel_id} configuration: {old_name} -> {self.panel_name}")

                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Configuración Actualizada",
                    f"La configuración del panel ha sido actualizada exitosamente.\n\n"
                    f"Nombre: {self.panel_name}\n"
                    f"Color: {self.panel_color}"
                )

            except Exception as e:
                logger.error(f"Failed to update panel configuration: {e}", exc_info=True)
                # Revertir cambios
                self.panel_name = old_name
                self.panel_color = old_color
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Error",
                    f"No se pudo actualizar la configuración: {e}"
                )

    def contextMenuEvent(self, event):
        """Show context menu when right-clicking on the panel

        Solo se muestra si el panel está anclado (is_pinned == True)
        """
        if not self.is_pinned:
            # No mostrar menú contextual si no está anclado
            return

        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction

        # Create context menu
        menu = QMenu(self)

        # Estilo del menú
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px 8px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
            QMenu::separator {
                height: 1px;
                background: #3d3d3d;
                margin: 5px 0px;
            }
        """)

        # Actions
        refresh_action = QAction("🔄 Actualizar resultados", self)
        refresh_action.triggered.connect(self.refresh_search_results)
        menu.addAction(refresh_action)

        save_filters_action = QAction("💾 Guardar filtros actuales", self)
        save_filters_action.triggered.connect(self.save_current_filters)
        menu.addAction(save_filters_action)

        clear_filters_action = QAction("🧹 Limpiar todos los filtros", self)
        clear_filters_action.triggered.connect(self._clear_all_filters)
        menu.addAction(clear_filters_action)

        menu.addSeparator()

        copy_all_action = QAction("📋 Copiar todos los items visibles", self)
        copy_all_action.triggered.connect(self.on_copy_all_visible)
        menu.addAction(copy_all_action)

        create_list_action = QAction("📝 Crear lista con resultados", self)
        create_list_action.triggered.connect(self.on_create_list_clicked)
        menu.addAction(create_list_action)

        menu.addSeparator()

        open_manager_action = QAction("📌 Abrir gestor de paneles", self)
        open_manager_action.triggered.connect(self._open_panels_manager)
        menu.addAction(open_manager_action)

        configure_action = QAction("⚙️ Configurar panel", self)
        configure_action.triggered.connect(self.show_panel_configuration)
        menu.addAction(configure_action)

        info_action = QAction("ℹ️ Información del panel", self)
        info_action.triggered.connect(self._show_panel_info)
        menu.addAction(info_action)

        # Show menu at cursor position
        menu.exec(event.globalPos())

    def on_copy_all_visible(self):
        """Copiar al portapapeles el contenido de todos los items visibles"""
        # Obtener todos los widgets de items actualmente en el layout
        visible_items = []
        for i in range(self.items_layout.count() - 1):  # -1 para excluir el stretch
            widget = self.items_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'item'):
                visible_items.append(widget.item)

        if not visible_items:
            logger.warning("No visible items to copy")
            return

        # Construir texto para copiar
        content_parts = []
        for item in visible_items:
            # Formato: [Categoría] Label: Contenido
            category_info = f"[{item.category_icon} {item.category_name}]" if hasattr(item, 'category_name') else ""
            item_text = f"{category_info} {item.label}: {item.content}"
            content_parts.append(item_text)

        # Copiar al portapapeles
        full_content = "\n".join(content_parts)

        try:
            import pyperclip
            pyperclip.copy(full_content)
            logger.info(f"Copied {len(visible_items)} items to clipboard")

            # Feedback visual (opcional)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Copiado",
                f"Se copiaron {len(visible_items)} item(s) al portapapeles"
            )
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error",
                f"Error al copiar al portapapeles: {e}"
            )

    def on_state_filter_changed(self, index):
        """Handle cuando cambia el filtro de estado"""
        state_filter = self.state_filter_combo.itemData(index)
        self.current_state_filter = state_filter
        logger.info(f"State filter changed to: {state_filter}")

        # Re-aplicar búsqueda con nuevo filtro de estado
        current_query = self.search_bar.search_input.text()
        self.on_search_changed(current_query)

        # Update filter badge
        self.update_filter_badge()

        # Trigger auto-save after 1 second
        if self.is_pinned:
            self.update_timer.start(self.update_delay_ms)

    def filter_items_by_state(self, items):
        """Filtrar items por estado (activo/archivado/inactivo)

        Args:
            items: Lista de items a filtrar

        Returns:
            Lista filtrada de items
        """
        if self.current_state_filter == "all":
            # Mostrar todos los items
            return items

        filtered = []
        for item in items:
            # Verificar estado del item en la base de datos
            if self.db_manager:
                item_data = self.db_manager.get_item(int(item.id))
                if item_data:
                    is_active = item_data.get('is_active', True)
                    is_archived = item_data.get('is_archived', False)

                    # Aplicar filtro según selección
                    if self.current_state_filter == "normal":
                        # Solo items activos y no archivados
                        if is_active and not is_archived:
                            filtered.append(item)
                    elif self.current_state_filter == "archived":
                        # Solo items archivados
                        if is_archived:
                            filtered.append(item)
                    elif self.current_state_filter == "inactive":
                        # Solo items inactivos (no activos y no archivados)
                        if not is_active and not is_archived:
                            filtered.append(item)

        return filtered

    def on_create_list_clicked(self):
        """Abrir diálogo para crear lista desde items visibles"""
        if not self.list_controller:
            logger.warning("Cannot create list: no list controller available")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error",
                "Funcionalidad de listas no disponible"
            )
            return

        # Obtener items visibles
        visible_items = []
        for i in range(self.items_layout.count() - 1):
            widget = self.items_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'item'):
                visible_items.append(widget.item)

        if not visible_items:
            logger.warning("No visible items to create list from")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Sin Items",
                "No hay items visibles para crear una lista"
            )
            return

        # Abrir diálogo de selección de categoría y creación de lista
        from views.dialogs.create_list_from_search_dialog import CreateListFromSearchDialog

        creator_dialog = CreateListFromSearchDialog(
            items=visible_items,
            db_manager=self.db_manager,
            config_manager=self.config_manager,
            list_controller=self.list_controller,
            parent=self
        )

        creator_dialog.list_created.connect(self.on_list_created_from_dialog)
        creator_dialog.exec()

    def on_list_created_from_dialog(self, list_name: str, category_id: int, item_ids: list):
        """Handle cuando se crea una lista desde el diálogo"""
        logger.info(f"List '{list_name}' created in category {category_id} with {len(item_ids)} items")

        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Lista Creada",
            f"Lista '{list_name}' creada exitosamente con {len(item_ids)} items"
        )

    def position_near_sidebar(self, sidebar_window):
        """Position the floating panel near the sidebar window"""
        # Get sidebar window geometry
        sidebar_x = sidebar_window.x()
        sidebar_y = sidebar_window.y()
        sidebar_width = sidebar_window.width()

        # Position to the left of the sidebar
        panel_x = sidebar_x - self.width() - 10  # 10px gap
        panel_y = sidebar_y

        self.move(panel_x, panel_y)
        logger.debug(f"Positioned global search panel at ({panel_x}, {panel_y})")

    def toggle_filters_window(self):
        """Abrir/cerrar la ventana de filtros avanzados"""
        if self.filters_window.isVisible():
            self.filters_window.hide()
        else:
            # Posicionar cerca del panel flotante
            self.filters_window.position_near_panel(self)
            self.filters_window.show()
            self.filters_window.raise_()
            self.filters_window.activateWindow()

    def refresh_search_results(self):
        """Refresh search results by re-running the current search"""
        logger.info("Refreshing search results...")

        # Get current search query
        current_query = self.search_bar.search_input.text()

        # Clear current results
        self.clear_items()

        # Re-run search
        if current_query:
            self.on_search_changed(current_query)
        else:
            # If no query, show all items
            self.on_search_changed("")

        logger.info("Search results refreshed")

        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Actualizado",
            "Los resultados de búsqueda han sido actualizados"
        )

    def save_current_filters(self):
        """Save current filters as a named filter preset"""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox

        # Check if there are any filters applied
        has_filters = False
        if self.search_bar.search_input.text():
            has_filters = True
        if self.current_filters:
            has_filters = True
        if self.current_state_filter != "normal":
            has_filters = True

        if not has_filters:
            QMessageBox.information(
                self,
                "Sin Filtros",
                "No hay filtros aplicados para guardar"
            )
            return

        # Ask for preset name
        preset_name, ok = QInputDialog.getText(
            self,
            "Guardar Filtros",
            "Nombre para este preset de filtros:",
            text="Mi Búsqueda"
        )

        if ok and preset_name:
            try:
                # Create filter preset
                filter_preset = {
                    'name': preset_name,
                    'search_query': self.search_bar.search_input.text(),
                    'advanced_filters': self.current_filters,
                    'state_filter': self.current_state_filter
                }

                # Save to config
                if self.config_manager:
                    # Get existing presets
                    presets = self.config_manager.get_setting('search_filter_presets', [])
                    if not isinstance(presets, list):
                        presets = []

                    # Add new preset
                    presets.append(filter_preset)

                    # Save back to config
                    self.config_manager.set_setting('search_filter_presets', presets)

                    logger.info(f"Saved filter preset: {preset_name}")
                    QMessageBox.information(
                        self,
                        "Guardado",
                        f"Preset de filtros '{preset_name}' guardado exitosamente"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "No se pudo guardar el preset: ConfigManager no disponible"
                    )

            except Exception as e:
                logger.error(f"Failed to save filter preset: {e}", exc_info=True)
                QMessageBox.warning(
                    self,
                    "Error",
                    f"No se pudo guardar el preset: {e}"
                )

    def _clear_all_filters(self):
        """Clear all filters and show all items"""
        logger.info("Clearing all filters...")

        # Clear search query
        self.search_bar.search_input.clear()

        # Clear advanced filters
        self.current_filters = None

        # Reset state filter to normal
        self.current_state_filter = "normal"
        for i in range(self.state_filter_combo.count()):
            if self.state_filter_combo.itemData(i) == "normal":
                self.state_filter_combo.setCurrentIndex(i)
                break

        # Update filter badge
        self.update_filter_badge()

        # Clear results
        self.clear_items()

        logger.info("All filters cleared")

        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Filtros Limpiados",
            "Todos los filtros han sido eliminados"
        )

    def _open_panels_manager(self):
        """Open the pinned panels manager window"""
        logger.info("Opening panels manager window...")

        # Find MainWindow
        widget = self
        main_window = None
        while widget:
            if hasattr(widget, 'show_pinned_panels_manager'):
                main_window = widget
                break
            widget = widget.parent() if hasattr(widget, 'parent') and widget.parent() else None

        if main_window:
            main_window.show_pinned_panels_manager()
        else:
            logger.warning("Could not find MainWindow to open panels manager")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error",
                "No se pudo abrir el gestor de paneles"
            )

    def _show_panel_info(self):
        """Show information dialog about this panel"""
        from PyQt6.QtWidgets import QMessageBox

        # Count visible items
        visible_count = 0
        for i in range(self.items_layout.count() - 1):
            widget = self.items_layout.itemAt(i).widget()
            if widget:
                visible_count += 1

        # Build info message
        info_lines = [
            f"<b>Nombre:</b> {self.panel_name}",
            f"<b>ID del Panel:</b> {self.panel_id if self.panel_id else 'No anclado'}",
            f"<b>Color:</b> {self.panel_color}",
            "",
            f"<b>Items Visibles:</b> {visible_count}",
            "",
            f"<b>Búsqueda Actual:</b> {self.search_bar.search_input.text() or '(ninguna)'}",
            f"<b>Filtro de Estado:</b> {self.current_state_filter}",
            f"<b>Filtros Avanzados:</b> {'Sí' if self.current_filters else 'No'}",
            "",
            f"<b>Posición:</b> ({self.x()}, {self.y()})",
            f"<b>Tamaño:</b> {self.width()}x{self.height()}",
            f"<b>Minimizado:</b> {'Sí' if self.is_minimized else 'No'}",
        ]

        info_text = "<br>".join(info_lines)

        QMessageBox.information(
            self,
            f"ℹ️ Información del Panel",
            info_text
        )

    def _save_panel_state_to_db(self):
        """AUTO-UPDATE: Save current panel state (position/size/filters/search) to database"""
        logger.info(f"[AUTO-SAVE] _save_panel_state_to_db() called for global search panel {self.panel_id}")

        # Only save if this is a pinned panel with a valid panel_id
        if not self.is_pinned or not self.panel_id or not self.panels_manager:
            logger.warning(f"[AUTO-SAVE] Cannot save - is_pinned={self.is_pinned}, panel_id={self.panel_id}, panels_manager={self.panels_manager is not None}")
            return

        try:
            # Log current state
            logger.info(f"[AUTO-SAVE] Current global search panel state:")
            logger.info(f"  - current_filters: {self.current_filters}")
            logger.info(f"  - current_state_filter: {self.current_state_filter}")
            logger.info(f"  - search_text: '{self.search_bar.search_input.text()}'")

            # Serialize filter configuration
            filter_config = {
                'advanced_filters': self.current_filters,
                'state_filter': self.current_state_filter,
                'search_query': self.search_bar.search_input.text()
            }

            # Update panel state in database
            self.panels_manager.db.execute_update(
                """UPDATE pinned_panels
                   SET x_position = ?, y_position = ?, width = ?, height = ?,
                       is_minimized = ?, filter_config = ?
                   WHERE id = ?""",
                (self.x(), self.y(), self.width(), self.height(),
                 1 if self.is_minimized else 0,
                 json.dumps(filter_config),
                 self.panel_id)
            )

            logger.info(f"[AUTO-SAVE] Global search panel {self.panel_id} state saved successfully")
            logger.info(f"  - Position: {self.pos()}, Size: {self.size()}")
            logger.info(f"  - Filters saved: {filter_config}")

        except Exception as e:
            logger.error(f"[AUTO-SAVE] Error auto-saving global search panel state: {e}", exc_info=True)

    def moveEvent(self, event):
        """Handle window move event - trigger auto-save"""
        super().moveEvent(event)

        # Trigger auto-save after 1 second (debounced)
        if self.is_pinned and not self.is_minimized:
            self.update_timer.start(self.update_delay_ms)

    def resizeEvent(self, event):
        """Handle window resize event - trigger auto-save"""
        super().resizeEvent(event)

        # Trigger auto-save after 1 second (debounced)
        if self.is_pinned and not self.is_minimized:
            self.update_timer.start(self.update_delay_ms)

    def on_panel_resized(self, width: int, height: int):
        """Handle panel resize completion from PanelResizer"""
        logger.info(f"Global Search Panel resized to: {width}x{height}")

        # Save new dimensions to config
        if self.config_manager:
            self.config_manager.set_setting('panel_width', width)
            self.config_manager.set_setting('panel_height', height)

            # Save to panel_settings table if db_manager is available
            if self.db_manager:
                self.db_manager.save_panel_settings(
                    panel_name='global_search_panel',
                    width=width,
                    height=height,
                    x=self.x(),
                    y=self.y()
                )

        # Trigger auto-save for pinned panels
        if self.is_pinned and self.panel_id and self.panels_manager:
            self.update_timer.start(self.update_delay_ms)

    def smooth_scroll_to(self, value: int, duration: int = 300):
        """
        Anima el scroll vertical hacia un valor específico

        Args:
            value: Valor objetivo del scroll (0 = arriba, max = abajo)
            duration: Duración de la animación en milisegundos (default: 300ms)
        """
        scroll_bar = self.scroll_area.verticalScrollBar()
        animation = PanelStyles.create_smooth_scroll_animation(scroll_bar, value, duration)
        animation.start()
        # Guardar referencia para que no se destruya
        self._scroll_animation = animation

    def smooth_scroll_to_top(self, duration: int = 300):
        """Anima el scroll hacia arriba"""
        self.smooth_scroll_to(0, duration)

    def smooth_scroll_to_bottom(self, duration: int = 300):
        """Anima el scroll hacia abajo"""
        scroll_bar = self.scroll_area.verticalScrollBar()
        self.smooth_scroll_to(scroll_bar.maximum(), duration)

    def showEvent(self, event):
        """Handler al mostrar ventana - aplicar animación de entrada"""
        super().showEvent(event)

        if self._first_show:
            self._first_show = False
            # Aplicar animación de fade-in con las nuevas animaciones de PanelStyles
            animation = PanelStyles.create_fade_in_animation(self, duration=200)
            animation.start()
            # Guardar referencia para que no se destruya
            self._show_animation = animation

    def closeEvent(self, event):
        """Handle window close event"""
        # Ignorar el evento inicialmente para aplicar animación
        event.ignore()

        # Cerrar también la ventana de filtros si está abierta
        if self.filters_window.isVisible():
            self.filters_window.close()

        # Crear y ejecutar animación de fade-out
        animation = PanelStyles.create_fade_out_animation(self, duration=150)

        # Cuando termine la animación, cerrar la ventana realmente
        def on_animation_finished():
            self.window_closed.emit()
            super(GlobalSearchPanel, self).close()  # Cerrar sin disparar closeEvent nuevamente

        animation.finished.connect(on_animation_finished)
        animation.start()

        # Guardar referencia para que no se destruya
        self._close_animation = animation
