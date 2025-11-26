"""
Appearance Settings
Widget for configuring theme and appearance options
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSlider, QSpinBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class AppearanceSettings(QWidget):
    """
    Appearance settings widget
    Configure theme, opacity, and window dimensions
    """

    # Signal emitted when settings change
    settings_changed = pyqtSignal()

    def __init__(self, config_manager=None, parent=None):
        """
        Initialize appearance settings

        Args:
            config_manager: ConfigManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Theme group
        theme_group = QGroupBox("Tema")
        theme_layout = QFormLayout()
        theme_layout.setSpacing(10)

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light (próximamente)", "light")
        self.theme_combo.setItemData(1, 0, Qt.ItemDataRole.UserRole - 1)  # Disable light theme
        self.theme_combo.currentIndexChanged.connect(self.settings_changed)
        theme_layout.addRow("Tema:", self.theme_combo)

        theme_group.setLayout(theme_layout)
        main_layout.addWidget(theme_group)

        # Window group
        window_group = QGroupBox("Ventana")
        window_layout = QFormLayout()
        window_layout.setSpacing(10)

        # Opacity slider
        opacity_container = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(50)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(95)
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)

        self.opacity_value_label = QLabel("95%")
        self.opacity_value_label.setFixedWidth(40)
        self.opacity_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        opacity_container.addWidget(self.opacity_slider)
        opacity_container.addWidget(self.opacity_value_label)

        window_layout.addRow("Opacidad:", opacity_container)

        # Sidebar width
        self.sidebar_width_spin = QSpinBox()
        self.sidebar_width_spin.setMinimum(60)
        self.sidebar_width_spin.setMaximum(100)
        self.sidebar_width_spin.setValue(70)
        self.sidebar_width_spin.setSuffix(" px")
        self.sidebar_width_spin.valueChanged.connect(self.settings_changed)
        window_layout.addRow("Ancho sidebar:", self.sidebar_width_spin)

        # Panel width
        self.panel_width_spin = QSpinBox()
        self.panel_width_spin.setMinimum(250)
        self.panel_width_spin.setMaximum(800)  # Aumentado a 800px para mayor flexibilidad
        self.panel_width_spin.setValue(300)
        self.panel_width_spin.setSuffix(" px")
        self.panel_width_spin.setSingleStep(10)  # Incrementos de 10px
        self.panel_width_spin.valueChanged.connect(self.settings_changed)
        window_layout.addRow("Ancho panel:", self.panel_width_spin)

        window_group.setLayout(window_layout)
        main_layout.addWidget(window_group)

        # Animation group
        animation_group = QGroupBox("Animaciones")
        animation_layout = QFormLayout()
        animation_layout.setSpacing(10)

        # Animation speed
        self.animation_speed_spin = QSpinBox()
        self.animation_speed_spin.setMinimum(100)
        self.animation_speed_spin.setMaximum(500)
        self.animation_speed_spin.setValue(250)
        self.animation_speed_spin.setSuffix(" ms")
        self.animation_speed_spin.setSingleStep(50)
        self.animation_speed_spin.valueChanged.connect(self.settings_changed)
        animation_layout.addRow("Velocidad:", self.animation_speed_spin)

        animation_group.setLayout(animation_layout)
        main_layout.addWidget(animation_group)

        # Note
        note_label = QLabel("Nota: Algunos cambios requieren reiniciar la aplicación")
        note_label.setStyleSheet("color: #666666; font-size: 9pt; font-style: italic;")
        note_label.setWordWrap(True)
        main_layout.addWidget(note_label)

        # Spacer
        main_layout.addStretch()

        # Apply widget styles
        self.setStyleSheet("""
            AppearanceSettings {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #cccccc;
                background-color: transparent;
            }
            QGroupBox {
                background-color: #2b2b2b;
                color: #cccccc;
                font-weight: bold;
                font-size: 11pt;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #cccccc;
            }
            QComboBox, QSpinBox {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                min-width: 120px;
            }
            QComboBox:focus, QSpinBox:focus {
                border: 1px solid #007acc;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #cccccc;
                selection-background-color: #007acc;
                selection-color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QSlider::groove:horizontal {
                background: #2d2d2d;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #007acc;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #005a9e;
            }
        """)

    def on_opacity_changed(self, value):
        """Handle opacity slider change"""
        self.opacity_value_label.setText(f"{value}%")
        self.settings_changed.emit()

    def load_settings(self):
        """Load settings from config manager"""
        if not self.config_manager:
            return

        # Load theme
        theme = self.config_manager.get_setting("theme", "dark")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == theme:
                self.theme_combo.setCurrentIndex(i)
                break

        # Load opacity
        opacity = self.config_manager.get_setting("opacity", 0.95)
        self.opacity_slider.setValue(int(opacity * 100))

        # Load dimensions
        sidebar_width = self.config_manager.get_setting("sidebar_width", 70)
        self.sidebar_width_spin.setValue(sidebar_width)

        panel_width = self.config_manager.get_setting("panel_width", 300)
        self.panel_width_spin.setValue(panel_width)

        # Load animation speed
        animation_speed = self.config_manager.get_setting("animation_speed", 250)
        self.animation_speed_spin.setValue(animation_speed)

    def get_settings(self) -> dict:
        """
        Get current settings

        Returns:
            Dictionary with appearance settings
        """
        return {
            "theme": self.theme_combo.currentData(),
            "opacity": self.opacity_slider.value() / 100.0,
            "sidebar_width": self.sidebar_width_spin.value(),
            "panel_width": self.panel_width_spin.value(),
            "animation_speed": self.animation_speed_spin.value()
        }
