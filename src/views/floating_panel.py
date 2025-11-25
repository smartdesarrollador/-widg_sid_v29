"""
Floating Panel Window - Independent window for displaying category items
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton, QComboBox, QMenu, QSizePolicy, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QEvent, QTimer
from PyQt6.QtGui import QFont, QCursor
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.category import Category
from models.item import Item
from views.widgets.item_widget import ItemButton
from views.widgets.list_widget import ListWidget
from views.widgets.table_group_widget import TableGroupWidget
from views.widgets.search_bar import SearchBar
from views.advanced_filters_window import AdvancedFiltersWindow
from views.dialogs.list_creator_dialog import ListCreatorDialog
from views.dialogs.list_editor_dialog import ListEditorDialog
from views.dialogs.table_view_dialog import TableViewDialog
from core.search_engine import SearchEngine
from core.advanced_filter_engine import AdvancedFilterEngine
from styles.futuristic_theme import get_theme
from styles.animations import AnimationSystem, AnimationDurations
from styles.effects import ParticleEffect, ScanLineEffect
from styles.panel_styles import PanelStyles
from utils.panel_resizer import PanelResizer

# Get logger
logger = logging.getLogger(__name__)


class FloatingPanel(QWidget):
    """Floating window for displaying category items"""

    # Signal emitted when an item is clicked
    item_clicked = pyqtSignal(object)

    # Signal emitted when window is closed
    window_closed = pyqtSignal()

    # Signal emitted when pin state changes
    pin_state_changed = pyqtSignal(bool)  # True = pinned, False = unpinned

    # Signal emitted when customization is requested
    customization_requested = pyqtSignal()

    # Signal emitted when URL should be opened in embedded browser
    url_open_requested = pyqtSignal(str)

    def __init__(self, config_manager=None, list_controller=None, panel_id=None, custom_name=None, custom_color=None, parent=None, main_window=None):
        super().__init__(parent)
        self.current_category = None
        self.config_manager = config_manager
        self.list_controller = list_controller  # Controlador de listas
        self.main_window = main_window  # Direct reference to MainWindow (for auto-save)
        self.search_engine = SearchEngine()
        self.filter_engine = AdvancedFilterEngine()  # Motor de filtrado avanzado
        self.all_items = []  # Store all items before filtering
        self.all_lists = []  # Store all lists before filtering
        self.visible_items = []  # Store currently visible items (after filtering)
        self.current_filters = {}  # Filtros activos actuales
        self.current_state_filter = "normal"  # Filtro de estado actual: normal, archived, inactive, all
        self.is_pinned = False  # Estado de anclaje del panel
        self.is_minimized = False  # Estado de minimizado (solo para paneles anclados)
        self.normal_height = None  # Altura normal antes de minimizar
        self.normal_width = None  # Ancho normal antes de minimizar
        self.normal_position = None  # Posición normal antes de minimizar

        # Panel persistence attributes
        self.panel_id = panel_id  # ID del panel en la base de datos (None si no está guardado)
        self.custom_name = custom_name  # Nombre personalizado del panel
        self.custom_color = custom_color  # Color personalizado del header (hex format)

        # Futuristic theme and effects
        self.theme = get_theme()
        self.animation_system = AnimationSystem()
        self._first_show = True  # Flag para animación de entrada

        # Get panel width from config (or use new default)
        if config_manager:
            self.panel_width = config_manager.get_setting('panel_width', PanelStyles.PANEL_WIDTH_DEFAULT)
        else:
            self.panel_width = PanelStyles.PANEL_WIDTH_DEFAULT

        # Panel resizer (will be initialized in init_ui)
        self.panel_resizer = None

        # AUTO-UPDATE: Timer for debounced panel state updates
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._save_panel_state_to_db)
        self.update_delay_ms = 1000  # 1 second delay after move/resize

        self.init_ui()

    def init_ui(self):
        """Initialize the floating panel UI"""
        # Window properties
        self.setWindowTitle("Widget Sidebar - Items")
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

        # Header with category name and close button
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

        # Category title
        self.header_label = QLabel("📁 Select a category")
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
        self.pin_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_button.setStyleSheet(PanelStyles.get_close_button_style())
        self.pin_button.setToolTip("Anclar panel (permite abrir múltiples paneles)")
        self.pin_button.clicked.connect(self.toggle_pin)
        self.header_layout.addWidget(self.pin_button)

        # Minimize button (only visible when pinned)
        self.minimize_button = QPushButton("−")
        self.minimize_button.setFixedSize(PanelStyles.CLOSE_BUTTON_SIZE, PanelStyles.CLOSE_BUTTON_SIZE)
        self.minimize_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minimize_button.setStyleSheet(PanelStyles.get_close_button_style())
        self.minimize_button.setToolTip("Minimizar panel")
        self.minimize_button.clicked.connect(self.toggle_minimize)
        self.minimize_button.setVisible(False)  # Hidden by default (only show when pinned)
        self.header_layout.addWidget(self.minimize_button)

        # Config button (only visible when pinned)
        self.config_button = QPushButton("⚙")
        self.config_button.setFixedSize(PanelStyles.CLOSE_BUTTON_SIZE, PanelStyles.CLOSE_BUTTON_SIZE)
        self.config_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_button.setStyleSheet(PanelStyles.get_close_button_style())
        self.config_button.setToolTip("Configurar panel (nombre y color)")
        self.config_button.clicked.connect(self.on_config_clicked)
        self.config_button.setVisible(False)  # Hidden by default (only show when pinned)
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
        self.filters_button_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme.get_color('background_mid')};
                border-bottom: 1px solid {self.theme.get_color('surface')};
            }}
        """)
        filters_button_layout = QHBoxLayout(self.filters_button_widget)
        filters_button_layout.setContentsMargins(8, 5, 8, 5)
        filters_button_layout.setSpacing(0)

        self.open_filters_button = QPushButton("🔍 Filtros Avanzados")
        self.open_filters_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_filters_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('background_deep')};
                color: {self.theme.get_color('text_primary')};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get_color('secondary')};
            }}
            QPushButton:pressed {{
                background-color: {self.theme.get_color('accent')};
            }}
        """)
        self.open_filters_button.clicked.connect(self.toggle_filters_window)
        filters_button_layout.addWidget(self.open_filters_button)

        # Agregar espaciador
        filters_button_layout.addSpacing(10)

        # ComboBox para filtrar por estado
        self.state_filter_combo = QComboBox()
        self.state_filter_combo.addItem("📄 Normal", "normal")
        self.state_filter_combo.addItem("📦 Archivados", "archived")
        self.state_filter_combo.addItem("⏸️ Inactivos", "inactive")
        self.state_filter_combo.addItem("📋 Todos", "all")
        self.state_filter_combo.setCurrentIndex(0)  # Default: Normal
        self.state_filter_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.state_filter_combo.setStyleSheet(self.theme.get_combobox_style())
        self.state_filter_combo.currentIndexChanged.connect(self.on_state_filter_changed)
        filters_button_layout.addWidget(self.state_filter_combo)

        # Agregar stretch para empujar los botones a la derecha
        filters_button_layout.addStretch()

        # Botón Copiar Todo
        self.copy_all_button = QPushButton("📋")
        self.copy_all_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_all_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('background_deep')};
                color: {self.theme.get_color('text_primary')};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get_color('secondary')};
                color: {self.theme.get_color('text_primary')};
            }}
            QPushButton:pressed {{
                background-color: {self.theme.get_color('accent')};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.get_color('surface')};
                color: {self.theme.get_color('text_secondary')};
            }}
        """)
        self.copy_all_button.setToolTip("Copiar el contenido de todos los items visibles actualmente")
        self.copy_all_button.clicked.connect(self.on_copy_all_clicked)
        self.copy_all_button.setEnabled(False)  # Disabled hasta que se cargue una categoría
        filters_button_layout.addWidget(self.copy_all_button)

        # Botón Nueva Lista
        self.new_list_button = QPushButton("📝 Nueva Lista")
        self.new_list_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.new_list_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.get_color('success')};
                color: {self.theme.get_color('background_deep')};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get_color('secondary')};
                color: {self.theme.get_color('text_primary')};
            }}
            QPushButton:pressed {{
                background-color: {self.theme.get_color('accent')};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.get_color('surface')};
                color: {self.theme.get_color('text_secondary')};
            }}
        """)
        self.new_list_button.setToolTip("Crear una nueva lista de pasos secuenciales")
        self.new_list_button.clicked.connect(self.on_new_list_clicked)
        self.new_list_button.setEnabled(False)  # Disabled hasta que se cargue una categoría
        filters_button_layout.addWidget(self.new_list_button)

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

        # Display options row with checkboxes
        self.display_options_widget = QWidget()
        self.display_options_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme.get_color('background_mid')};
                border-bottom: 1px solid {self.theme.get_color('surface')};
            }}
        """)
        display_options_layout = QHBoxLayout(self.display_options_widget)
        display_options_layout.setContentsMargins(15, 5, 15, 5)
        display_options_layout.setSpacing(15)

        # Label for the section
        display_label = QLabel("Mostrar:")
        display_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme.get_color('text_secondary')};
                font-size: 9pt;
                font-weight: bold;
            }}
        """)
        display_options_layout.addWidget(display_label)

        # Checkbox: Mostrar Labels (checked by default)
        self.show_labels_checkbox = QCheckBox("Labels")
        self.show_labels_checkbox.setChecked(True)  # Default: ON
        self.show_labels_checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.show_labels_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {self.theme.get_color('text_primary')};
                font-size: 9pt;
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {self.theme.get_color('primary')};
                border-radius: 3px;
                background-color: {self.theme.get_color('background_deep')};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.theme.get_color('primary')};
                border-color: {self.theme.get_color('primary')};
            }}
            QCheckBox::indicator:hover {{
                border-color: {self.theme.get_color('accent')};
            }}
        """)
        self.show_labels_checkbox.stateChanged.connect(self.on_display_options_changed)
        display_options_layout.addWidget(self.show_labels_checkbox)

        # Checkbox: Mostrar Tags
        self.show_tags_checkbox = QCheckBox("Tags")
        self.show_tags_checkbox.setChecked(False)  # Default: OFF
        self.show_tags_checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.show_tags_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {self.theme.get_color('text_primary')};
                font-size: 9pt;
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {self.theme.get_color('primary')};
                border-radius: 3px;
                background-color: {self.theme.get_color('background_deep')};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.theme.get_color('primary')};
                border-color: {self.theme.get_color('primary')};
            }}
            QCheckBox::indicator:hover {{
                border-color: {self.theme.get_color('accent')};
            }}
        """)
        self.show_tags_checkbox.stateChanged.connect(self.on_display_options_changed)
        display_options_layout.addWidget(self.show_tags_checkbox)

        # Checkbox: Mostrar Contenido
        self.show_content_checkbox = QCheckBox("Contenido")
        self.show_content_checkbox.setChecked(False)  # Default: OFF
        self.show_content_checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.show_content_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {self.theme.get_color('text_primary')};
                font-size: 9pt;
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {self.theme.get_color('primary')};
                border-radius: 3px;
                background-color: {self.theme.get_color('background_deep')};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.theme.get_color('primary')};
                border-color: {self.theme.get_color('primary')};
            }}
            QCheckBox::indicator:hover {{
                border-color: {self.theme.get_color('accent')};
            }}
        """)
        self.show_content_checkbox.stateChanged.connect(self.on_display_options_changed)
        display_options_layout.addWidget(self.show_content_checkbox)

        # Checkbox: Mostrar Descripción
        self.show_description_checkbox = QCheckBox("Descripción")
        self.show_description_checkbox.setChecked(False)  # Default: OFF
        self.show_description_checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.show_description_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {self.theme.get_color('text_primary')};
                font-size: 9pt;
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {self.theme.get_color('primary')};
                border-radius: 3px;
                background-color: {self.theme.get_color('background_deep')};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.theme.get_color('primary')};
                border-color: {self.theme.get_color('primary')};
            }}
            QCheckBox::indicator:hover {{
                border-color: {self.theme.get_color('accent')};
            }}
        """)
        self.show_description_checkbox.stateChanged.connect(self.on_display_options_changed)
        display_options_layout.addWidget(self.show_description_checkbox)

        # Add stretch to push checkboxes to the left
        display_options_layout.addStretch()

        main_layout.addWidget(self.display_options_widget)

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
        # Configurar política de tamaño para permitir expansión horizontal
        self.items_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,  # Horizontal: expandir completamente (permite scroll)
            QSizePolicy.Policy.Preferred  # Vertical: tamaño preferido
        )
        # Aplicar estilo del body (fondo y padding)
        self.items_container.setStyleSheet(PanelStyles.get_body_style())

        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(PanelStyles.BODY_PADDING, PanelStyles.BODY_PADDING, PanelStyles.BODY_PADDING, PanelStyles.BODY_PADDING)
        self.items_layout.setSpacing(PanelStyles.ITEM_SPACING)
        self.items_layout.addStretch()

        self.scroll_area.setWidget(self.items_container)
        main_layout.addWidget(self.scroll_area)

        # Aplicar efectos visuales futuristas
        # Partículas flotantes (muy sutiles)
        self.particle_effect = ParticleEffect(self, particle_count=20)
        self.particle_effect.setGeometry(self.rect())
        self.particle_effect.lower()

        # Líneas de escaneo (muy sutiles)
        self.scanline_effect = ScanLineEffect(self, line_spacing=6, speed=1.0)
        self.scanline_effect.setGeometry(self.rect())
        self.scanline_effect.lower()

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

    def load_category(self, category: Category):
        """Load and display items and lists from a category"""
        logger.info(f"Loading category: {category.name} with {len(category.items)} items")

        self.current_category = category

        # Separar items normales de items de listas
        self.all_items = [item for item in category.items if not item.is_list_item()]

        # Obtener listas si tenemos ListController
        self.all_lists = []
        if self.list_controller and hasattr(category, 'id'):
            try:
                self.all_lists = self.list_controller.get_lists(category.id)
                logger.info(f"Loaded {len(self.all_lists)} lists from category {category.name}")
            except Exception as e:
                logger.error(f"Error loading lists: {e}", exc_info=True)

        # Update header
        self.header_label.setText(category.name)
        logger.debug(f"Header updated to: {category.name}")

        # Update available tags in filters window (Fase 4)
        self.filters_window.update_available_tags(self.all_items)
        logger.debug(f"Updated available tags from {len(self.all_items)} items")

        # Clear search bar
        self.search_bar.clear_search()

        # Clear existing items
        self.clear_items()
        logger.debug("Previous items and lists cleared")

        # Display items and lists
        self.display_items_and_lists(self.all_items, self.all_lists)

        # Enable "Nueva Lista" button if we have a list controller
        if self.list_controller and hasattr(category, 'id'):
            self.new_list_button.setEnabled(True)
        else:
            self.new_list_button.setEnabled(False)

        # Show the window
        self.show()
        self.raise_()
        self.activateWindow()

    def display_items(self, items):
        """Display a list of items (mantiene compatibilidad hacia atrás)"""
        logger.info(f"Displaying {len(items)} items")

        # Clear existing items
        self.clear_items()

        # Add items
        for idx, item in enumerate(items):
            logger.debug(f"Creating button {idx+1}/{len(items)}: {item.label}")
            item_button = ItemButton(item)
            item_button.item_clicked.connect(self.on_item_clicked)
            item_button.url_open_requested.connect(self.on_url_open_requested)
            item_button.table_view_requested.connect(self.on_table_view_requested)
            item_button.web_static_render_requested.connect(self.on_web_static_render_requested)
            self.items_layout.insertWidget(self.items_layout.count() - 1, item_button)

        logger.info(f"Successfully added {len(items)} item buttons to layout")

    def display_items_and_lists(self, items, lists):
        """Display items and lists in separate sections

        Limits display to maximum 100 items and 100 lists for performance

        Args:
            items: List of Item objects (solo items normales, no items de listas)
            lists: List of list metadata dicts from ListController.get_lists()
        """
        logger.info(f"Displaying {len(items)} items and {len(lists)} lists")

        # Store visible items for "Copy All" functionality
        self.visible_items = items

        # Enable/disable "Copiar Todo" button based on visible items
        self.copy_all_button.setEnabled(len(items) > 0)

        # Clear existing content
        self.clear_items()

        # Límite de visualización
        MAX_DISPLAY_ITEMS = 100
        MAX_DISPLAY_LISTS = 100

        # === SECCIÓN DE ITEMS ===
        if items:
            total_items = len(items)
            items_to_display = items[:MAX_DISPLAY_ITEMS]  # Limitar a 100

            # Section header con conteo
            if total_items > MAX_DISPLAY_ITEMS:
                items_header_text = f"━━━ Items ({MAX_DISPLAY_ITEMS} de {total_items}) ━━━"
            else:
                items_header_text = f"━━━ Items ({total_items}) ━━━"

            items_header = QLabel(items_header_text)
            items_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            items_header.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 10pt;
                    font-weight: bold;
                    padding: 8px;
                    background-color: transparent;
                }
            """)
            self.items_layout.insertWidget(self.items_layout.count() - 1, items_header)

            # Add items (solo los primeros 100)
            for idx, item in enumerate(items_to_display):
                logger.debug(f"Creating item button {idx+1}/{len(items_to_display)}: {item.label}")

                # Get display options from checkboxes
                show_labels = self.show_labels_checkbox.isChecked()
                show_tags = self.show_tags_checkbox.isChecked()
                show_content = self.show_content_checkbox.isChecked()
                show_description = self.show_description_checkbox.isChecked()

                # Create ItemButton with display options
                item_button = ItemButton(
                    item,
                    show_category=False,
                    show_labels=show_labels,
                    show_tags=show_tags,
                    show_content=show_content,
                    show_description=show_description
                )
                item_button.item_clicked.connect(self.on_item_clicked)
                item_button.url_open_requested.connect(self.on_url_open_requested)
                item_button.table_view_requested.connect(self.on_table_view_requested)
                item_button.web_static_render_requested.connect(self.on_web_static_render_requested)
                self.items_layout.insertWidget(self.items_layout.count() - 1, item_button)

        # === SECCIÓN DE LISTAS ===
        if lists:
            total_lists = len(lists)
            lists_to_display = lists[:MAX_DISPLAY_LISTS]  # Limitar a 100

            # Spacer entre secciones
            if items:
                spacer_label = QLabel("")
                spacer_label.setFixedHeight(10)
                spacer_label.setStyleSheet("background-color: transparent;")
                self.items_layout.insertWidget(self.items_layout.count() - 1, spacer_label)

            # Section header con conteo
            if total_lists > MAX_DISPLAY_LISTS:
                lists_header_text = f"━━━ Listas ({MAX_DISPLAY_LISTS} de {total_lists}) ━━━"
            else:
                lists_header_text = f"━━━ Listas ({total_lists}) ━━━"

            lists_header = QLabel(lists_header_text)
            lists_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lists_header.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 10pt;
                    font-weight: bold;
                    padding: 8px;
                    background-color: transparent;
                }
            """)
            self.items_layout.insertWidget(self.items_layout.count() - 1, lists_header)

            # Add lists (solo las primeras 100)
            for idx, list_data in enumerate(lists_to_display):
                logger.debug(f"Creating list widget {idx+1}/{len(lists_to_display)}: {list_data.get('list_group')}")

                # Obtener items de la lista
                list_items = []
                if self.list_controller and hasattr(self.current_category, 'id'):
                    list_items = self.list_controller.get_list_items(
                        self.current_category.id,
                        list_data.get('list_group')
                    )

                # Crear ListWidget
                list_widget = ListWidget(
                    list_data=list_data,
                    category_id=int(self.current_category.id) if hasattr(self.current_category, 'id') and self.current_category.id else None,
                    list_items=list_items
                )

                # Conectar señales
                list_widget.list_executed.connect(self.on_list_executed)
                list_widget.list_edited.connect(self.on_list_edit_requested)
                list_widget.list_deleted.connect(self.on_list_delete_requested)
                list_widget.copy_all_requested.connect(self.on_list_copy_all_requested)
                list_widget.item_copied.connect(self.on_list_item_copied)

                self.items_layout.insertWidget(self.items_layout.count() - 1, list_widget)

        logger.info(f"Successfully displayed {len(items_to_display) if items else 0}/{len(items)} items and {len(lists_to_display) if lists else 0}/{len(lists)} lists")

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

    def on_table_view_requested(self, table_name: str):
        """Handle table view request from ItemButton or TableGroupWidget"""
        logger.info(f"Table view requested: {table_name}")

        try:
            # Get DBManager from config_manager
            db = self.config_manager.db if self.config_manager else None

            if not db:
                logger.error("No database manager available")
                return

            # Open TableViewDialog
            dialog = TableViewDialog(db, table_name, parent=self)
            dialog.show()

        except Exception as e:
            logger.error(f"Error opening table view: {e}", exc_info=True)

    def on_web_static_render_requested(self, item):
        """Handle WEB_STATIC render request from ItemButton"""
        logger.info(f"WEB_STATIC render requested: {item.label}")

        try:
            from views.dialogs.embedded_browser_dialog import EmbeddedBrowserDialog

            # Abrir diálogo con navegador embebido
            dialog = EmbeddedBrowserDialog(html_content=item.content, parent=self)
            dialog.setWindowTitle(f"🌐 {item.label}")
            dialog.show()  # Usar show() en lugar de exec() para que sea no-modal

            logger.info(f"WEB_STATIC dialog opened for item: {item.label}")

        except Exception as e:
            logger.error(f"Error opening WEB_STATIC renderer: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Error al renderizar item web estático:\n\n{str(e)}"
            )

    def on_item_state_changed(self, item_id: str):
        """Handle item state change (favorite/archived) from ItemDetailsDialog"""
        logger.info(f"Item {item_id} state changed, refreshing panel")
        # Reload category from database to get updated data
        if self.current_category and self.config_manager:
            logger.debug(f"Reloading category {self.current_category.id} from database")
            refreshed_category = self.config_manager.get_category(self.current_category.id)
            if refreshed_category:
                self.load_category(refreshed_category)
            else:
                logger.error(f"Could not reload category {self.current_category.id}")

    # ========== LIST WIDGET HANDLERS ==========

    def on_list_executed(self, list_group: str, category_id: int):
        """Handle list execution request from ListWidget"""
        logger.info(f"Executing list '{list_group}' from category {category_id}")

        if not self.list_controller:
            logger.warning("No ListController available for execution")
            return

        try:
            # Ejecutar lista secuencialmente con delay de 500ms
            success = self.list_controller.execute_list_sequentially(
                category_id=category_id,
                list_group=list_group,
                delay_ms=500
            )

            if success:
                logger.info(f"List '{list_group}' execution started successfully")
            else:
                logger.warning(f"Failed to start list '{list_group}' execution")

        except Exception as e:
            logger.error(f"Error executing list '{list_group}': {e}", exc_info=True)

    def on_list_edit_requested(self, list_group: str, category_id: int):
        """Handle list edit request from ListWidget"""
        logger.info(f"Edit requested for list '{list_group}' from category {category_id}")
        logger.info(f"Current category: {self.current_category.name if self.current_category else 'None'}")
        logger.info(f"Current category ID: {self.current_category.id if hasattr(self.current_category, 'id') else 'No ID attribute'}")

        if not self.list_controller:
            logger.error("No ListController available for editing - Panel was created without controller")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error",
                "ListController no disponible.\n\nPor favor reinicia la aplicación."
            )
            return

        try:
            # Obtener categorías para el editor
            categories = []
            if self.config_manager:
                categories = self.config_manager.get_categories()
                logger.info(f"Loaded {len(categories)} categories for editor dialog")

            # Crear y mostrar dialog de edición
            editor_dialog = ListEditorDialog(
                list_controller=self.list_controller,
                categories=categories,
                category_id=category_id,
                list_group=list_group,
                parent=self
            )

            # Conectar señal de lista actualizada
            editor_dialog.list_updated.connect(self.on_list_updated_from_dialog)

            # Mostrar dialog
            result = editor_dialog.exec()

            logger.info(f"List editor dialog closed with result: {result}")

        except Exception as e:
            logger.error(f"Error opening list editor: {e}", exc_info=True)

    def on_list_delete_requested(self, list_group: str, category_id: int):
        """Handle list deletion request from ListWidget"""
        logger.info(f"Delete requested for list '{list_group}' from category {category_id}")

        if not self.list_controller:
            logger.warning("No ListController available for deletion")
            return

        try:
            # Eliminar la lista
            success, message = self.list_controller.delete_list(category_id, list_group)

            if success:
                logger.info(f"List '{list_group}' deleted successfully")

                # Recargar categoría para reflejar cambios
                if self.current_category:
                    # Necesitamos actualizar la categoría desde la base de datos
                    # Por ahora solo recargamos la vista
                    self.all_lists = self.list_controller.get_lists(category_id)
                    self.display_items_and_lists(self.all_items, self.all_lists)
            else:
                logger.warning(f"Failed to delete list '{list_group}': {message}")

        except Exception as e:
            logger.error(f"Error deleting list '{list_group}': {e}", exc_info=True)

    def on_list_copy_all_requested(self, list_group: str, category_id: int):
        """Handle copy all request from ListWidget"""
        logger.info(f"Copy all requested for list '{list_group}' from category {category_id}")

        if not self.list_controller:
            logger.error("No ListController available for copy operation - Panel was created without controller")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error",
                "ListController no disponible.\n\nPor favor reinicia la aplicación."
            )
            return

        try:
            # Copiar todo el contenido de la lista
            success, message = self.list_controller.copy_all_list_items(
                category_id=category_id,
                list_group=list_group,
                separator='\n'
            )

            if success:
                logger.info(f"All items from list '{list_group}' copied to clipboard")
            else:
                logger.warning(f"Failed to copy list '{list_group}': {message}")

        except Exception as e:
            logger.error(f"Error copying list '{list_group}': {e}", exc_info=True)

    def on_list_item_copied(self, content: str):
        """Handle individual list item copy"""
        logger.info(f"List item copied: {content[:50]}...")
        # El contenido ya fue copiado por el ListWidget, solo loguear

    def on_copy_all_clicked(self):
        """Handle click on 'Copiar Todo' button - Copy all visible items to clipboard"""
        logger.info("Copy All button clicked")

        if not self.visible_items:
            logger.warning("No visible items to copy")
            return

        try:
            from PyQt6.QtWidgets import QApplication

            # Collect all item contents
            all_contents = []
            for item in self.visible_items:
                if item.content:
                    # Format: Label: Content
                    all_contents.append(f"{item.label}: {item.content}")

            if not all_contents:
                logger.warning("No content to copy from visible items")
                return

            # Join all contents with double newlines for readability
            combined_content = "\n\n".join(all_contents)

            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(combined_content)

            logger.info(f"Copied {len(self.visible_items)} items to clipboard")

            # Visual feedback: Change button text temporarily
            original_text = self.copy_all_button.text()
            self.copy_all_button.setText("✅ Copiado!")
            QTimer.singleShot(1500, lambda: self.copy_all_button.setText(original_text))

        except Exception as e:
            logger.error(f"Error copying all items: {e}", exc_info=True)

    def on_new_list_clicked(self):
        """Handle click on 'Nueva Lista' button"""
        logger.info("New list button clicked")

        if not self.current_category or not self.list_controller:
            logger.warning("Cannot create list: no category or list controller")
            return

        try:
            # Obtener categorías desde config_manager
            categories = []
            if self.config_manager:
                categories = self.config_manager.get_categories()
                logger.info(f"Loaded {len(categories)} categories for dialog")

            # Crear y mostrar dialog de creación
            db_path = str(self.config_manager.db.db_path) if self.config_manager and hasattr(self.config_manager, 'db') else None
            creator_dialog = ListCreatorDialog(
                list_controller=self.list_controller,
                categories=categories,
                db_path=db_path,
                selected_category_id=int(self.current_category.id) if hasattr(self.current_category, 'id') and self.current_category.id else None,
                parent=self
            )

            # Conectar señal de lista creada
            creator_dialog.list_created.connect(self.on_list_created_from_dialog)

            # Mostrar dialog
            result = creator_dialog.exec()

            logger.info(f"List creator dialog closed with result: {result}")

        except Exception as e:
            logger.error(f"Error opening list creator: {e}", exc_info=True)

    def on_list_created_from_dialog(self, list_name: str, category_id: int, item_ids: list):
        """Handle list creation from ListCreatorDialog"""
        logger.info(f"List '{list_name}' created successfully in category {category_id} with {len(item_ids)} items")

        # Recargar la categoría para mostrar la nueva lista
        if self.current_category and hasattr(self.current_category, 'id'):
            if int(self.current_category.id) == category_id:
                # Recargar items y listas desde la base de datos
                self.reload_current_category()

    def on_list_updated_from_dialog(self, list_name: str, category_id: int):
        """Handle list update from ListEditorDialog"""
        logger.info(f"List '{list_name}' updated successfully in category {category_id}")

        # Recargar la categoría para mostrar cambios
        if self.current_category and hasattr(self.current_category, 'id'):
            if int(self.current_category.id) == category_id:
                self.reload_current_category()

    def reload_current_category(self):
        """Reload current category from database"""
        if not self.current_category or not self.config_manager:
            logger.warning("Cannot reload: no current category or config manager")
            return

        try:
            # Obtener items actualizados desde DB
            if hasattr(self.current_category, 'id'):
                category_id = int(self.current_category.id)

                # Obtener items desde config_manager
                if hasattr(self.config_manager, 'db'):
                    all_items_from_db = self.config_manager.db.get_items_by_category(category_id)

                    # Actualizar items en la categoría
                    from models.item import Item
                    self.current_category.items = [Item.from_dict(item_dict) for item_dict in all_items_from_db]

                    # Separar items normales
                    self.all_items = [item for item in self.current_category.items if not item.is_list_item()]

                    # Recargar listas
                    if self.list_controller:
                        self.all_lists = self.list_controller.get_lists(category_id)

                    # Re-renderizar
                    self.display_items_and_lists(self.all_items, self.all_lists)

                    logger.info(f"Category reloaded successfully: {len(self.all_items)} items, {len(self.all_lists)} lists")

        except Exception as e:
            logger.error(f"Error reloading category: {e}", exc_info=True)

    def on_search_changed(self, query: str):
        """Handle search query change with filtering"""
        if not self.current_category:
            return

        # Aplicar filtros avanzados primero a items
        filtered_items = self.filter_engine.apply_filters(self.all_items, self.current_filters)

        # Aplicar filtro de estado (is_active, is_archived)
        filtered_items = self.filter_items_by_state(filtered_items)

        # Filtrar listas (por ahora solo por nombre)
        filtered_lists = self.all_lists.copy()

        # Luego aplicar búsqueda si hay query
        if query and query.strip():
            # Buscar en items
            from models.category import Category
            temp_category = Category(
                category_id="temp",
                name="temp",
                icon=""
            )
            # Asignar items después de crear la categoría
            temp_category.items = filtered_items
            filtered_items = self.search_engine.search_in_category(query, temp_category)

            # Buscar en nombres de listas
            query_lower = query.lower()
            filtered_lists = [
                list_data for list_data in filtered_lists
                if query_lower in list_data.get('list_group', '').lower()
            ]

        self.display_items_and_lists(filtered_items, filtered_lists)

        # Update filter badge when search changes
        self.update_filter_badge()

    def on_display_options_changed(self):
        """Handle changes in display options checkboxes - refresh item widgets"""
        logger.info("Display options changed - refreshing items")

        # Get current display state
        show_labels = self.show_labels_checkbox.isChecked()
        show_tags = self.show_tags_checkbox.isChecked()
        show_content = self.show_content_checkbox.isChecked()
        show_description = self.show_description_checkbox.isChecked()

        logger.debug(f"Display options: labels={show_labels}, tags={show_tags}, content={show_content}, description={show_description}")

        # Re-render all items with new display options
        # This will recreate all ItemButton widgets with the updated display mode
        current_query = self.search_bar.search_input.text()
        self.on_search_changed(current_query)

    def on_filters_changed(self, filters: dict):
        """Handle cuando cambian los filtros avanzados"""
        logger.info(f"Filters changed: {filters}")
        self.current_filters = filters

        # Re-aplicar búsqueda y filtros
        current_query = self.search_bar.search_input.text()
        self.on_search_changed(current_query)

        # Update filter badge
        self.update_filter_badge()

        # AUTO-UPDATE: Trigger panel state save with new filters
        logger.debug(f"[AUTO-SAVE CHECK] is_pinned={self.is_pinned}, panel_id={self.panel_id}, config_manager={self.config_manager is not None}")
        if self.is_pinned and self.panel_id and self.config_manager:
            self.update_timer.start(self.update_delay_ms)
            logger.info(f"[AUTO-SAVE] Filter change triggered auto-save timer ({self.update_delay_ms}ms)")
        else:
            logger.warning(f"[AUTO-SAVE] Skipped - panel not ready for auto-save")

    def on_filters_cleared(self):
        """Handle cuando se limpian todos los filtros"""
        logger.info("All filters cleared")
        self.current_filters = {}

        # Re-aplicar búsqueda sin filtros
        current_query = self.search_bar.search_input.text()
        self.on_search_changed(current_query)

        # Update filter badge
        self.update_filter_badge()

        # AUTO-UPDATE: Trigger panel state save with cleared filters
        if self.is_pinned and self.panel_id and self.config_manager:
            self.update_timer.start(self.update_delay_ms)
            logger.debug("Filter clear triggered auto-save")

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

        # AUTO-UPDATE: Trigger panel state save with new state filter
        logger.debug(f"[AUTO-SAVE CHECK] is_pinned={self.is_pinned}, panel_id={self.panel_id}, config_manager={self.config_manager is not None}")
        if self.is_pinned and self.panel_id and self.config_manager:
            self.update_timer.start(self.update_delay_ms)
            logger.info(f"[AUTO-SAVE] State filter change triggered auto-save timer ({self.update_delay_ms}ms)")
        else:
            logger.warning(f"[AUTO-SAVE] Skipped - panel not ready for auto-save")

    def update_filter_badge(self):
        """Actualizar badge de filtros activos en el header"""
        filter_count = 0

        # Contar filtros avanzados activos
        if self.current_filters:
            filter_count += len(self.current_filters)

        # Contar filtro de estado (si no es 'normal')
        if self.current_state_filter != "normal":
            filter_count += 1

        # Contar búsqueda activa
        if hasattr(self, 'search_bar') and self.search_bar:
            if hasattr(self.search_bar, 'search_input'):
                search_text = self.search_bar.search_input.text().strip()
                if search_text:
                    filter_count += 1

        # Mostrar/ocultar badge según la cantidad de filtros
        if filter_count > 0:
            self.filter_badge.setText(f"🔍 {filter_count}")
            self.filter_badge.setVisible(True)
            tooltip_parts = []
            if self.current_filters:
                tooltip_parts.append(f"{len(self.current_filters)} filtro(s) avanzado(s)")
            if self.current_state_filter != "normal":
                tooltip_parts.append(f"Estado: {self.current_state_filter}")
            if hasattr(self, 'search_bar') and self.search_bar and self.search_bar.search_input.text().strip():
                tooltip_parts.append(f"Búsqueda activa")
            self.filter_badge.setToolTip(" | ".join(tooltip_parts))
        else:
            self.filter_badge.setVisible(False)

    def filter_items_by_state(self, items):
        """Filtrar items por estado (activo/archivado)

        Args:
            items: Lista de items a filtrar

        Returns:
            Lista de items filtrados según el estado actual
        """
        if self.current_state_filter == "all":
            # Mostrar todos los items
            return items
        elif self.current_state_filter == "normal":
            # Mostrar solo items activos y NO archivados
            return [item for item in items if getattr(item, 'is_active', True) and not getattr(item, 'is_archived', False)]
        elif self.current_state_filter == "archived":
            # Mostrar solo items archivados (independiente de si están activos)
            return [item for item in items if getattr(item, 'is_archived', False)]
        elif self.current_state_filter == "inactive":
            # Mostrar solo items inactivos
            return [item for item in items if not getattr(item, 'is_active', True)]
        else:
            return items

    def apply_filter_config(self, filter_config: dict):
        """Apply saved filter configuration to panel

        Args:
            filter_config: Dict with 'advanced_filters', 'state_filter', and 'search_text'
        """
        if not filter_config:
            logger.debug("No filter config to apply")
            return

        try:
            logger.info(f"Applying filter configuration: {filter_config}")

            # Apply advanced filters
            if 'advanced_filters' in filter_config:
                self.current_filters = filter_config['advanced_filters']
                logger.debug(f"Applied advanced filters: {self.current_filters}")

            # Apply state filter and update combo box
            if 'state_filter' in filter_config:
                state_filter = filter_config['state_filter']
                self.current_state_filter = state_filter

                # Update combo box to match (without triggering signal)
                state_index_map = {
                    'normal': 0,
                    'archived': 1,
                    'inactive': 2,
                    'all': 3
                }
                if state_filter in state_index_map:
                    self.state_filter_combo.blockSignals(True)
                    self.state_filter_combo.setCurrentIndex(state_index_map[state_filter])
                    self.state_filter_combo.blockSignals(False)
                    logger.debug(f"Applied state filter: {state_filter}")

            # Apply search text and update search bar
            if 'search_text' in filter_config:
                search_text = filter_config['search_text']
                if search_text:
                    self.search_bar.search_input.blockSignals(True)
                    self.search_bar.search_input.setText(search_text)
                    self.search_bar.search_input.blockSignals(False)
                    logger.debug(f"Applied search text: {search_text}")

            # Trigger filter application
            current_query = self.search_bar.search_input.text()
            self.on_search_changed(current_query)

            logger.info("Filter configuration applied successfully")
        except Exception as e:
            logger.error(f"Error applying filter config: {e}", exc_info=True)

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
        logger.debug(f"Positioned floating panel at ({panel_x}, {panel_y})")

    # mousePressEvent y mouseMoveEvent no están definidos aquí
    # porque PanelResizer maneja todo a través de su eventFilter.
    # El eventFilter detecta si estás en un borde (resize) o en el centro (drag).

    def on_panel_resized(self, width: int, height: int):
        """Handle panel resize completion from PanelResizer"""
        logger.info(f"Panel resized to: {width}x{height}")

        # Save new dimensions to config
        if self.config_manager:
            self.config_manager.set_setting('panel_width', width)
            self.config_manager.set_setting('panel_height', height)

            # Save to panel_settings table if db_manager is available
            if hasattr(self.config_manager, 'db_manager') and self.config_manager.db_manager:
                self.config_manager.db_manager.save_panel_settings(
                    panel_name='floating_panel',
                    width=width,
                    height=height,
                    x=self.x(),
                    y=self.y()
                )

        # Trigger auto-save for pinned panels
        if self.is_pinned and self.panel_id and self.config_manager:
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

    def contextMenuEvent(self, event):
        """Mostrar menú contextual en panel anclado con click derecho"""
        if not self.is_pinned:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.theme.get_color('background_mid')};
                color: {self.theme.get_color('text_primary')};
                border: 2px solid {self.theme.get_color('primary')};
                border-radius: 8px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 25px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.theme.get_color('primary')};
            }}
            QMenu::separator {{
                height: 1px;
                background: {self.theme.get_color('surface')};
                margin: 5px 10px;
            }}
        """)

        # Acciones de filtros
        save_filters_action = menu.addAction("💾 Guardar filtros actuales")
        save_filters_action.triggered.connect(self._save_panel_state_to_db)

        clear_filters_action = menu.addAction("🧹 Limpiar todos los filtros")
        clear_filters_action.triggered.connect(self._clear_all_filters)

        menu.addSeparator()

        # Acciones de panel
        manager_action = menu.addAction("📍 Abrir gestor de paneles")
        manager_action.triggered.connect(self._open_panels_manager)

        customize_action = menu.addAction("✏️ Personalizar panel")
        customize_action.triggered.connect(self.on_config_clicked)

        menu.addSeparator()

        # Info
        info_action = menu.addAction("ℹ️ Información del panel")
        info_action.triggered.connect(self._show_panel_info)

        menu.exec(event.globalPos())

    def _clear_all_filters(self):
        """Limpiar todos los filtros del panel"""
        # Limpiar filtros avanzados
        self.on_filters_cleared()

        # Restablecer filtro de estado a "normal"
        if hasattr(self, 'state_filter_combo'):
            for i in range(self.state_filter_combo.count()):
                if self.state_filter_combo.itemData(i) == "normal":
                    self.state_filter_combo.setCurrentIndex(i)
                    break

        # Limpiar texto de búsqueda
        if hasattr(self, 'search_bar') and self.search_bar:
            if hasattr(self.search_bar, 'search_input'):
                self.search_bar.search_input.clear()

        logger.info("All filters cleared via context menu")

    def _open_panels_manager(self):
        """Abrir ventana de gestión de paneles"""
        # Buscar MainWindow y llamar a show_pinned_panels_manager()
        if self.main_window and hasattr(self.main_window, 'show_pinned_panels_manager'):
            self.main_window.show_pinned_panels_manager()
        else:
            logger.warning("Cannot open panels manager - main_window reference not available")

    def _show_panel_info(self):
        """Mostrar información del panel"""
        from PyQt6.QtWidgets import QMessageBox

        # Contar filtros activos
        filter_count = 0
        if self.current_filters:
            filter_count += len(self.current_filters)
        if self.current_state_filter != "normal":
            filter_count += 1
        if hasattr(self, 'search_bar') and self.search_bar and self.search_bar.search_input.text().strip():
            filter_count += 1

        # Construir mensaje de información
        category_name = self.current_category.name if self.current_category else 'N/A'
        panel_name = self.custom_name or category_name

        info_text = f"""
        <h3>📍 Información del Panel</h3>
        <table style="width: 100%;">
            <tr><td><b>ID:</b></td><td>{self.panel_id if self.panel_id else 'No guardado'}</td></tr>
            <tr><td><b>Nombre:</b></td><td>{panel_name}</td></tr>
            <tr><td><b>Categoría:</b></td><td>{category_name}</td></tr>
            <tr><td><b>Estado:</b></td><td>{'📍 Anclado' if self.is_pinned else 'Flotante'}</td></tr>
            <tr><td><b>Filtros activos:</b></td><td>{filter_count}</td></tr>
            <tr><td><b>Items visibles:</b></td><td>{len(self.visible_items)}/{len(self.all_items)}</td></tr>
        </table>
        """

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Información del Panel")
        msg_box.setText(info_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.theme.get_color('background_mid')};
            }}
            QLabel {{
                color: {self.theme.get_color('text_primary')};
            }}
        """)
        msg_box.exec()

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

    def toggle_pin(self):
        """Toggle panel pin state"""
        self.is_pinned = not self.is_pinned

        # Update pin button appearance
        if self.is_pinned:
            self.pin_button.setText("📍")  # Pinned icon
            self.pin_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 200, 0, 0.3);
                    color: #ffffff;
                    border: 1px solid rgba(0, 200, 0, 0.6);
                    border-radius: 12px;
                    font-size: 10pt;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 200, 0, 0.4);
                    border: 1px solid rgba(0, 200, 0, 0.8);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 200, 0, 0.5);
                }
            """)
            self.pin_button.setToolTip("Desanclar panel")

            # Show minimize and config buttons when pinned
            self.minimize_button.setVisible(True)
            self.config_button.setVisible(True)
            logger.info(f"Panel '{self.header_label.text()}' ANCLADO - puede abrir otros paneles")
        else:
            self.pin_button.setText("📌")  # Unpinned icon
            self.pin_button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.1);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 12px;
                    font-size: 10pt;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.4);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.3);
                }
            """)
            self.pin_button.setToolTip("Anclar panel (permite abrir múltiples paneles)")

            # Hide minimize and config buttons when unpinned
            self.minimize_button.setVisible(False)
            self.config_button.setVisible(False)

            # If panel was minimized, restore it before unpinning
            if self.is_minimized:
                self.toggle_minimize()  # Restore to normal state

            logger.info(f"Panel '{self.header_label.text()}' DESANCLADO")

        # Emit signal
        self.pin_state_changed.emit(self.is_pinned)

    def toggle_minimize(self):
        """Toggle panel minimize state (only for pinned panels)"""
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
            self.display_options_widget.setVisible(False)  # Hide display options checkboxes
            self.scroll_area.setVisible(False)

            # Reduce header margins for compact look
            self.header_layout.setContentsMargins(8, 3, 5, 3)

            # CRITICAL: Remove size constraints temporarily to allow small size
            self.setMinimumWidth(0)
            self.setMinimumHeight(0)

            # Resize to compact size (height: 50px for buttons visibility, width: ~250px)
            minimized_height = 50  # Increased to 50px for better button visibility
            minimized_width = 250  # Increased width to show all buttons
            self.resize(minimized_width, minimized_height)

            # Set fixed size when minimized to prevent unwanted resizing
            self.setFixedSize(minimized_width, minimized_height)

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
            self.display_options_widget.setVisible(True)  # Show display options checkboxes
            self.scroll_area.setVisible(True)

            # Restore header margins
            self.header_layout.setContentsMargins(15, 10, 10, 10)

            # Remove fixed size constraint to allow resizing again
            self.setFixedSize(16777215, 16777215)  # Maximum QWidget size (effectively removes fixed size)

            # CRITICAL: Restore size constraints
            self.setMinimumWidth(PanelStyles.PANEL_WIDTH_MIN)
            self.setMinimumHeight(PanelStyles.PANEL_HEIGHT_MIN)
            self.setMaximumWidth(PanelStyles.PANEL_WIDTH_MAX)
            self.setMaximumHeight(PanelStyles.PANEL_HEIGHT_MAX)

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

    def apply_custom_styling(self):
        """Apply custom color to panel header if custom_color is set"""
        if self.custom_color:
            self.header_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {self.custom_color};
                    border-radius: 6px 6px 0 0;
                }}
            """)
            logger.info(f"Applied custom color to panel: {self.custom_color}")
        else:
            # Restore default styling
            self.header_widget.setStyleSheet("""
                QWidget {
                    background-color: #007acc;
                    border-radius: 6px 6px 0 0;
                }
            """)
            logger.debug("Restored default header color")

    def get_display_name(self) -> str:
        """Get name to display in header (custom name takes priority over category name)"""
        if self.custom_name:
            return self.custom_name
        elif self.current_category:
            return self.current_category.name
        else:
            return "Select a category"

    def update_header_title(self):
        """Update the header label with current display name"""
        display_name = self.get_display_name()
        self.header_label.setText(display_name)
        logger.debug(f"Updated header title to: {display_name}")

    def update_customization(self, custom_name: str = None, custom_color: str = None):
        """Update panel customization (name and/or color)

        Args:
            custom_name: New custom name (None to keep unchanged)
            custom_color: New custom color in hex format (None to keep unchanged)
        """
        if custom_name is not None:
            self.custom_name = custom_name
            self.update_header_title()
            logger.info(f"Updated panel custom name to: {custom_name}")

        if custom_color is not None:
            self.custom_color = custom_color
            self.apply_custom_styling()
            logger.info(f"Updated panel custom color to: {custom_color}")

    def on_config_clicked(self):
        """Handle config button click - emit signal for parent to handle"""
        logger.info(f"Config button clicked for panel: {self.get_display_name()}")
        self.customization_requested.emit()

    def closeEvent(self, event):
        """Handle window close event"""
        # Si ya estamos cerrando con animación, aceptar y salir
        if hasattr(self, '_closing_with_animation') and self._closing_with_animation:
            self.window_closed.emit()
            event.accept()
            return

        # Primera vez: iniciar animación
        event.ignore()

        # Cerrar también la ventana de filtros si está abierta
        if self.filters_window.isVisible():
            self.filters_window.close()

        # Marcar que estamos en proceso de cierre
        self._closing_with_animation = True

        # Crear y ejecutar animación de fade-out
        animation = PanelStyles.create_fade_out_animation(self, duration=150)

        # Cuando termine la animación, cerrar realmente
        def on_animation_finished():
            # Usar QWidget.close() directamente para evitar recursión
            from PyQt6.QtWidgets import QWidget
            QWidget.close(self)

        animation.finished.connect(on_animation_finished)
        animation.start()

        # Guardar referencia para que no se destruya
        self._close_animation = animation

    def moveEvent(self, event):
        """AUTO-UPDATE: Handle window move event - save position to database (debounced)"""
        super().moveEvent(event)

        # Only save if this is a pinned panel with a panel_id
        if self.is_pinned and self.panel_id and self.config_manager:
            # Restart the debounce timer
            self.update_timer.start(self.update_delay_ms)

    def resizeEvent(self, event):
        """AUTO-UPDATE: Handle window resize event - save size to database (debounced)"""
        super().resizeEvent(event)

        # Only save if this is a pinned panel with a panel_id
        if self.is_pinned and self.panel_id and self.config_manager:
            # Restart the debounce timer
            self.update_timer.start(self.update_delay_ms)

    def _save_panel_state_to_db(self):
        """AUTO-UPDATE: Save current panel state (position/size/filters) to database"""
        logger.info(f"[AUTO-SAVE] _save_panel_state_to_db() called for panel {self.panel_id}")

        # Only save if this is a pinned panel with a valid panel_id
        if not self.is_pinned or not self.panel_id or not self.config_manager:
            logger.warning(f"[AUTO-SAVE] Cannot save - is_pinned={self.is_pinned}, panel_id={self.panel_id}, config_manager={self.config_manager is not None}")
            return

        try:
            # Log current filter state
            logger.info(f"[AUTO-SAVE] Current filters state:")
            logger.info(f"  - current_filters: {self.current_filters}")
            logger.info(f"  - current_state_filter: {self.current_state_filter}")
            logger.info(f"  - search_text: '{self.search_bar.search_input.text()}'")

            # Use direct reference to MainWindow (no need to search parent chain)
            if not self.main_window:
                logger.warning("[AUTO-SAVE] main_window reference is None - skipping panel state save")
                return

            if not self.main_window.controller:
                logger.warning("[AUTO-SAVE] main_window.controller is None - skipping panel state save")
                return

            # Get the PinnedPanelsManager
            panels_manager = self.main_window.controller.pinned_panels_manager

            # Update panel state in database
            panels_manager.update_panel_state(
                panel_id=self.panel_id,
                panel_widget=self
            )

            logger.info(f"[AUTO-SAVE] Panel {self.panel_id} state saved successfully (Position: {self.pos()}, Size: {self.size()})")

        except Exception as e:
            logger.error(f"[AUTO-SAVE] Error auto-saving panel state: {e}", exc_info=True)
