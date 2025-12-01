"""
Panel Styles - Estilos centralizados para paneles flotantes
Proporciona una paleta de colores sofisticada y dimensiones optimizadas
para los paneles de Categoría, Búsqueda Global y Proceso
"""
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtWidgets import QWidget


class PanelStyles:
    """Estilos centralizados para todos los paneles flotantes"""

    # ==================== PALETA DE COLORES ====================

    # Fondos
    BACKGROUND_PRIMARY = '#1a1d23'      # Fondo principal (gris oscuro profundo)
    BACKGROUND_SECONDARY = '#22252b'    # Fondo secundario (gris medio oscuro)
    BACKGROUND_HOVER = '#2a2d35'        # Fondo hover sutil
    BACKGROUND_ACTIVE = '#2f3339'       # Fondo item activo

    # Bordes
    BORDER_PRIMARY = '#2f3339'          # Bordes principales
    BORDER_SECONDARY = '#3d4149'        # Bordes secundarios
    BORDER_RESIZE = '#5b9dd9'           # Indicador de redimensión

    # Textos
    TEXT_PRIMARY = '#e4e6eb'            # Texto principal (blanco suave)
    TEXT_SECONDARY = '#8b8d94'          # Texto secundario (gris)
    TEXT_MUTED = '#6b6d74'              # Texto deshabilitado

    # Acentos
    ACCENT_PRIMARY = '#5b9dd9'          # Azul sereno (principal)
    ACCENT_HOVER = '#6eb3e8'            # Azul hover
    ACCENT_SUBTLE = '#3d5a75'           # Azul oscuro (fondo sutil)
    ACCENT_SUCCESS = '#4ea961'          # Verde suave (éxito/activo)
    ACCENT_WARNING = '#d9a05b'          # Naranja sutil (advertencia)

    # Scrollbar
    SCROLLBAR_TRACK = '#1a1d23'         # Fondo scrollbar
    SCROLLBAR_THUMB = '#3d4149'         # Thumb scrollbar
    SCROLLBAR_THUMB_HOVER = '#5b9dd9'   # Thumb hover

    # ==================== DIMENSIONES ====================

    # Panel
    PANEL_WIDTH_DEFAULT = 380
    PANEL_WIDTH_MIN = 320
    PANEL_WIDTH_MAX = 600
    PANEL_HEIGHT_DEFAULT = 650
    PANEL_HEIGHT_MIN = 300
    PANEL_HEIGHT_MAX = 900
    PANEL_BORDER_RADIUS = 6

    # Cabecera
    HEADER_HEIGHT = 40
    HEADER_PADDING_V = 8
    HEADER_PADDING_H = 12
    HEADER_FONT_SIZE = 11
    CLOSE_BUTTON_SIZE = 24

    # Cuerpo
    BODY_PADDING = 6
    ITEM_SPACING = 3

    # Items
    ITEM_HEIGHT = 42
    ITEM_PADDING_V = 6
    ITEM_PADDING_H = 10
    ITEM_BORDER_RADIUS = 4
    ITEM_FONT_SIZE = 9.5

    # Iconos y badges
    ICON_SIZE = 14
    ICON_SPACING = 4
    BADGE_PADDING_V = 2
    BADGE_PADDING_H = 6
    BADGE_FONT_SIZE = 8

    # Scrollbar
    SCROLLBAR_WIDTH = 4

    # Resize handle
    RESIZE_HANDLE_SIZE = 12

    # ==================== TIPOGRAFÍA ====================

    FONT_FAMILY = 'Segoe UI, Arial, sans-serif'
    FONT_WEIGHT_NORMAL = 400
    FONT_WEIGHT_SEMIBOLD = 600
    FONT_WEIGHT_BOLD = 700

    # ==================== MÉTODOS DE ESTILOS ====================

    @staticmethod
    def get_panel_style() -> str:
        """
        Retorna el estilo CSS para el panel principal (ventana contenedora)

        Ejemplo:
            panel = QWidget()
            panel.setStyleSheet(PanelStyles.get_panel_style())
        """
        return f"""
            QWidget {{
                background-color: {PanelStyles.BACKGROUND_PRIMARY};
                border: 1px solid {PanelStyles.BORDER_PRIMARY};
                border-radius: {PanelStyles.PANEL_BORDER_RADIUS}px;
            }}
        """

    @staticmethod
    def get_header_style() -> str:
        """
        Retorna el estilo CSS para la cabecera del panel

        Incluye:
        - Fondo secundario
        - Padding optimizado (8px vertical, 12px horizontal)
        - Borde inferior sutil
        - Altura fija de 40px

        Ejemplo:
            header = QWidget()
            header.setStyleSheet(PanelStyles.get_header_style())
        """
        return f"""
            QWidget {{
                background-color: {PanelStyles.BACKGROUND_SECONDARY};
                border: none;
                border-bottom: 1px solid {PanelStyles.BORDER_PRIMARY};
                padding: {PanelStyles.HEADER_PADDING_V}px {PanelStyles.HEADER_PADDING_H}px;
                min-height: {PanelStyles.HEADER_HEIGHT}px;
                max-height: {PanelStyles.HEADER_HEIGHT}px;
            }}
        """

    @staticmethod
    def get_header_title_style() -> str:
        """
        Retorna el estilo CSS para el título en la cabecera

        Ejemplo:
            title = QLabel("🔍 Panel Title")
            title.setStyleSheet(PanelStyles.get_header_title_style())
        """
        return f"""
            QLabel {{
                color: {PanelStyles.TEXT_PRIMARY};
                font-size: {PanelStyles.HEADER_FONT_SIZE}pt;
                font-weight: {PanelStyles.FONT_WEIGHT_SEMIBOLD};
                font-family: {PanelStyles.FONT_FAMILY};
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """

    @staticmethod
    def get_close_button_style() -> str:
        """
        Retorna el estilo CSS para el botón de cerrar en la cabecera

        Incluye estados hover y pressed

        Ejemplo:
            close_btn = QPushButton("✕")
            close_btn.setStyleSheet(PanelStyles.get_close_button_style())
        """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {PanelStyles.TEXT_SECONDARY};
                border: none;
                border-radius: 3px;
                font-size: 14pt;
                font-weight: bold;
                min-width: {PanelStyles.CLOSE_BUTTON_SIZE}px;
                max-width: {PanelStyles.CLOSE_BUTTON_SIZE}px;
                min-height: {PanelStyles.CLOSE_BUTTON_SIZE}px;
                max-height: {PanelStyles.CLOSE_BUTTON_SIZE}px;
                padding: 0px;
                transition: background-color 150ms ease, color 150ms ease;
            }}
            QPushButton:hover {{
                background-color: {PanelStyles.BACKGROUND_HOVER};
                color: {PanelStyles.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {PanelStyles.BACKGROUND_ACTIVE};
                color: {PanelStyles.TEXT_PRIMARY};
            }}
        """

    @staticmethod
    def get_body_style() -> str:
        """
        Retorna el estilo CSS para el cuerpo del panel (área de contenido)

        Incluye:
        - Fondo principal
        - Padding mínimo (6px)
        - Sin bordes

        Ejemplo:
            body = QWidget()
            body.setStyleSheet(PanelStyles.get_body_style())
        """
        return f"""
            QWidget {{
                background-color: {PanelStyles.BACKGROUND_PRIMARY};
                border: none;
                padding: {PanelStyles.BODY_PADDING}px;
            }}
        """

    @staticmethod
    def get_scroll_area_style() -> str:
        """
        Retorna el estilo CSS para QScrollArea

        Incluye estilos para el área scrollable sin bordes

        Ejemplo:
            scroll = QScrollArea()
            scroll.setStyleSheet(PanelStyles.get_scroll_area_style())
        """
        return f"""
            QScrollArea {{
                background-color: {PanelStyles.BACKGROUND_PRIMARY};
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: {PanelStyles.BACKGROUND_PRIMARY};
            }}
        """

    @staticmethod
    def get_scrollbar_style() -> str:
        """
        Retorna el estilo CSS para scrollbars personalizados (vertical y horizontal)

        Características:
        - Ancho/alto: 4px (ultra compacto)
        - Colores sutiles que combinan con la paleta
        - Estados hover suaves
        - Transiciones de 200ms

        Ejemplo:
            scroll_area = QScrollArea()
            scroll_area.setStyleSheet(PanelStyles.get_scrollbar_style())
        """
        return f"""
            /* Scrollbar Vertical */
            QScrollBar:vertical {{
                background-color: {PanelStyles.SCROLLBAR_TRACK};
                width: {PanelStyles.SCROLLBAR_WIDTH}px;
                border: none;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {PanelStyles.SCROLLBAR_THUMB};
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {PanelStyles.SCROLLBAR_THUMB_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            /* Scrollbar Horizontal */
            QScrollBar:horizontal {{
                background-color: {PanelStyles.SCROLLBAR_TRACK};
                height: {PanelStyles.SCROLLBAR_WIDTH}px;
                border: none;
                border-radius: 2px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {PanelStyles.SCROLLBAR_THUMB};
                border-radius: 2px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {PanelStyles.SCROLLBAR_THUMB_HOVER};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """

    @staticmethod
    def get_item_style() -> str:
        """
        Retorna el estilo CSS base para items individuales

        Incluye:
        - Altura fija: 32px
        - Padding optimizado: 6px vertical, 10px horizontal
        - Border-radius: 4px
        - Estados: normal, hover, activo
        - Transiciones suaves: 150ms

        Ejemplo:
            item = QWidget()
            item.setStyleSheet(PanelStyles.get_item_style())
        """
        return f"""
            QWidget {{
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                border-radius: {PanelStyles.ITEM_BORDER_RADIUS}px;
                padding: {PanelStyles.ITEM_PADDING_V}px {PanelStyles.ITEM_PADDING_H}px;
                min-height: {PanelStyles.ITEM_HEIGHT}px;
                max-height: {PanelStyles.ITEM_HEIGHT}px;
                transition: background-color 150ms ease, border-left 150ms ease;
            }}
            QWidget:hover {{
                background-color: {PanelStyles.BACKGROUND_HOVER};
            }}
            QWidget[active="true"] {{
                background-color: {PanelStyles.BACKGROUND_ACTIVE};
                border-left: 3px solid {PanelStyles.ACCENT_PRIMARY};
            }}
        """

    @staticmethod
    def get_item_label_style() -> str:
        """
        Retorna el estilo CSS para labels de items

        Ejemplo:
            label = QLabel("Item label")
            label.setStyleSheet(PanelStyles.get_item_label_style())
        """
        return f"""
            QLabel {{
                color: {PanelStyles.TEXT_PRIMARY};
                font-size: {PanelStyles.ITEM_FONT_SIZE}pt;
                font-weight: {PanelStyles.FONT_WEIGHT_NORMAL};
                font-family: {PanelStyles.FONT_FAMILY};
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """

    @staticmethod
    def get_badge_style(badge_type: str = 'default') -> str:
        """
        Retorna el estilo CSS para badges (favorito, popular, nuevo)

        Args:
            badge_type: Tipo de badge ('favorite', 'popular', 'new', 'default')

        Ejemplo:
            badge = QLabel("⭐")
            badge.setStyleSheet(PanelStyles.get_badge_style('favorite'))
        """
        # Colores según tipo
        colors = {
            'favorite': (PanelStyles.ACCENT_WARNING, '#000000'),  # Naranja, texto negro
            'popular': (PanelStyles.ACCENT_SUCCESS, '#000000'),   # Verde, texto negro
            'new': (PanelStyles.ACCENT_PRIMARY, '#ffffff'),       # Azul, texto blanco
            'default': (PanelStyles.ACCENT_SUBTLE, PanelStyles.TEXT_SECONDARY),
        }

        bg_color, text_color = colors.get(badge_type, colors['default'])

        return f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                font-size: {PanelStyles.BADGE_FONT_SIZE}pt;
                font-weight: {PanelStyles.FONT_WEIGHT_SEMIBOLD};
                font-family: {PanelStyles.FONT_FAMILY};
                border: none;
                border-radius: 3px;
                padding: {PanelStyles.BADGE_PADDING_V}px {PanelStyles.BADGE_PADDING_H}px;
            }}
        """

    @staticmethod
    def get_icon_type_color(item_type: str) -> str:
        """
        Retorna el color apropiado para el icono según el tipo de item

        Args:
            item_type: Tipo de item ('CODE', 'URL', 'PATH', 'TEXT', 'WEB_STATIC')

        Returns:
            Color hexadecimal para el icono

        Ejemplo:
            color = PanelStyles.get_icon_type_color('CODE')
            icon.setStyleSheet(f"color: {color};")
        """
        colors = {
            'CODE': PanelStyles.ACCENT_PRIMARY,      # Azul
            'URL': PanelStyles.ACCENT_SUCCESS,       # Verde
            'PATH': PanelStyles.ACCENT_WARNING,      # Naranja
            'TEXT': PanelStyles.TEXT_SECONDARY,      # Gris
            'WEB_STATIC': PanelStyles.ACCENT_HOVER,  # Azul claro
        }
        return colors.get(item_type, PanelStyles.TEXT_SECONDARY)

    @staticmethod
    def get_icon_type_emoji(item_type: str) -> str:
        """
        Retorna el emoji apropiado para el tipo de item

        Args:
            item_type: Tipo de item ('CODE', 'URL', 'PATH', 'TEXT', 'WEB_STATIC')

        Returns:
            Emoji representativo del tipo

        Ejemplo:
            emoji = PanelStyles.get_icon_type_emoji('CODE')
            icon_label.setText(emoji)
        """
        emojis = {
            'CODE': '📝',
            'URL': '🔗',
            'PATH': '📁',
            'TEXT': '📄',
            'WEB_STATIC': '📱',
        }
        return emojis.get(item_type, '📄')

    @staticmethod
    def get_search_bar_style() -> str:
        """
        Retorna el estilo CSS para la barra de búsqueda

        Ejemplo:
            search_bar = QLineEdit()
            search_bar.setStyleSheet(PanelStyles.get_search_bar_style())
        """
        return f"""
            QLineEdit {{
                background-color: {PanelStyles.BACKGROUND_SECONDARY};
                color: {PanelStyles.TEXT_PRIMARY};
                border: 1px solid {PanelStyles.BORDER_PRIMARY};
                border-radius: {PanelStyles.ITEM_BORDER_RADIUS}px;
                padding: 6px 10px;
                font-size: {PanelStyles.ITEM_FONT_SIZE}pt;
                font-family: {PanelStyles.FONT_FAMILY};
                min-height: {PanelStyles.ITEM_HEIGHT}px;
                max-height: {PanelStyles.ITEM_HEIGHT}px;
                transition: border 150ms ease, background-color 150ms ease;
            }}
            QLineEdit:focus {{
                border: 1px solid {PanelStyles.ACCENT_PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {PanelStyles.TEXT_MUTED};
            }}
        """

    @staticmethod
    def get_combined_style() -> str:
        """
        Retorna todos los estilos combinados para aplicar a un widget raíz

        Útil para aplicar todos los estilos de una vez

        Ejemplo:
            panel = QWidget()
            panel.setStyleSheet(PanelStyles.get_combined_style())
        """
        return f"""
            {PanelStyles.get_scroll_area_style()}
            {PanelStyles.get_scrollbar_style()}
        """

    # ==================== ANIMACIONES ====================

    @staticmethod
    def create_fade_in_animation(widget: QWidget, duration: int = 200) -> QPropertyAnimation:
        """
        Crea una animación de fade-in (aparición gradual)

        Usa windowOpacity en lugar de QGraphicsOpacityEffect para evitar
        conflictos con otros efectos visuales

        Args:
            widget: Widget a animar
            duration: Duración en milisegundos (default: 200ms)

        Returns:
            QPropertyAnimation configurada

        Ejemplo:
            anim = PanelStyles.create_fade_in_animation(panel, 200)
            anim.start()
        """
        # Usar windowOpacity en lugar de graphicsEffect para evitar conflictos
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        return animation

    @staticmethod
    def create_fade_out_animation(widget: QWidget, duration: int = 150) -> QPropertyAnimation:
        """
        Crea una animación de fade-out (desaparición gradual)

        Usa windowOpacity en lugar de QGraphicsOpacityEffect para evitar
        conflictos con otros efectos visuales

        Args:
            widget: Widget a animar
            duration: Duración en milisegundos (default: 150ms)

        Returns:
            QPropertyAnimation configurada

        Ejemplo:
            anim = PanelStyles.create_fade_out_animation(panel, 150)
            anim.finished.connect(panel.close)
            anim.start()
        """
        # Usar windowOpacity en lugar de graphicsEffect para evitar conflictos
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)

        return animation

    @staticmethod
    def create_slide_in_animation(widget: QWidget, start_pos: tuple, end_pos: tuple,
                                  duration: int = 200) -> QPropertyAnimation:
        """
        Crea una animación de deslizamiento (slide-in)

        Args:
            widget: Widget a animar
            start_pos: Posición inicial (x, y)
            end_pos: Posición final (x, y)
            duration: Duración en milisegundos (default: 200ms)

        Returns:
            QPropertyAnimation configurada

        Ejemplo:
            # Deslizar desde la derecha
            start = (screen_width, y_pos)
            end = (x_pos, y_pos)
            anim = PanelStyles.create_slide_in_animation(panel, start, end, 200)
            anim.start()
        """
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration)

        start_rect = QRect(start_pos[0], start_pos[1], widget.width(), widget.height())
        end_rect = QRect(end_pos[0], end_pos[1], widget.width(), widget.height())

        animation.setStartValue(start_rect)
        animation.setEndValue(end_rect)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        return animation

    @staticmethod
    def create_smooth_scroll_animation(scroll_bar, target_value: int,
                                      duration: int = 300) -> QPropertyAnimation:
        """
        Crea una animación de scroll suave

        Args:
            scroll_bar: QScrollBar a animar
            target_value: Valor objetivo del scroll
            duration: Duración en milisegundos (default: 300ms)

        Returns:
            QPropertyAnimation configurada

        Ejemplo:
            scroll_bar = scroll_area.verticalScrollBar()
            anim = PanelStyles.create_smooth_scroll_animation(scroll_bar, 100, 300)
            anim.start()
        """
        animation = QPropertyAnimation(scroll_bar, b"value")
        animation.setDuration(duration)
        animation.setStartValue(scroll_bar.value())
        animation.setEndValue(target_value)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        return animation
