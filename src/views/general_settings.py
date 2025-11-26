"""
General Settings
Widget for general application settings
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QSpinBox, QPushButton, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import json
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from views.dialogs.password_verify_dialog import PasswordVerifyDialog

logger = logging.getLogger(__name__)


class GeneralSettings(QWidget):
    """
    General settings widget
    Configure misc application options
    """

    # Signal emitted when settings change
    settings_changed = pyqtSignal()

    def __init__(self, config_manager=None, parent=None):
        """
        Initialize general settings

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

        # Behavior group
        behavior_group = QGroupBox("Comportamiento")
        behavior_layout = QVBoxLayout()
        behavior_layout.setSpacing(10)

        # Minimize to tray checkbox
        self.minimize_tray_check = QCheckBox("Minimizar a tray al cerrar ventana")
        self.minimize_tray_check.setChecked(True)
        self.minimize_tray_check.stateChanged.connect(self.settings_changed)
        behavior_layout.addWidget(self.minimize_tray_check)

        # Always on top checkbox
        self.always_on_top_check = QCheckBox("Mantener ventana siempre visible")
        self.always_on_top_check.setChecked(True)
        self.always_on_top_check.stateChanged.connect(self.settings_changed)
        behavior_layout.addWidget(self.always_on_top_check)

        # Start with Windows checkbox
        self.start_windows_check = QCheckBox("Iniciar con Windows (próximamente)")
        self.start_windows_check.setChecked(False)
        self.start_windows_check.setEnabled(False)
        behavior_layout.addWidget(self.start_windows_check)

        behavior_group.setLayout(behavior_layout)
        main_layout.addWidget(behavior_group)

        # Clipboard group
        clipboard_group = QGroupBox("Portapapeles")
        clipboard_layout = QFormLayout()
        clipboard_layout.setSpacing(10)

        # Max history items
        self.max_history_spin = QSpinBox()
        self.max_history_spin.setMinimum(10)
        self.max_history_spin.setMaximum(50)
        self.max_history_spin.setValue(20)
        self.max_history_spin.setSuffix(" items")
        self.max_history_spin.valueChanged.connect(self.settings_changed)
        clipboard_layout.addRow("Máximo items historial:", self.max_history_spin)

        clipboard_group.setLayout(clipboard_layout)
        main_layout.addWidget(clipboard_group)

        # Import/Export group
        io_group = QGroupBox("Importar/Exportar")
        io_layout = QVBoxLayout()
        io_layout.setSpacing(10)

        # Export button
        export_layout = QHBoxLayout()
        export_label = QLabel("Exportar configuración:")
        self.export_button = QPushButton("Exportar...")
        self.export_button.clicked.connect(self.export_config)
        export_layout.addWidget(export_label)
        export_layout.addStretch()
        export_layout.addWidget(self.export_button)
        io_layout.addLayout(export_layout)

        # Import button
        import_layout = QHBoxLayout()
        import_label = QLabel("Importar configuración:")
        self.import_button = QPushButton("Importar...")
        self.import_button.clicked.connect(self.import_config)
        import_layout.addWidget(import_label)
        import_layout.addStretch()
        import_layout.addWidget(self.import_button)
        io_layout.addLayout(import_layout)

        io_group.setLayout(io_layout)
        main_layout.addWidget(io_group)

        # About group
        about_group = QGroupBox("Acerca de")
        about_layout = QVBoxLayout()
        about_layout.setSpacing(5)

        about_text = QLabel(
            "<b>Widget Sidebar</b><br>"
            "Version: 2.0.0<br>"
            "Framework: PyQt6<br>"
            "Architecture: MVC<br><br>"
            "Gestor avanzado de portapapeles para Windows"
        )
        about_text.setStyleSheet("font-size: 10pt;")
        about_layout.addWidget(about_text)

        about_group.setLayout(about_layout)
        main_layout.addWidget(about_group)

        # Spacer
        main_layout.addStretch()

        # Apply widget styles
        self.setStyleSheet("""
            GeneralSettings {
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
            QCheckBox {
                color: #cccccc;
                spacing: 5px;
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #007acc;
                border-color: #007acc;
            }
            QCheckBox::indicator:hover {
                border-color: #007acc;
            }
            QSpinBox {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                min-width: 100px;
            }
            QSpinBox:focus {
                border: 1px solid #007acc;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #007acc;
            }
        """)

    def load_settings(self):
        """Load settings from config manager"""
        if not self.config_manager:
            return

        # Load minimize to tray (default True)
        minimize_tray = self.config_manager.get_setting("minimize_to_tray", True)
        self.minimize_tray_check.setChecked(minimize_tray)

        # Load always on top
        always_on_top = self.config_manager.get_setting("always_on_top", True)
        self.always_on_top_check.setChecked(always_on_top)

        # Load start with windows
        start_windows = self.config_manager.get_setting("start_with_windows", False)
        self.start_windows_check.setChecked(start_windows)

        # Load max history
        max_history = self.config_manager.get_setting("max_history", 20)
        self.max_history_spin.setValue(max_history)

    def export_config(self):
        """Export configuration to JSON file"""
        if not self.config_manager:
            QMessageBox.warning(
                self,
                "Error",
                "ConfigManager no disponible"
            )
            return

        # Verify password before exporting (security measure)
        password_verified = PasswordVerifyDialog.verify(
            title="Exportar Configuración",
            message="Por razones de seguridad, ingresa tu contraseña para exportar la configuración:",
            parent=self.window()
        )

        if not password_verified:
            # User cancelled or password incorrect
            return

        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Configuración",
            str(Path.home() / "widget_sidebar_config.json"),
            "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            # Export config
            success = self.config_manager.export_config(file_path)
            if success:
                QMessageBox.information(
                    self,
                    "Exportar",
                    f"Configuración exportada exitosamente a:\n{file_path}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "No se pudo exportar la configuración"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al exportar configuración:\n{str(e)}"
            )

    def import_config(self):
        """Import configuration from JSON file"""
        if not self.config_manager:
            QMessageBox.warning(
                self,
                "Error",
                "ConfigManager no disponible"
            )
            return

        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar Configuración",
            str(Path.home()),
            "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            # Import config
            success = self.config_manager.import_config(file_path)
            if success:
                QMessageBox.information(
                    self,
                    "Importar",
                    "Configuración importada exitosamente.\n"
                    "Reinicie la aplicación para aplicar los cambios."
                )
                # Reload settings
                self.load_settings()
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "No se pudo importar la configuración"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al importar configuración:\n{str(e)}"
            )

    def get_settings(self) -> dict:
        """
        Get current general settings

        Returns:
            Dictionary with general settings
        """
        return {
            "minimize_to_tray": self.minimize_tray_check.isChecked(),
            "always_on_top": self.always_on_top_check.isChecked(),
            "start_with_windows": self.start_windows_check.isChecked(),
            "max_history": self.max_history_spin.value()
        }
