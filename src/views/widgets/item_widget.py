"""
Item Button Widget
"""
from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont
import sys
import webbrowser
import os
import subprocess
import platform
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from models.item import Item, ItemType
from core.usage_tracker import UsageTracker
from core.favorites_manager import FavoritesManager
from core.file_manager import FileManager
from core.config_manager import ConfigManager
from views.command_output_dialog import CommandOutputDialog
from views.dialogs.item_details_dialog import ItemDetailsDialog
from styles.panel_styles import PanelStyles
import time
import logging

logger = logging.getLogger(__name__)


class ItemButton(QFrame):
    """Custom item button widget for content panel with tags support"""

    # Signals
    item_clicked = pyqtSignal(object)
    favorite_toggled = pyqtSignal(int, bool)  # item_id, is_favorite (deprecated - kept for compatibility)
    archived_toggled = pyqtSignal(int, bool)  # item_id, is_archived (deprecated - kept for compatibility)
    url_open_requested = pyqtSignal(str)  # url to open in embedded browser
    table_view_requested = pyqtSignal(str)  # table_name to view complete table
    web_static_render_requested = pyqtSignal(object)  # item to render as WEB_STATIC

    def __init__(self, item: Item, show_category: bool = False, show_labels: bool = True, show_tags: bool = False, show_content: bool = False, show_description: bool = False, parent=None):
        super().__init__(parent)
        self.item = item
        self.show_category = show_category  # Show category badge in global search
        self.show_labels = show_labels  # Show labels (default: True)
        self.show_tags = show_tags  # Show tags (default: False)
        self.show_content = show_content  # Show content preview (default: False)
        self.show_description = show_description  # Show description (default: False)
        self.is_copied = False
        self.is_revealed = False  # Track if sensitive content is revealed
        self.reveal_timer = None  # Timer for auto-hide
        self.clipboard_clear_timer = None  # Timer for clipboard clearing

        # Usage tracking
        self.usage_tracker = UsageTracker()
        self.execution_start_time = None

        # Favorites management
        self.favorites_manager = FavoritesManager()

        self.init_ui()

    def _resolve_path(self, content_path: str) -> Path:
        """
        Resuelve una ruta, convirtiendo rutas relativas a absolutas si es necesario

        Args:
            content_path: Ruta desde item.content (puede ser relativa o absoluta)

        Returns:
            Path: Ruta absoluta resuelta
        """
        path = Path(content_path)

        # Si la ruta es absoluta y existe, usarla directamente
        if path.is_absolute():
            return path

        # Si es relativa, intentar construir ruta absoluta desde config
        # Formato relativo: "IMAGENES/test.jpg" o "IMAGENES\test.jpg"
        try:
            # Intentar obtener FileManager para construir ruta absoluta
            db_path = Path(__file__).parent.parent.parent.parent / "widget_sidebar.db"
            config_manager = ConfigManager(str(db_path))
            file_manager = FileManager(config_manager)

            # Convertir ruta relativa a absoluta
            absolute_path = file_manager.get_absolute_path(content_path)
            config_manager.close()

            return Path(absolute_path)

        except Exception as e:
            logger.warning(f"Could not resolve relative path '{content_path}': {e}")
            # Fallback: asumir que es ruta absoluta
            return path

    def init_ui(self):
        """Initialize button UI with new optimized design"""
        # Set frame properties with new dimensions
        self.setFixedHeight(PanelStyles.ITEM_HEIGHT)
        self.setMinimumWidth(300)  # Keep min width for horizontal scroll
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed  # Fixed height instead of expanding
        )

        # Apply new item style
        self.setStyleSheet(PanelStyles.get_item_style())

        # Set tooltip - show content preview
        if not self.item.is_sensitive and self.item.content:
            content_preview = self.item.content[:100]  # Reduced to 100 chars
            if len(self.item.content) > 100:
                content_preview += "..."
            # Include type and description in tooltip
            tooltip_parts = []
            if self.item.description:
                tooltip_parts.append(f"{self.item.description}")
            tooltip_parts.append(f"\n{content_preview}")
            tooltip_parts.append(f"\nTipo: {self.item.type}")
            self.setToolTip("\n".join(tooltip_parts))
        else:
            self.setToolTip(self.item.label)

        # Main layout - optimized spacing
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(
            PanelStyles.ITEM_PADDING_H,
            PanelStyles.ITEM_PADDING_V,
            PanelStyles.ITEM_PADDING_H,
            PanelStyles.ITEM_PADDING_V
        )
        main_layout.setSpacing(PanelStyles.ICON_SPACING)

        # ==== NEW OPTIMIZED HORIZONTAL LAYOUT ====

        # 1. Type Icon (14px, with 4px spacing)
        type_emoji = PanelStyles.get_icon_type_emoji(self.item.type)
        type_color = PanelStyles.get_icon_type_color(self.item.type)
        self.type_icon = QLabel(type_emoji)
        self.type_icon.setFixedSize(PanelStyles.ICON_SIZE, PanelStyles.ICON_SIZE)
        self.type_icon.setStyleSheet(f"""
            QLabel {{
                color: {type_color};
                font-size: {PanelStyles.ICON_SIZE}px;
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """)
        self.type_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.type_icon.setToolTip(f"Tipo: {self.item.type}")
        main_layout.addWidget(self.type_icon)

        # 2. Item Label/Tags/Content (expandable, elided if too long)
        display_text = self.get_display_text()
        self.label_widget = QLabel(display_text)
        self.label_widget.setStyleSheet(PanelStyles.get_item_label_style())
        # Enable text eliding for long labels
        self.label_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        self.label_widget.setWordWrap(False)  # No wrap, use eliding
        self.label_widget.setTextFormat(Qt.TextFormat.PlainText)
        main_layout.addWidget(self.label_widget, 1)  # Stretch factor 1

        # 3. Badges (compact, inline) - Use new PanelStyles
        # Favorite badge
        if hasattr(self.item, 'is_favorite') and self.item.is_favorite:
            fav_badge = QLabel("⭐")
            fav_badge.setStyleSheet(PanelStyles.get_badge_style('favorite'))
            fav_badge.setToolTip("Favorito")
            main_layout.addWidget(fav_badge)

        # Popular badge (if use_count > 50)
        if hasattr(self.item, 'use_count') and self.item.use_count and self.item.use_count > 50:
            pop_badge = QLabel("🔥")
            pop_badge.setStyleSheet(PanelStyles.get_badge_style('popular'))
            pop_badge.setToolTip(f"Popular ({self.item.use_count} usos)")
            main_layout.addWidget(pop_badge)

        # New badge (if use_count == 0)
        if hasattr(self.item, 'use_count') and self.item.use_count == 0:
            new_badge = QLabel("🆕")
            new_badge.setStyleSheet(PanelStyles.get_badge_style('new'))
            new_badge.setToolTip("Nuevo")
            main_layout.addWidget(new_badge)

        # Category badge (for global search)
        if self.show_category and hasattr(self.item, 'category_name') and self.item.category_name:
            category_badge = QLabel(f"📁 {self.item.category_name}")
            category_badge.setStyleSheet(PanelStyles.get_badge_style('default'))
            category_badge.setToolTip(f"Categoría: {self.item.category_name}")
            main_layout.addWidget(category_badge)

        # File badge (for PATH items with saved files)
        if (self.item.type == ItemType.PATH and
            hasattr(self.item, 'file_hash') and self.item.file_hash):
            file_badge = QLabel("📦")
            file_badge.setStyleSheet(PanelStyles.get_badge_style('default'))
            file_badge.setToolTip("Archivo guardado en almacenamiento organizado")
            main_layout.addWidget(file_badge)

        # Table badge (for table items)
        if hasattr(self.item, 'table_id') and self.item.table_id:
            table_badge = QLabel("📊")
            table_badge.setStyleSheet(PanelStyles.get_badge_style('default'))
            table_badge.setToolTip(f"Item de tabla (ID: {self.item.table_id})")
            main_layout.addWidget(table_badge)

        # Spacer to push action buttons to the right
        main_layout.addStretch()

        # ==== ACTION BUTTONS (compact 28x28px) ====
        if self.item.type == ItemType.CODE:
            # Execute command button (only for CODE items)
            self.execute_button = QPushButton("⚡")
            self.execute_button.setFixedSize(28, 28)
            self.execute_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PanelStyles.ACCENT_WARNING};
                    color: #000000;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {PanelStyles.ACCENT_HOVER};
                    color: #ffffff;
                }}
                QPushButton:pressed {{
                    background-color: {PanelStyles.ACCENT_SUBTLE};
                }}
            """)
            self.execute_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.execute_button.setToolTip("Ejecutar comando")
            self.execute_button.clicked.connect(self.execute_command)
            main_layout.addWidget(self.execute_button)

        elif self.item.type == 'WEB_STATIC' or self.item.type == ItemType.WEB_STATIC:
            # Render button (only for WEB_STATIC items) - FIRST FOR VISIBILITY
            self.render_button = QPushButton("📱")  # Cambiado de 🌐 a 📱 para diferenciarlo de URL
            self.render_button.setFixedSize(28, 28)
            self.render_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #388E3C;
                }
            """)
            self.render_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.render_button.setToolTip("Renderizar aplicación web estática")
            self.render_button.clicked.connect(self.render_web_static)
            main_layout.addWidget(self.render_button)

        elif self.item.type == ItemType.URL:
            # URL action buttons - two buttons layout
            url_buttons_layout = QHBoxLayout()
            url_buttons_layout.setSpacing(4)

            # Open in embedded browser button
            self.open_url_button = QPushButton("🌐")
            self.open_url_button.setFixedSize(28, 28)
            self.open_url_button.setStyleSheet("""
                QPushButton {
                    background-color: #007acc;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #005a9e;
                }
                QPushButton:pressed {
                    background-color: #004578;
                }
            """)
            self.open_url_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.open_url_button.setToolTip("Abrir en navegador embebido")
            self.open_url_button.clicked.connect(self.open_in_browser)
            url_buttons_layout.addWidget(self.open_url_button)

            # Open in system browser button (NEW)
            self.open_external_button = QPushButton("🔗")
            self.open_external_button.setFixedSize(28, 28)
            self.open_external_button.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            """)
            self.open_external_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.open_external_button.setToolTip("Abrir en navegador predeterminado del sistema")
            self.open_external_button.clicked.connect(self.open_in_system_browser)
            url_buttons_layout.addWidget(self.open_external_button)

            main_layout.addLayout(url_buttons_layout)

        elif self.item.type == ItemType.PATH:
            # PATH action buttons
            path_buttons_layout = QHBoxLayout()
            path_buttons_layout.setSpacing(4)

            # Open in explorer button
            self.open_explorer_button = QPushButton("📁")
            self.open_explorer_button.setFixedSize(28, 28)
            self.open_explorer_button.setStyleSheet("""
                QPushButton {
                    background-color: #2d7d2d;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #236123;
                }
                QPushButton:pressed {
                    background-color: #1a4a1a;
                }
            """)
            self.open_explorer_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.open_explorer_button.setToolTip("Abrir en explorador")
            self.open_explorer_button.clicked.connect(self.open_in_explorer)
            path_buttons_layout.addWidget(self.open_explorer_button)

            # Open file button (only if it's a file, not a directory)
            # Resolver ruta (relativa -> absoluta si es necesario)
            path = self._resolve_path(self.item.content)
            if path.exists() and path.is_file():
                self.open_file_button = QPushButton("📝")
                self.open_file_button.setFixedSize(28, 28)
                self.open_file_button.setStyleSheet("""
                    QPushButton {
                        background-color: #cc7a00;
                        color: #ffffff;
                        border: none;
                        border-radius: 3px;
                        font-size: 12pt;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #9e5e00;
                    }
                    QPushButton:pressed {
                        background-color: #784500;
                    }
                """)
                self.open_file_button.setCursor(Qt.CursorShape.PointingHandCursor)
                self.open_file_button.setToolTip("Abrir archivo")
                self.open_file_button.clicked.connect(self.open_file)
                path_buttons_layout.addWidget(self.open_file_button)

            main_layout.addLayout(path_buttons_layout)

        # Common buttons (for all item types)

        # View table button (for table items)
        if hasattr(self.item, 'table_id') and self.item.table_id:
            self.view_table_btn = QPushButton("🗂️")
            self.view_table_btn.setFixedSize(28, 28)
            self.view_table_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.view_table_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007acc;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #005a9e;
                }
                QPushButton:pressed {
                    background-color: #004578;
                }
            """)
            self.view_table_btn.setToolTip(f"Ver tabla completa")
            self.view_table_btn.clicked.connect(self.view_table)
            main_layout.addWidget(self.view_table_btn)

        # Reveal button for sensitive items
        if hasattr(self.item, 'is_sensitive') and self.item.is_sensitive:
            self.reveal_button = QPushButton("👁")
            self.reveal_button.setFixedSize(28, 28)
            self.reveal_button.setStyleSheet("""
                QPushButton {
                    background-color: #cc0000;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #9e0000;
                }
                QPushButton:pressed {
                    background-color: #780000;
                }
            """)
            self.reveal_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.reveal_button.setToolTip("Revelar/Ocultar contenido sensible")
            self.reveal_button.clicked.connect(self.toggle_reveal)
            main_layout.addWidget(self.reveal_button)

        # Info button (show details) - ALWAYS LAST
        self.info_btn = QPushButton("ℹ️")
        self.info_btn.setFixedSize(28, 28)
        self.info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.info_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 12pt;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #3e3e42;
                border-radius: 3px;
            }
        """)
        self.info_btn.setToolTip("Ver detalles del item")
        self.info_btn.clicked.connect(self.show_details)
        main_layout.addWidget(self.info_btn)

        # Set initial style (different for sensitive items and file items)
        if hasattr(self.item, 'is_sensitive') and self.item.is_sensitive:
            self.setStyleSheet("""
                QFrame {
                    background-color: #3d2020;
                    border: none;
                    border-left: 3px solid #cc0000;
                    border-bottom: 1px solid #1e1e1e;
                }
                QFrame:hover {
                    background-color: #4d2525;
                }
                QLabel {
                    color: #cccccc;
                    background-color: transparent;
                    border: none;
                }
            """)
        elif (self.item.type == ItemType.PATH and
              hasattr(self.item, 'file_hash') and self.item.file_hash):
            # Special style for PATH items with saved files
            self.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: none;
                    border-left: 3px solid #4CAF50;
                    border-bottom: 1px solid #1e1e1e;
                }
                QFrame:hover {
                    background-color: #3d3d3d;
                }
                QLabel {
                    color: #cccccc;
                    background-color: transparent;
                    border: none;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: none;
                    border-bottom: 1px solid #1e1e1e;
                }
                QFrame:hover {
                    background-color: #3d3d3d;
                }
                QLabel {
                    color: #cccccc;
                    background-color: transparent;
                    border: none;
                }
            """)

    def mousePressEvent(self, event):
        """Handle mouse press event"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_clicked()
        super().mousePressEvent(event)

    def on_clicked(self):
        """Handle button click"""
        # Track clipboard copy (comando simple)
        if self.item.type not in [ItemType.URL, ItemType.PATH]:
            start_time = self.usage_tracker.track_execution_start(self.item.id)

        # Emit signal with item
        self.item_clicked.emit(self.item)

        # Show copied feedback
        self.show_copied_feedback()

        # Track completion for clipboard copy
        if self.item.type not in [ItemType.URL, ItemType.PATH]:
            self.usage_tracker.track_execution_end(self.item.id, start_time, True, None)

        # If sensitive item, start clipboard auto-clear timer
        if hasattr(self.item, 'is_sensitive') and self.item.is_sensitive:
            self.start_clipboard_clear_timer()

    def open_in_browser(self):
        """Open URL in embedded browser"""
        if self.item.type == ItemType.URL:
            # Track execution start
            start_time = self.usage_tracker.track_execution_start(self.item.id)
            success = False
            error_msg = None

            try:
                url = self.item.content
                # Ensure URL has proper protocol
                if not url.startswith(('http://', 'https://')):
                    if url.startswith('www.'):
                        url = 'https://' + url
                    else:
                        url = 'https://' + url

                # Emit signal to open in embedded browser
                self.url_open_requested.emit(url)
                success = True
                logger.info(f"URL open requested in embedded browser: {url}")

                # Update button style briefly to show it was clicked
                original_style = self.open_url_button.styleSheet()
                self.open_url_button.setStyleSheet("""
                    QPushButton {
                        background-color: #00ff00;
                        color: #ffffff;
                        border: none;
                        border-radius: 3px;
                        font-size: 12pt;
                        padding: 0px;
                    }
                """)
                QTimer.singleShot(300, lambda: self.open_url_button.setStyleSheet(original_style))

            except Exception as e:
                logger.error(f"Error opening URL {self.item.label}: {e}")
                error_msg = str(e)

            finally:
                # Track execution end
                self.usage_tracker.track_execution_end(self.item.id, start_time, success, error_msg)

    def open_in_system_browser(self):
        """Open URL in system default browser (Chrome, Firefox, Edge, etc.)"""
        if self.item.type == ItemType.URL:
            # Track execution start
            start_time = self.usage_tracker.track_execution_start(self.item.id)
            success = False
            error_msg = None

            try:
                url = self.item.content
                # Ensure URL has proper protocol
                if not url.startswith(('http://', 'https://')):
                    if url.startswith('www.'):
                        url = 'https://' + url
                    else:
                        url = 'https://' + url

                # Open in system default browser
                webbrowser.open(url)
                success = True
                logger.info(f"URL opened in system browser: {url}")

                # Update button style briefly to show it was clicked
                original_style = self.open_external_button.styleSheet()
                self.open_external_button.setStyleSheet("""
                    QPushButton {
                        background-color: #00ff00;
                        color: #ffffff;
                        border: none;
                        border-radius: 3px;
                        font-size: 12pt;
                        padding: 0px;
                    }
                """)
                QTimer.singleShot(300, lambda: self.open_external_button.setStyleSheet(original_style))

            except Exception as e:
                logger.error(f"Error opening URL in system browser {self.item.label}: {e}")
                error_msg = str(e)

            finally:
                # Track execution end
                self.usage_tracker.track_execution_end(self.item.id, start_time, success, error_msg)

    def open_in_explorer(self):
        """Open file/folder in system file explorer"""
        if self.item.type == ItemType.PATH:
            # Track execution start
            start_time = self.usage_tracker.track_execution_start(self.item.id)
            success = False
            error_msg = None

            try:
                # Resolver ruta (relativa -> absoluta si es necesario)
                path = self._resolve_path(self.item.content)
                system = platform.system()

                if system == 'Windows':
                    # Windows: Use explorer with /select to highlight the file/folder
                    if path.exists():
                        subprocess.run(['explorer', '/select,', str(path.absolute())])
                    else:
                        # If path doesn't exist, try to open parent directory
                        parent = path.parent
                        if parent.exists():
                            subprocess.run(['explorer', str(parent.absolute())])

                elif system == 'Darwin':  # macOS
                    if path.exists():
                        subprocess.run(['open', '-R', str(path.absolute())])
                    else:
                        parent = path.parent
                        if parent.exists():
                            subprocess.run(['open', str(parent.absolute())])

                else:  # Linux
                    if path.exists():
                        if path.is_file():
                            subprocess.run(['xdg-open', str(path.parent.absolute())])
                        else:
                            subprocess.run(['xdg-open', str(path.absolute())])
                    else:
                        parent = path.parent
                        if parent.exists():
                            subprocess.run(['xdg-open', str(parent.absolute())])

                success = True

                # Visual feedback
                original_style = self.open_explorer_button.styleSheet()
                self.open_explorer_button.setStyleSheet("""
                    QPushButton {
                        background-color: #00ff00;
                        color: #ffffff;
                        border: none;
                        border-radius: 3px;
                        font-size: 12pt;
                        padding: 0px;
                    }
                """)
                QTimer.singleShot(300, lambda: self.open_explorer_button.setStyleSheet(original_style))

            except Exception as e:
                logger.error(f"Error opening explorer for {self.item.label}: {e}")
                error_msg = str(e)

            finally:
                # Track execution end
                self.usage_tracker.track_execution_end(self.item.id, start_time, success, error_msg)

    def open_file(self):
        """Open file with default application"""
        if self.item.type == ItemType.PATH:
            # Resolver ruta (relativa -> absoluta si es necesario)
            path = self._resolve_path(self.item.content)

            if not path.exists() or not path.is_file():
                logger.warning(f"File not found: {path}")
                return

            try:
                system = platform.system()

                if system == 'Windows':
                    # Windows: Use os.startfile
                    os.startfile(str(path.absolute()))

                elif system == 'Darwin':  # macOS
                    subprocess.run(['open', str(path.absolute())])

                else:  # Linux
                    subprocess.run(['xdg-open', str(path.absolute())])

                # Visual feedback
                original_style = self.open_file_button.styleSheet()
                self.open_file_button.setStyleSheet("""
                    QPushButton {
                        background-color: #00ff00;
                        color: #ffffff;
                        border: none;
                        border-radius: 3px;
                        font-size: 12pt;
                        padding: 0px;
                    }
                """)
                QTimer.singleShot(300, lambda: self.open_file_button.setStyleSheet(original_style))

            except Exception as e:
                print(f"Error opening file: {e}")

    def show_copied_feedback(self):
        """Show visual feedback that item was copied"""
        self.is_copied = True

        # Different style for sensitive items (orange/warning color)
        if hasattr(self.item, 'is_sensitive') and self.item.is_sensitive:
            self.setStyleSheet("""
                QFrame {
                    background-color: #cc7a00;
                    border: none;
                    border-bottom: 1px solid #9e5e00;
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                    border: none;
                    font-weight: bold;
                }
            """)
        else:
            # Normal items: blue feedback
            self.setStyleSheet("""
                QFrame {
                    background-color: #007acc;
                    border: none;
                    border-bottom: 1px solid #005a9e;
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                    border: none;
                    font-weight: bold;
                }
            """)

        # Reset after 500ms
        QTimer.singleShot(500, self.reset_style)

    def reset_style(self):
        """Reset button style to normal"""
        self.is_copied = False
        # Apply special style for sensitive items
        if hasattr(self.item, 'is_sensitive') and self.item.is_sensitive:
            self.setStyleSheet("""
                QFrame {
                    background-color: #3d2020;
                    border: none;
                    border-left: 3px solid #cc0000;
                    border-bottom: 1px solid #1e1e1e;
                }
                QFrame:hover {
                    background-color: #4d2525;
                }
                QLabel {
                    color: #cccccc;
                    background-color: transparent;
                    border: none;
                }
            """)
        elif (self.item.type == ItemType.PATH and
              hasattr(self.item, 'file_hash') and self.item.file_hash):
            # Special style for PATH items with saved files
            self.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: none;
                    border-left: 3px solid #4CAF50;
                    border-bottom: 1px solid #1e1e1e;
                }
                QFrame:hover {
                    background-color: #3d3d3d;
                }
                QLabel {
                    color: #cccccc;
                    background-color: transparent;
                    border: none;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: none;
                    border-bottom: 1px solid #1e1e1e;
                }
                QFrame:hover {
                    background-color: #3d3d3d;
                }
                QLabel {
                    color: #cccccc;
                    background-color: transparent;
                    border: none;
                }
            """)

    def get_display_text(self):
        """Get display text based on selected display options (labels/tags/content/description)"""
        MAX_CONTENT_LENGTH = 100  # Max characters for content preview
        MAX_DESCRIPTION_LENGTH = 80  # Max characters for description

        display_parts = []

        # Get file type icon if this is a PATH item with file metadata
        file_icon = ""
        if (self.item.type == ItemType.PATH and
            hasattr(self.item, 'file_hash') and self.item.file_hash and
            hasattr(self.item, 'get_file_type_icon')):
            file_icon = self.item.get_file_type_icon() + " "

        # 1. Show Labels (if enabled)
        if self.show_labels:
            display_parts.append(f"{file_icon}{self.item.label}")

        # 2. Show Description (if enabled and item has description)
        if self.show_description and hasattr(self.item, 'description') and self.item.description:
            description = self.item.description[:MAX_DESCRIPTION_LENGTH]
            if len(self.item.description) > MAX_DESCRIPTION_LENGTH:
                description += "..."
            display_parts.append(f"📝 {description}")

        # 3. Show Tags (if enabled and item has tags)
        if self.show_tags and hasattr(self.item, 'tags') and self.item.tags:
            if isinstance(self.item.tags, list):
                tags_text = ", ".join(self.item.tags)
            else:
                tags_text = str(self.item.tags)
            display_parts.append(f"🏷️ {tags_text}")

        # 4. Show Content (if enabled)
        if self.show_content:
            # Handle sensitive content
            if hasattr(self.item, 'is_sensitive') and self.item.is_sensitive and not self.is_revealed:
                # Obfuscate sensitive content
                display_parts.append("🔒 ********")
            elif hasattr(self.item, 'is_sensitive') and self.item.is_sensitive and self.is_revealed:
                # Show revealed sensitive content (truncated)
                content = self.item.content[:MAX_CONTENT_LENGTH]
                if len(self.item.content) > MAX_CONTENT_LENGTH:
                    content += "..."
                display_parts.append(f"🔓 {content}")
            else:
                # Show normal content (truncated)
                if self.item.content:
                    content = self.item.content[:MAX_CONTENT_LENGTH]
                    if len(self.item.content) > MAX_CONTENT_LENGTH:
                        content += "..."
                    display_parts.append(f"📄 {content}")

        # Join all parts with separator
        if display_parts:
            return " | ".join(display_parts)
        else:
            # Fallback: show at least the label
            return f"{file_icon}{self.item.label}"

    def get_display_label(self):
        """Get display label (ofuscado si es sensible y no revelado) - DEPRECATED, use get_display_text()"""
        # Get file type icon if this is a PATH item with file metadata
        file_icon = ""
        if (self.item.type == ItemType.PATH and
            hasattr(self.item, 'file_hash') and self.item.file_hash and
            hasattr(self.item, 'get_file_type_icon')):
            file_icon = self.item.get_file_type_icon() + " "

        if hasattr(self.item, 'is_sensitive') and self.item.is_sensitive and not self.is_revealed:
            # Ofuscar: mostrar label + (********)
            content_preview = "********"
            return f"{file_icon}{self.item.label} ({content_preview})"
        elif hasattr(self.item, 'is_sensitive') and self.item.is_sensitive and self.is_revealed:
            # Revelado: mostrar label + preview del contenido
            content = self.item.content[:30] if len(self.item.content) > 30 else self.item.content
            return f"{file_icon}{self.item.label} ({content}...)" if len(self.item.content) > 30 else f"{file_icon}{self.item.label} ({content})"
        else:
            # Item normal: solo el label (con icono de archivo si aplica)
            return f"{file_icon}{self.item.label}"

    def toggle_reveal(self):
        """Toggle reveal/hide sensitive content"""
        self.is_revealed = not self.is_revealed

        # Update label with new display text
        self.label_widget.setText(self.get_display_text())

        if self.is_revealed:
            # Cambiar icono del boton
            self.reveal_button.setText("🙈")
            self.reveal_button.setToolTip("Ocultar contenido sensible")

            # Cancelar timer anterior si existe
            if self.reveal_timer:
                self.reveal_timer.stop()

            # Auto-ocultar despues de 10 segundos
            self.reveal_timer = QTimer()
            self.reveal_timer.setSingleShot(True)
            self.reveal_timer.timeout.connect(self.auto_hide)
            self.reveal_timer.start(10000)  # 10 segundos
        else:
            # Cambiar icono del boton
            self.reveal_button.setText("👁")
            self.reveal_button.setToolTip("Revelar/Ocultar contenido sensible")

            # Cancelar timer si existe
            if self.reveal_timer:
                self.reveal_timer.stop()

    def auto_hide(self):
        """Auto-hide sensitive content after timeout"""
        if self.is_revealed:
            self.toggle_reveal()

    def start_clipboard_clear_timer(self):
        """Start timer to clear clipboard after 30 seconds for sensitive items"""
        # Cancel previous timer if exists
        if self.clipboard_clear_timer:
            self.clipboard_clear_timer.stop()

        # Start 30-second timer
        self.clipboard_clear_timer = QTimer()
        self.clipboard_clear_timer.setSingleShot(True)
        self.clipboard_clear_timer.timeout.connect(self.clear_clipboard)
        self.clipboard_clear_timer.start(30000)  # 30 seconds

    def clear_clipboard(self):
        """Clear clipboard content"""
        try:
            import pyperclip
            pyperclip.copy("")  # Clear clipboard
        except Exception as e:
            print(f"Error clearing clipboard: {e}")

    def update_favorite_button(self):
        """Actualizar icono del botón de favorito"""
        is_fav = self.favorites_manager.is_favorite(self.item.id)

        if is_fav:
            self.favorite_btn.setText("⭐")
            self.favorite_btn.setToolTip("Quitar de favoritos")
        else:
            self.favorite_btn.setText("☆")
            self.favorite_btn.setToolTip("Marcar como favorito")

    def toggle_favorite(self):
        """Alternar estado de favorito"""
        try:
            is_fav = self.favorites_manager.toggle_favorite(self.item.id)

            # Actualizar botón
            self.update_favorite_button()

            # Emitir señal
            self.favorite_toggled.emit(self.item.id, is_fav)

            # Log
            msg = "agregado a" if is_fav else "quitado de"
            logger.info(f"Item '{self.item.label}' {msg} favoritos")

        except Exception as e:
            logger.error(f"Error toggling favorite for item {self.item.id}: {e}")

    def get_badge(self) -> str:
        """Obtener badge del item (🔥 Popular)"""
        use_count = getattr(self.item, 'use_count', 0)

        # Popular: más de 50 usos
        if use_count > 50:
            return "🔥"

        # Badge "Nuevo" deshabilitado
        return ""

    def get_usage_stats(self) -> str:
        """Obtener estadísticas de uso (use_count + last_used)"""
        use_count = getattr(self.item, 'use_count', 0)
        last_used = getattr(self.item, 'last_used', None)

        parts = []

        # Use count
        if use_count > 0:
            parts.append(f"{use_count} usos")
        else:
            parts.append("Sin usar")

        # Last used
        if last_used:
            from datetime import datetime
            try:
                # Parse SQLite datetime format: YYYY-MM-DD HH:MM:SS
                # Si ya es datetime, usarlo directamente
                if isinstance(last_used, datetime):
                    last_used_dt = last_used
                else:
                    last_used_dt = datetime.strptime(str(last_used), "%Y-%m-%d %H:%M:%S")

                now = datetime.now()
                diff = now - last_used_dt

                # Format relative time
                if diff.days == 0:
                    if diff.seconds < 60:
                        time_str = "hace unos segundos"
                    elif diff.seconds < 3600:
                        minutes = diff.seconds // 60
                        time_str = f"hace {minutes} min"
                    else:
                        hours = diff.seconds // 3600
                        time_str = f"hace {hours}h"
                elif diff.days == 1:
                    time_str = "ayer"
                elif diff.days < 7:
                    time_str = f"hace {diff.days} días"
                elif diff.days < 30:
                    weeks = diff.days // 7
                    time_str = f"hace {weeks} semanas"
                else:
                    months = diff.days // 30
                    time_str = f"hace {months} meses"

                parts.append(f"último: {time_str}")
            except Exception as e:
                logger.debug(f"Error parsing last_used date: {e}")

        return " | ".join(parts) if parts else ""

    def show_details(self):
        """Mostrar ventana de detalles del item"""
        try:
            # Find the FloatingPanel or GlobalSearchPanel parent to pass to dialog
            refresh_panel = None
            parent_widget = self.parent()
            while parent_widget:
                class_name = parent_widget.__class__.__name__
                if class_name in ('FloatingPanel', 'GlobalSearchPanel', 'FavoritesFloatingPanel'):
                    refresh_panel = parent_widget
                    break
                parent_widget = parent_widget.parent()

            dialog = ItemDetailsDialog(self.item, floating_panel=refresh_panel, parent=self.window())
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing item details: {e}")

    def view_table(self):
        """Emite señal para ver la tabla completa"""
        if not hasattr(self.item, 'table_id') or not self.item.table_id:
            return

        # Get table name from database
        from src.database.db_manager import DBManager
        db = DBManager()
        table = db.get_table(self.item.table_id)

        if not table:
            logger.warning(f"Table not found for table_id: {self.item.table_id}")
            return

        table_name = table['name']

        # Emitir señal para que el FloatingPanel maneje la apertura del diálogo
        self.table_view_requested.emit(table_name)
        logger.info(f"Table view requested: {table_name}")

    def execute_command(self):
        """Ejecutar comando de tipo CODE"""
        if self.item.type != ItemType.CODE:
            return

        # Track execution start
        start_time = self.usage_tracker.track_execution_start(self.item.id)
        success = False
        error_msg = None

        try:
            command = self.item.content.strip()

            # Visual feedback - cambiar botón a amarillo mientras ejecuta
            original_style = self.execute_button.styleSheet()
            self.execute_button.setStyleSheet("""
                QPushButton {
                    background-color: #ffff00;
                    color: #000000;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
            """)
            self.execute_button.setText("⏳")

            # Ejecutar comando usando subprocess
            # En Windows, necesitamos usar shell=True para comandos como 'dir', 'git', etc.
            system = platform.system()

            # Determinar directorio de trabajo
            cwd = None
            if hasattr(self.item, 'working_dir') and self.item.working_dir:
                from pathlib import Path
                working_dir_path = Path(self.item.working_dir)
                if working_dir_path.exists() and working_dir_path.is_dir():
                    cwd = str(working_dir_path.absolute())
                    logger.info(f"Executing command in working directory: {cwd}")
                else:
                    logger.warning(f"Working directory does not exist: {self.item.working_dir}")

            if system == 'Windows':
                # En Windows, usar cmd.exe para ejecutar el comando
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,  # Timeout de 30 segundos
                    cwd=cwd  # Directorio de trabajo
                )
            else:
                # En Unix-like systems, usar bash
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    executable='/bin/bash',
                    cwd=cwd  # Directorio de trabajo
                )

            # Obtener output y error
            stdout = result.stdout if result.stdout else ""
            stderr = result.stderr if result.stderr else ""
            return_code = result.returncode

            # Considerar éxito si return code es 0
            success = (return_code == 0)

            # Restaurar botón
            self.execute_button.setText("⚡")
            if success:
                # Verde si éxito
                self.execute_button.setStyleSheet("""
                    QPushButton {
                        background-color: #00ff00;
                        color: #000000;
                        border: none;
                        border-radius: 3px;
                        font-size: 12pt;
                        padding: 0px;
                    }
                """)
            else:
                # Rojo si error
                self.execute_button.setStyleSheet("""
                    QPushButton {
                        background-color: #ff0000;
                        color: #ffffff;
                        border: none;
                        border-radius: 3px;
                        font-size: 12pt;
                        padding: 0px;
                    }
                """)
                error_msg = stderr if stderr else "Error desconocido"

            # Restaurar estilo original después de 1 segundo
            QTimer.singleShot(1000, lambda: self.execute_button.setStyleSheet(original_style))

            # Mostrar dialog con el resultado
            dialog = CommandOutputDialog(
                command=command,
                output=stdout,
                error=stderr,
                return_code=return_code,
                parent=self.window()
            )
            dialog.exec()

        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {self.item.label}")
            error_msg = "Comando excedió el tiempo de espera (30 segundos)"

            # Restaurar botón con estilo de error
            self.execute_button.setText("⚡")
            self.execute_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff0000;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
            """)
            QTimer.singleShot(1000, lambda: self.execute_button.setStyleSheet(original_style))

            # Mostrar dialog de error
            dialog = CommandOutputDialog(
                command=command,
                output="",
                error=error_msg,
                return_code=-1,
                parent=self.window()
            )
            dialog.exec()

        except Exception as e:
            logger.error(f"Error executing command {self.item.label}: {e}")
            error_msg = str(e)

            # Restaurar botón con estilo de error
            self.execute_button.setText("⚡")
            self.execute_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff0000;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
            """)
            QTimer.singleShot(1000, lambda: self.execute_button.setStyleSheet(original_style))

            # Mostrar dialog de error
            dialog = CommandOutputDialog(
                command=command if 'command' in locals() else self.item.content,
                output="",
                error=error_msg,
                return_code=-1,
                parent=self.window()
            )
            dialog.exec()

        finally:
            # Track execution end
            self.usage_tracker.track_execution_end(self.item.id, start_time, success, error_msg)

    def render_web_static(self):
        """Renderiza item WEB_STATIC en navegador embebido seguro"""
        if self.item.type != 'WEB_STATIC' and self.item.type != ItemType.WEB_STATIC:
            return

        # Track execution start
        start_time = self.usage_tracker.track_execution_start(self.item.id)
        success = False
        error_msg = None

        try:
            # Visual feedback - cambiar botón mientras abre
            original_style = self.render_button.styleSheet()
            self.render_button.setStyleSheet("""
                QPushButton {
                    background-color: #00d4ff;
                    color: #000000;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
            """)

            # Emitir señal con el item completo
            self.web_static_render_requested.emit(self.item)
            success = True

            logger.info(f"WEB_STATIC render requested for item: {self.item.label}")

            # Restaurar estilo después de 300ms
            QTimer.singleShot(300, lambda: self.render_button.setStyleSheet(original_style))

        except Exception as e:
            logger.error(f"Error rendering WEB_STATIC item {self.item.label}: {e}")
            error_msg = str(e)

            # Restaurar estilo con color de error
            self.render_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: #ffffff;
                    border: none;
                    border-radius: 3px;
                    font-size: 12pt;
                    padding: 0px;
                }
            """)
            QTimer.singleShot(1000, lambda: self.render_button.setStyleSheet(original_style))

        finally:
            # Track execution end
            self.usage_tracker.track_execution_end(self.item.id, start_time, success, error_msg)
