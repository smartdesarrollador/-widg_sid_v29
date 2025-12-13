"""
Left Sidebar Manager - Barra lateral izquierda para ventanas/paneles minimizados

Características:
- Barra vertical de 70px en el borde izquierdo
- Dos secciones: Paneles flotantes (superior) y Ventanas especiales (inferior)
- Aparece solo cuando hay items minimizados
- Animaciones de entrada/salida
- Scroll vertical independiente por sección
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QMenu, QSizePolicy, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QPoint, QTimer
from PyQt6.QtGui import QCursor, QColor, QFont
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Constantes de diseño
COLORS = {
    'sidebar_background': '#0f0f1e',
    'header_background': '#1a1a2e',
    'footer_background': '#1a1a2e',
    'panels_section_bg': '#16213e',
    'windows_section_bg': '#0e1621',
    'separator': '#00ccff',
    'button_normal': '#2d2d2d',
    'button_hover': '#3d3d3d',
    'button_pressed': '#1d1d1d',
    'border_panels': '#00ccff',
    'border_windows': '#ff00ff',
    'text_primary': '#ffffff',
    'text_secondary': '#aaaaaa',
    'badge_bg': '#ff4444',
    'badge_text': '#ffffff',
}

DIMENSIONS = {
    'sidebar_width': 70,
    'sidebar_height_percent': 0.8,
    'margin_top_percent': 0.1,
    'header_height': 50,
    'footer_height': 60,
    'separator_height': 3,
    'button_size': 60,
    'button_margin': 5,
    'icon_size': 28,
    'badge_size': 18,
    'border_width': 3,
    'border_radius': 10,
    'peek_width': 5,  # Ancho del borde visible cuando está colapsada
}


class MinimizedItemButton(QPushButton):
    """Botón que representa un item minimizado (panel o ventana)"""

    restore_requested = pyqtSignal(object)
    close_requested = pyqtSignal(object)

    def __init__(self, window, item_type='panel', parent=None):
        super().__init__(parent)
        self.window = window
        self.item_type = item_type  # 'panel' o 'window'
        self.window_title = self._get_window_title()
        self.window_icon = self._get_window_icon()

        self._setup_button()

    def _get_window_title(self) -> str:
        """Obtener título de la ventana"""
        if hasattr(self.window, 'entity_name'):
            return self.window.entity_name
        elif hasattr(self.window, 'windowTitle'):
            return self.window.windowTitle()
        return "Untitled"

    def _get_window_icon(self) -> str:
        """Obtener ícono de la ventana"""
        if hasattr(self.window, 'entity_icon') and self.window.entity_icon:
            return self.window.entity_icon

        # Iconos por defecto según tipo de clase
        class_name = self.window.__class__.__name__
        icons_map = {
            'FloatingPanel': '📂',
            'FavoritesFloatingPanel': '⭐',
            'StatsFloatingPanel': '📈',
            'ProcessFloatingPanel': '⚙️',
            'GlobalSearchPanel': '🔍',
            'RelatedItemsFloatingPanel': '📄',
            'ProcessesFloatingPanel': '⚙️',
            'AdvancedSearchWindow': '🔍',
            'ProjectsWindow': '📁',
            'AreasWindow': '🗂️',
            'StructureDashboard': '📊',
            'CategoryManagerWindow': '📂',
        }
        return icons_map.get(class_name, '🪟')

    def _setup_button(self):
        """Configurar apariencia del botón"""
        # Tamaño fijo
        button_size = DIMENSIONS['button_size']
        self.setFixedSize(button_size, button_size)

        # Ícono como texto
        self.setText(self.window_icon)

        # Font para emoji
        font = QFont()
        font.setPointSize(DIMENSIONS['icon_size'])
        self.setFont(font)

        # Tooltip
        self.setToolTip(f"{self.window_title}\n\nClick: Restaurar\nClick derecho: Opciones")

        # Cursor
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Estilo según tipo
        border_color = COLORS['border_panels'] if self.item_type == 'panel' else COLORS['border_windows']

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['button_normal']};
                color: {COLORS['text_primary']};
                border: {DIMENSIONS['border_width']}px solid {border_color};
                border-radius: {DIMENSIONS['border_radius']}px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_hover']};
                border-color: {border_color};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['button_pressed']};
            }}
        """)

        # Sombra
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

        # Conectar señales
        self.clicked.connect(self._on_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _on_clicked(self):
        """Manejar click para restaurar"""
        self.restore_requested.emit(self.window)

    def _show_context_menu(self, position):
        """Mostrar menú contextual"""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['sidebar_background']};
                color: {COLORS['text_primary']};
                border: 2px solid {COLORS['separator']};
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['separator']};
                color: #000000;
            }}
        """)

        # Acciones
        restore_action = menu.addAction(f"📖 Restaurar")
        restore_action.triggered.connect(lambda: self.restore_requested.emit(self.window))

        menu.addSeparator()

        close_action = menu.addAction("✕ Cerrar")
        close_action.triggered.connect(lambda: self.close_requested.emit(self.window))

        menu.exec(self.mapToGlobal(position))

    def enterEvent(self, event):
        """Animación al pasar mouse - Glow effect mejorado"""
        shadow = self.graphicsEffect()
        if shadow:
            shadow.setBlurRadius(25)
            border_color = COLORS['border_panels'] if self.item_type == 'panel' else COLORS['border_windows']
            # Cyan brillante para paneles, magenta para ventanas
            glow_color = QColor(0, 255, 136, 200) if self.item_type == 'panel' else QColor(255, 0, 255, 200)
            shadow.setColor(glow_color)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Restaurar al salir el mouse"""
        shadow = self.graphicsEffect()
        if shadow:
            shadow.setBlurRadius(15)
            shadow.setColor(QColor(0, 0, 0, 150))
        super().leaveEvent(event)


class MinimizedSection(QWidget):
    """Sección scrollable para items minimizados"""

    def __init__(self, section_title, section_type, parent=None):
        super().__init__(parent)
        self.section_title = section_title
        self.section_type = section_type  # 'panels' o 'windows'
        self.items = []  # Lista de ventanas en esta sección
        self.item_buttons = {}  # Dict: window -> button

        self.init_ui()

    def init_ui(self):
        """Inicializar UI de la sección"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(DIMENSIONS['button_margin'])

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Container para botones
        self.buttons_container = QWidget()
        self.buttons_layout = QVBoxLayout(self.buttons_container)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(DIMENSIONS['button_margin'])
        self.buttons_layout.addStretch()

        self.scroll_area.setWidget(self.buttons_container)

        # Color de fondo según tipo
        bg_color = COLORS['panels_section_bg'] if self.section_type == 'panels' else COLORS['windows_section_bg']

        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: #1a1a1a;
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['separator']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #00ff88;
            }}
        """)

        layout.addWidget(self.scroll_area)

    def add_item(self, window) -> MinimizedItemButton:
        """Agregar item a la sección"""
        if window in self.items:
            logger.warning(f"Item already in section: {window}")
            return None

        self.items.append(window)

        # Crear botón
        button = MinimizedItemButton(window, self.section_type)

        # Agregar al layout (antes del stretch)
        self.buttons_layout.insertWidget(self.buttons_layout.count() - 1, button)
        self.item_buttons[window] = button

        logger.info(f"Item added to {self.section_type} section")
        return button

    def remove_item(self, window):
        """Remover item de la sección"""
        if window not in self.items:
            return

        self.items.remove(window)

        # Remover botón
        if window in self.item_buttons:
            button = self.item_buttons[window]
            self.buttons_layout.removeWidget(button)
            button.deleteLater()
            del self.item_buttons[window]

        logger.info(f"Item removed from {self.section_type} section")

    def get_item_count(self) -> int:
        """Obtener cantidad de items"""
        return len(self.items)

    def clear_all(self):
        """Remover todos los items"""
        items_copy = self.items.copy()
        for item in items_copy:
            self.remove_item(item)


class LeftSidebarManager(QWidget):
    """Gestor de barra lateral izquierda para ventanas/paneles minimizados"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.panels_section = None
        self.windows_section = None
        self.all_items = {}  # Registro de todos los items: window -> section_type

        # Estado de expansión
        self.is_expanded = False

        # Timer para auto-hide
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.setInterval(3000)  # 3 segundos
        self.auto_hide_timer.timeout.connect(self._auto_hide)

        self.init_ui()
        self.hide()  # Oculto por defecto

        logger.info("LeftSidebarManager initialized")

    def init_ui(self):
        """Inicializar UI de la barra lateral"""
        # Window flags
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # No aparece en taskbar
        )

        # Tamaño fijo
        self.setFixedWidth(DIMENSIONS['sidebar_width'])

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === HEADER ===
        header = self._create_header()
        main_layout.addWidget(header)

        # === SECCIÓN 1: PANELES ===
        self.panels_section = MinimizedSection("Paneles", "panels")
        main_layout.addWidget(self.panels_section, 1)  # Stretch factor 1

        # === SEPARADOR ===
        separator = self._create_separator()
        main_layout.addWidget(separator)

        # === SECCIÓN 2: VENTANAS ===
        self.windows_section = MinimizedSection("Ventanas", "windows")
        main_layout.addWidget(self.windows_section, 1)  # Stretch factor 1

        # === FOOTER ===
        footer = self._create_footer()
        main_layout.addWidget(footer)

        # Estilo general
        self.setStyleSheet(f"""
            LeftSidebarManager {{
                background-color: {COLORS['sidebar_background']};
                border: {DIMENSIONS['border_width']}px solid {COLORS['separator']};
                border-left: none;
                border-radius: {DIMENSIONS['border_radius']}px;
            }}
        """)

        # Sombra
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(3)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 204, 255, 100))
        self.setGraphicsEffect(shadow)

        # Posicionar en pantalla
        self.position_on_screen()

    def _create_header(self) -> QWidget:
        """Crear header con título y contador"""
        header = QWidget()
        header.setFixedHeight(DIMENSIONS['header_height'])
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['header_background']};
                border-top-right-radius: {DIMENSIONS['border_radius']}px;
            }}
        """)

        layout = QVBoxLayout(header)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Label
        title_label = QLabel("📋")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 16pt;
                font-weight: bold;
            }}
        """)
        layout.addWidget(title_label)

        # Contador
        self.counter_label = QLabel("0")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['badge_text']};
                background-color: {COLORS['badge_bg']};
                font-size: 9pt;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 8px;
            }}
        """)
        layout.addWidget(self.counter_label)

        return header

    def _create_separator(self) -> QWidget:
        """Crear separador entre secciones"""
        separator = QWidget()
        separator.setFixedHeight(DIMENSIONS['separator_height'])
        separator.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['separator']};
            }}
        """)
        return separator

    def _create_footer(self) -> QWidget:
        """Crear footer con botones de acción"""
        footer = QWidget()
        footer.setFixedHeight(DIMENSIONS['footer_height'])
        footer.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['footer_background']};
                border-bottom-right-radius: {DIMENSIONS['border_radius']}px;
            }}
        """)

        layout = QVBoxLayout(footer)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Botón restaurar todo
        restore_btn = QPushButton("📖")
        restore_btn.setToolTip("Restaurar todo")
        restore_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        restore_btn.clicked.connect(self.restore_all)
        restore_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['button_normal']};
                color: #00ff88;
                border: 2px solid #00ff88;
                border-radius: 4px;
                padding: 4px;
                font-size: 14pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_hover']};
            }}
        """)
        layout.addWidget(restore_btn)

        # Botón cerrar todo
        close_btn = QPushButton("✕")
        close_btn.setToolTip("Cerrar todo")
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.clicked.connect(self.close_all)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['button_normal']};
                color: #ff4444;
                border: 2px solid #ff4444;
                border-radius: 4px;
                padding: 4px;
                font-size: 14pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_hover']};
            }}
        """)
        layout.addWidget(close_btn)

        return footer

    def position_on_screen(self):
        """Posicionar en borde izquierdo de la pantalla"""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()

            # Calcular altura (80% de pantalla)
            sidebar_height = int(screen_geometry.height() * DIMENSIONS['sidebar_height_percent'])
            self.setFixedHeight(sidebar_height)

            # Posición (borde izquierdo, centrado verticalmente)
            x = 0
            y = int((screen_geometry.height() - sidebar_height) / 2)

            self.move(x, y)

    def add_minimized_panel(self, panel):
        """Agregar panel flotante minimizado"""
        if panel in self.all_items:
            logger.warning(f"Panel already minimized: {panel}")
            return

        # Agregar a sección de paneles
        button = self.panels_section.add_item(panel)
        if button:
            button.restore_requested.connect(self.restore_item)
            button.close_requested.connect(self.close_item)

            self.all_items[panel] = 'panel'
            self._update_counter()
            self._update_visibility()

            # Expandir temporalmente si está en peek mode
            if self.isVisible() and not self.is_expanded:
                self._expand_from_peek()
                self._restart_auto_hide_timer()

            logger.info(f"Panel minimized: {button.window_title}")

    def add_minimized_window(self, window):
        """Agregar ventana especial minimizada"""
        if window in self.all_items:
            logger.warning(f"Window already minimized: {window}")
            return

        # Agregar a sección de ventanas
        button = self.windows_section.add_item(window)
        if button:
            button.restore_requested.connect(self.restore_item)
            button.close_requested.connect(self.close_item)

            self.all_items[window] = 'window'
            self._update_counter()
            self._update_visibility()

            # Expandir temporalmente si está en peek mode
            if self.isVisible() and not self.is_expanded:
                self._expand_from_peek()
                self._restart_auto_hide_timer()

            logger.info(f"Window minimized: {button.window_title}")

    def remove_minimized_item(self, item):
        """Remover item minimizado (panel o ventana)"""
        if item not in self.all_items:
            return

        item_type = self.all_items[item]

        # Remover de sección correspondiente
        if item_type == 'panel':
            self.panels_section.remove_item(item)
        else:
            self.windows_section.remove_item(item)

        del self.all_items[item]

        self._update_counter()
        self._update_visibility()

        logger.info(f"Item removed from sidebar: {item_type}")

    def restore_item(self, item):
        """Restaurar item minimizado"""
        if item in self.all_items:
            item.showNormal()
            item.activateWindow()
            item.raise_()
            self.remove_minimized_item(item)
            logger.info(f"Item restored")

    def close_item(self, item):
        """Cerrar item completamente"""
        if item in self.all_items:
            self.remove_minimized_item(item)
            item.close()
            logger.info(f"Item closed")

    def restore_all_panels(self):
        """Restaurar todos los paneles"""
        panels = [item for item, type_ in self.all_items.items() if type_ == 'panel']
        for panel in panels:
            self.restore_item(panel)

    def restore_all_windows(self):
        """Restaurar todas las ventanas"""
        windows = [item for item, type_ in self.all_items.items() if type_ == 'window']
        for window in windows:
            self.restore_item(window)

    def restore_all(self):
        """Restaurar todo"""
        items = list(self.all_items.keys())
        for item in items:
            self.restore_item(item)

    def close_all_panels(self):
        """Cerrar todos los paneles"""
        from PyQt6.QtWidgets import QMessageBox
        panels = [item for item, type_ in self.all_items.items() if type_ == 'panel']

        if not panels:
            return

        reply = QMessageBox.question(
            self,
            "Cerrar paneles",
            f"¿Cerrar {len(panels)} panel(es) minimizado(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for panel in panels:
                self.close_item(panel)

    def close_all_windows(self):
        """Cerrar todas las ventanas"""
        from PyQt6.QtWidgets import QMessageBox
        windows = [item for item, type_ in self.all_items.items() if type_ == 'window']

        if not windows:
            return

        reply = QMessageBox.question(
            self,
            "Cerrar ventanas",
            f"¿Cerrar {len(windows)} ventana(s) minimizada(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for window in windows:
                self.close_item(window)

    def close_all(self):
        """Cerrar todo"""
        from PyQt6.QtWidgets import QMessageBox

        if not self.all_items:
            return

        reply = QMessageBox.question(
            self,
            "Cerrar todo",
            f"¿Cerrar {len(self.all_items)} item(s) minimizado(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            items = list(self.all_items.keys())
            for item in items:
                self.close_item(item)

    def _restart_auto_hide_timer(self):
        """Reiniciar timer de auto-hide"""
        if len(self.all_items) > 0:
            self.auto_hide_timer.stop()
            self.auto_hide_timer.start()
            logger.debug("Auto-hide timer restarted")

    def _auto_hide(self):
        """Colapsar barra lateral a modo peek automáticamente"""
        if len(self.all_items) > 0 and self.is_expanded:
            logger.info("Auto-collapsing sidebar to peek mode after timeout")
            self._collapse_to_peek()

    def _show_sidebar(self):
        """Expandir barra lateral completamente y reiniciar timer"""
        if not self.is_expanded:
            self._expand_from_peek()
        self._restart_auto_hide_timer()

    def _collapse_to_peek(self):
        """Colapsar barra lateral a modo peek (solo borde visible)"""
        if not self.is_expanded:
            return

        self.is_expanded = False
        self.auto_hide_timer.stop()

        # Animación de colapso (mostrar solo peek)
        start_x = 0
        end_x = -(DIMENSIONS['sidebar_width'] - DIMENSIONS['peek_width'])

        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setStartValue(QPoint(start_x, self.y()))
        self.animation.setEndValue(QPoint(end_x, self.y()))
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.start()

        logger.info("Sidebar collapsed to peek mode")

    def _expand_from_peek(self):
        """Expandir barra lateral desde modo peek"""
        if self.is_expanded:
            return

        self.is_expanded = True

        # Animación de expansión (mostrar completa)
        start_x = self.x()
        end_x = 0

        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setStartValue(QPoint(start_x, self.y()))
        self.animation.setEndValue(QPoint(end_x, self.y()))
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.start()

        logger.info("Sidebar expanded from peek mode")

    def enterEvent(self, event):
        """Expandir cuando el mouse entra en el área de la barra"""
        if len(self.all_items) > 0:
            self.auto_hide_timer.stop()
            if not self.is_expanded:
                self._expand_from_peek()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Reiniciar auto-hide cuando el mouse sale de la barra"""
        if len(self.all_items) > 0 and self.is_expanded:
            self._restart_auto_hide_timer()
        super().leaveEvent(event)

    def _update_counter(self):
        """Actualizar contador total"""
        count = len(self.all_items)
        self.counter_label.setText(str(count))

    def _update_visibility(self):
        """Actualizar visibilidad de la barra"""
        if len(self.all_items) > 0:
            if not self.isVisible():
                self._show_expanded_temporarily()
        else:
            if self.isVisible():
                self._hide_completely()

    def _show_in_peek_mode(self):
        """Mostrar barra en modo peek (solo borde visible)"""
        self.show()
        self.position_on_screen()

        # Posicionar en modo peek (parcialmente oculta)
        peek_x = -(DIMENSIONS['sidebar_width'] - DIMENSIONS['peek_width'])
        self.move(peek_x, self.y())

        self.is_expanded = False
        logger.info("Left sidebar shown in peek mode")

    def _show_expanded_temporarily(self):
        """Mostrar barra expandida temporalmente, luego colapsar a peek después de 3 segundos"""
        self.show()
        self.position_on_screen()

        # Posicionar completamente visible
        self.move(0, self.y())
        self.is_expanded = True

        # Iniciar timer para colapsar a peek después de 3 segundos
        self._restart_auto_hide_timer()

        logger.info("Left sidebar shown expanded temporarily")

    def _hide_completely(self):
        """Ocultar completamente la barra"""
        # Animación de posición (slide hacia izquierda completamente)
        start_x = self.x()
        end_x = -self.width()

        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setStartValue(QPoint(start_x, self.y()))
        self.animation.setEndValue(QPoint(end_x, self.y()))
        self.animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.animation.finished.connect(self._on_hide_complete)
        self.animation.start()

        logger.info("Left sidebar hiding completely")

    def _on_hide_complete(self):
        """Callback cuando termina la animación de ocultar"""
        self.hide()
        self.is_expanded = False

    def resizeEvent(self, event):
        """Reposicionar al cambiar tamaño"""
        super().resizeEvent(event)
        self.position_on_screen()


# === SINGLETON GLOBAL ===
_left_sidebar_instance = None


def get_left_sidebar():
    """Obtener instancia única del gestor de barra lateral izquierda"""
    global _left_sidebar_instance
    if _left_sidebar_instance is None:
        _left_sidebar_instance = LeftSidebarManager()
        logger.info("Left Sidebar Manager singleton created")
    return _left_sidebar_instance
