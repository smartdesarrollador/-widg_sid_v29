"""
Panel Resizer - Utilidad para redimensionar paneles flotantes
Permite redimensionar ventanas desde cualquier borde o esquina
"""

from PyQt6.QtCore import Qt, QObject, QPoint, pyqtSignal
from PyQt6.QtGui import QCursor, QMouseEvent
from PyQt6.QtWidgets import QWidget
from typing import Optional


class ResizeEdge:
    """Enumeración de bordes y esquinas para redimensionamiento"""
    NONE = 0
    LEFT = 1
    RIGHT = 2
    TOP = 4
    BOTTOM = 8
    TOP_LEFT = TOP | LEFT
    TOP_RIGHT = TOP | RIGHT
    BOTTOM_LEFT = BOTTOM | LEFT
    BOTTOM_RIGHT = BOTTOM | RIGHT


class PanelResizer(QObject):
    """
    Gestor de redimensionamiento para paneles flotantes

    Características:
    - Detección de 8 áreas: 4 bordes + 4 esquinas
    - Cambio automático de cursor según área
    - Validación de límites mín/máx
    - Señal emitida al completar redimensión

    Uso:
        resizer = PanelResizer(panel, min_width=320, max_width=600)
        resizer.resized.connect(on_panel_resized)
    """

    # Señal emitida cuando el panel se redimensiona
    resized = pyqtSignal(int, int)  # width, height

    def __init__(
        self,
        widget: QWidget,
        min_width: int = 320,
        max_width: int = 600,
        min_height: int = 300,
        max_height: int = 800,
        handle_size: int = 8
    ):
        """
        Inicializa el redimensionador

        Args:
            widget: Widget/ventana a redimensionar
            min_width: Ancho mínimo permitido
            max_width: Ancho máximo permitido
            min_height: Alto mínimo permitido
            max_height: Alto máximo permitido
            handle_size: Tamaño del área sensible en los bordes (px)
        """
        super().__init__()

        self.widget = widget
        self.min_width = min_width
        self.max_width = max_width
        self.min_height = min_height
        self.max_height = max_height
        self.handle_size = handle_size

        # Estado del redimensionamiento
        self.is_resizing = False
        self.resize_edge = ResizeEdge.NONE
        self.drag_start_pos = QPoint()
        self.drag_start_geometry = None

        # Instalar event filter en el widget
        self.widget.installEventFilter(self)
        self.widget.setMouseTracking(True)

    def eventFilter(self, obj: QObject, event: QMouseEvent) -> bool:
        """
        Filtra eventos del widget para detectar redimensionamiento

        Args:
            obj: Objeto que emitió el evento
            event: Evento a procesar

        Returns:
            True si el evento fue manejado, False en caso contrario
        """
        if obj != self.widget:
            return False

        event_type = event.type()

        if event_type == event.Type.MouseMove:
            return self._handle_mouse_move(event)
        elif event_type == event.Type.MouseButtonPress:
            return self._handle_mouse_press(event)
        elif event_type == event.Type.MouseButtonRelease:
            return self._handle_mouse_release(event)

        return False

    def _handle_mouse_move(self, event: QMouseEvent) -> bool:
        """
        Maneja el movimiento del mouse

        Args:
            event: Evento de movimiento del mouse

        Returns:
            True si se está redimensionando
        """
        if self.is_resizing:
            # Redimensionar el panel
            self._resize_panel(event.globalPosition().toPoint())
            return True
        else:
            # Actualizar cursor según posición
            edge = self._get_resize_edge(event.pos())
            self._update_cursor(edge)
            return False

    def _handle_mouse_press(self, event: QMouseEvent) -> bool:
        """
        Maneja el clic del mouse

        Args:
            event: Evento de clic del mouse

        Returns:
            True si se inició redimensionamiento
        """
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge != ResizeEdge.NONE:
                # Iniciar redimensionamiento
                self.is_resizing = True
                self.resize_edge = edge
                self.drag_start_pos = event.globalPosition().toPoint()
                self.drag_start_geometry = self.widget.geometry()
                return True

        return False

    def _handle_mouse_release(self, event: QMouseEvent) -> bool:
        """
        Maneja la liberación del mouse

        Args:
            event: Evento de liberación del mouse

        Returns:
            True si se completó redimensionamiento
        """
        if event.button() == Qt.MouseButton.LeftButton and self.is_resizing:
            # Finalizar redimensionamiento
            self.is_resizing = False
            self.resize_edge = ResizeEdge.NONE

            # Limpiar tooltip de dimensiones
            self.widget.setToolTip("")

            # Emitir señal con nuevas dimensiones
            self.resized.emit(self.widget.width(), self.widget.height())

            # Restaurar cursor
            self._update_cursor(self._get_resize_edge(event.pos()))
            return True

        return False

    def _get_resize_edge(self, pos: QPoint) -> int:
        """
        Determina qué borde/esquina está bajo el cursor

        Args:
            pos: Posición del cursor relativa al widget

        Returns:
            Código de borde (ResizeEdge.*)
        """
        rect = self.widget.rect()
        edge = ResizeEdge.NONE

        # Detectar borde izquierdo
        if pos.x() <= self.handle_size:
            edge |= ResizeEdge.LEFT
        # Detectar borde derecho
        elif pos.x() >= rect.width() - self.handle_size:
            edge |= ResizeEdge.RIGHT

        # Detectar borde superior
        if pos.y() <= self.handle_size:
            edge |= ResizeEdge.TOP
        # Detectar borde inferior
        elif pos.y() >= rect.height() - self.handle_size:
            edge |= ResizeEdge.BOTTOM

        return edge

    def _update_cursor(self, edge: int):
        """
        Actualiza el cursor según el borde

        Args:
            edge: Código de borde (ResizeEdge.*)
        """
        cursor = Qt.CursorShape.ArrowCursor

        if edge == ResizeEdge.LEFT or edge == ResizeEdge.RIGHT:
            cursor = Qt.CursorShape.SizeHorCursor
        elif edge == ResizeEdge.TOP or edge == ResizeEdge.BOTTOM:
            cursor = Qt.CursorShape.SizeVerCursor
        elif edge == ResizeEdge.TOP_LEFT or edge == ResizeEdge.BOTTOM_RIGHT:
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif edge == ResizeEdge.TOP_RIGHT or edge == ResizeEdge.BOTTOM_LEFT:
            cursor = Qt.CursorShape.SizeBDiagCursor

        self.widget.setCursor(cursor)

    def _resize_panel(self, global_pos: QPoint):
        """
        Redimensiona el panel según el movimiento del mouse

        Args:
            global_pos: Posición global del cursor
        """
        if not self.drag_start_geometry:
            return

        # Calcular delta de movimiento
        delta = global_pos - self.drag_start_pos

        # Obtener geometría inicial
        x = self.drag_start_geometry.x()
        y = self.drag_start_geometry.y()
        width = self.drag_start_geometry.width()
        height = self.drag_start_geometry.height()

        # Aplicar cambios según borde activo
        if self.resize_edge & ResizeEdge.LEFT:
            new_width = width - delta.x()
            if self.min_width <= new_width <= self.max_width:
                x += delta.x()
                width = new_width

        if self.resize_edge & ResizeEdge.RIGHT:
            new_width = width + delta.x()
            if self.min_width <= new_width <= self.max_width:
                width = new_width

        if self.resize_edge & ResizeEdge.TOP:
            new_height = height - delta.y()
            if self.min_height <= new_height <= self.max_height:
                y += delta.y()
                height = new_height

        if self.resize_edge & ResizeEdge.BOTTOM:
            new_height = height + delta.y()
            if self.min_height <= new_height <= self.max_height:
                height = new_height

        # Aplicar nueva geometría
        self.widget.setGeometry(x, y, width, height)

        # Actualizar tooltip con dimensiones actuales durante redimensión
        self.widget.setToolTip(f"{width} × {height} px")

    def set_limits(
        self,
        min_width: Optional[int] = None,
        max_width: Optional[int] = None,
        min_height: Optional[int] = None,
        max_height: Optional[int] = None
    ):
        """
        Actualiza los límites de tamaño

        Args:
            min_width: Ancho mínimo
            max_width: Ancho máximo
            min_height: Alto mínimo
            max_height: Alto máximo
        """
        if min_width is not None:
            self.min_width = min_width
        if max_width is not None:
            self.max_width = max_width
        if min_height is not None:
            self.min_height = min_height
        if max_height is not None:
            self.max_height = max_height

    def get_current_size(self) -> tuple[int, int]:
        """
        Obtiene el tamaño actual del panel

        Returns:
            Tupla (width, height)
        """
        return (self.widget.width(), self.widget.height())

    def disable(self):
        """Deshabilita el redimensionamiento"""
        self.widget.removeEventFilter(self)
        self.widget.setCursor(Qt.CursorShape.ArrowCursor)

    def enable(self):
        """Habilita el redimensionamiento"""
        if not self.widget.testAttribute(Qt.WidgetAttribute.WA_Hover):
            self.widget.installEventFilter(self)
            self.widget.setMouseTracking(True)
