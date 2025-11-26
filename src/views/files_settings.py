# -*- coding: utf-8 -*-
"""
Files Settings Tab - Configuración de gestión de archivos
"""
import os
from pathlib import Path
from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QFileDialog, QMessageBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.config_manager import ConfigManager
from core.file_manager import FileManager


class FilesSettings(QWidget):
    """Widget de configuración de archivos"""

    settings_changed = pyqtSignal()  # Emitido cuando cambia configuración

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.file_manager = FileManager(config_manager)

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Inicializar interfaz de usuario"""
        # Apply dark theme styles
        self.setStyleSheet("""
            FilesSettings {
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
            QLineEdit {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
            QLineEdit:disabled {
                background-color: #1e1e1e;
                color: #666666;
            }
            QTableWidget {
                background-color: #2d2d2d;
                color: #cccccc;
                alternate-background-color: #323232;
                gridline-color: #3d3d3d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 5px;
                color: #cccccc;
            }
            QTableWidget::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: #3d3d3d;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #cccccc;
                padding: 5px;
                border: 1px solid #3d3d3d;
                font-weight: bold;
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
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
            QPushButton:disabled {
                background-color: #1e1e1e;
                color: #666666;
                border: 1px solid #2d2d2d;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Título
        title = QLabel("⚙️ Configuración de Archivos")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Sección 1: Ruta Base
        base_path_group = self._create_base_path_section()
        layout.addWidget(base_path_group)

        # Sección 2: Carpetas de Organización
        folders_group = self._create_folders_section()
        layout.addWidget(folders_group)

        # Sección 3: Opciones Adicionales
        options_group = self._create_options_section()
        layout.addWidget(options_group)

        # Sección 4: Estadísticas (solo lectura)
        stats_group = self._create_stats_section()
        layout.addWidget(stats_group)

        # Botones de acción
        buttons_layout = self._create_buttons_section()
        layout.addLayout(buttons_layout)

        # Stretch al final para empujar todo hacia arriba
        layout.addStretch()

    def _create_base_path_section(self) -> QGroupBox:
        """Crear sección de ruta base"""
        group = QGroupBox("📁 Ruta Base de Almacenamiento")
        layout = QVBoxLayout(group)

        # Descripción
        desc = QLabel(
            "Selecciona la carpeta raíz donde se guardarán los archivos.\n"
            "Los archivos se organizarán automáticamente en subcarpetas según su tipo."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-size: 11px; padding: 5px;")
        layout.addWidget(desc)

        # Input de ruta + botón
        path_layout = QHBoxLayout()

        self.base_path_input = QLineEdit()
        self.base_path_input.setPlaceholderText("Ejemplo: D:\\ARCHIVOS_GENERAL")
        self.base_path_input.setMinimumHeight(35)
        self.base_path_input.textChanged.connect(self._on_base_path_changed)
        path_layout.addWidget(self.base_path_input)

        self.browse_btn = QPushButton("📂 Seleccionar")
        self.browse_btn.setMinimumWidth(120)
        self.browse_btn.setMinimumHeight(35)
        self.browse_btn.clicked.connect(self._browse_folder)
        path_layout.addWidget(self.browse_btn)

        layout.addLayout(path_layout)

        # Validación visual
        self.path_status_label = QLabel("")
        self.path_status_label.setStyleSheet("padding: 5px; font-size: 11px;")
        layout.addWidget(self.path_status_label)

        return group

    def _create_folders_section(self) -> QGroupBox:
        """Crear sección de configuración de carpetas"""
        group = QGroupBox("🗂️ Carpetas de Organización")
        layout = QVBoxLayout(group)

        # Descripción
        desc = QLabel(
            "Configura los nombres de las subcarpetas donde se organizarán los archivos.\n"
            "Cada tipo de archivo se guardará en su carpeta correspondiente."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-size: 11px; padding: 5px;")
        layout.addWidget(desc)

        # Tabla de carpetas
        self.folders_table = QTableWidget()
        self.folders_table.setColumnCount(3)
        self.folders_table.setHorizontalHeaderLabels(["Tipo de Archivo", "Nombre de Carpeta", "Extensiones"])
        self.folders_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.folders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.folders_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.folders_table.setMinimumHeight(250)
        self.folders_table.setAlternatingRowColors(True)
        self.folders_table.itemChanged.connect(self._on_folder_name_edited)
        layout.addWidget(self.folders_table)

        # Botones de tabla
        table_buttons = QHBoxLayout()

        self.reset_folders_btn = QPushButton("🔄 Restaurar Valores por Defecto")
        self.reset_folders_btn.clicked.connect(self._reset_folders_to_default)
        table_buttons.addWidget(self.reset_folders_btn)

        table_buttons.addStretch()

        layout.addLayout(table_buttons)

        return group

    def _create_options_section(self) -> QGroupBox:
        """Crear sección de opciones adicionales"""
        group = QGroupBox("⚙️ Opciones")
        layout = QFormLayout(group)

        # Auto-crear carpetas
        self.auto_create_checkbox = QCheckBox(
            "Crear carpetas automáticamente si no existen"
        )
        self.auto_create_checkbox.setChecked(True)
        self.auto_create_checkbox.stateChanged.connect(self._on_options_changed)
        layout.addRow("Auto-crear:", self.auto_create_checkbox)

        return group

    def _create_stats_section(self) -> QGroupBox:
        """Crear sección de estadísticas"""
        group = QGroupBox("📊 Estadísticas de Almacenamiento")
        layout = QFormLayout(group)

        # Labels de estadísticas
        self.stats_files_count = QLabel("0 archivos")
        self.stats_total_size = QLabel("0 B")
        self.stats_base_path_exists = QLabel("❌ No configurada")

        layout.addRow("Archivos guardados:", self.stats_files_count)
        layout.addRow("Espacio utilizado:", self.stats_total_size)
        layout.addRow("Ruta base:", self.stats_base_path_exists)

        return group

    def _create_buttons_section(self) -> QHBoxLayout:
        """Crear sección de botones de acción"""
        layout = QHBoxLayout()

        self.open_folder_btn = QPushButton("📂 Abrir Carpeta de Archivos")
        self.open_folder_btn.setMinimumHeight(35)
        self.open_folder_btn.clicked.connect(self._open_base_folder)
        layout.addWidget(self.open_folder_btn)

        layout.addStretch()

        self.save_btn = QPushButton("💾 Guardar Cambios")
        self.save_btn.setMinimumHeight(35)
        self.save_btn.setMinimumWidth(150)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.save_btn.clicked.connect(self._save_settings)
        layout.addWidget(self.save_btn)

        return layout

    def load_settings(self):
        """Cargar configuración actual"""
        # Cargar ruta base
        base_path = self.file_manager.get_base_path()
        self.base_path_input.setText(base_path)
        self._validate_base_path(base_path)

        # Cargar configuración de carpetas
        folders_config = self.file_manager.get_folders_config()
        self._populate_folders_table(folders_config)

        # Cargar opciones
        auto_create = self.config_manager.get_files_auto_create_folders()
        self.auto_create_checkbox.setChecked(auto_create)

        # Actualizar estadísticas
        self._update_statistics()

    def _populate_folders_table(self, folders_config: Dict[str, str]):
        """Poblar tabla de carpetas"""
        # Mapeo de tipos a iconos y extensiones
        type_info = {
            'IMAGENES': ('🖼️', '.jpg, .png, .gif, .bmp, .svg, ...'),
            'VIDEOS': ('🎬', '.mp4, .avi, .mkv, .mov, ...'),
            'PDFS': ('📕', '.pdf'),
            'WORDS': ('📘', '.doc, .docx'),
            'EXCELS': ('📊', '.xls, .xlsx, .csv'),
            'TEXT': ('📄', '.txt, .md, .log, ...'),
            'OTROS': ('📎', 'Otros tipos de archivos')
        }

        self.folders_table.setRowCount(len(folders_config))

        row = 0
        for file_type, folder_name in folders_config.items():
            # Columna 1: Tipo (con icono)
            icon, extensions = type_info.get(file_type, ('📎', ''))
            type_item = QTableWidgetItem(f"{icon} {file_type}")
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # No editable
            self.folders_table.setItem(row, 0, type_item)

            # Columna 2: Nombre de carpeta (editable)
            folder_item = QTableWidgetItem(folder_name)
            self.folders_table.setItem(row, 1, folder_item)

            # Columna 3: Extensiones (info)
            ext_item = QTableWidgetItem(extensions)
            ext_item.setFlags(ext_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # No editable
            ext_item.setForeground(Qt.GlobalColor.gray)
            self.folders_table.setItem(row, 2, ext_item)

            row += 1

    def _get_folders_config_from_table(self) -> Dict[str, str]:
        """Obtener configuración de carpetas desde la tabla"""
        config = {}
        for row in range(self.folders_table.rowCount()):
            type_item = self.folders_table.item(row, 0)
            folder_item = self.folders_table.item(row, 1)

            if type_item and folder_item:
                # Extraer tipo sin emoji (ej: "🖼️ IMAGENES" -> "IMAGENES")
                file_type = type_item.text().split()[-1]
                folder_name = folder_item.text().strip()

                if folder_name:  # Solo si hay nombre
                    config[file_type] = folder_name

        return config

    def _browse_folder(self):
        """Abrir diálogo para seleccionar carpeta"""
        current_path = self.base_path_input.text()

        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Carpeta Base",
            current_path if current_path else str(Path.home()),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

        if folder:
            self.base_path_input.setText(folder)

    def _on_base_path_changed(self, text: str):
        """Handler cuando cambia la ruta base"""
        self._validate_base_path(text)

    def _validate_base_path(self, path: str) -> bool:
        """Validar ruta base y actualizar UI"""
        if not path:
            self.path_status_label.setText("⚠️ Ruta no configurada")
            self.path_status_label.setStyleSheet("color: orange; padding: 5px; font-size: 11px;")
            self.open_folder_btn.setEnabled(False)
            return False

        if not os.path.exists(path):
            self.path_status_label.setText("❌ La ruta no existe")
            self.path_status_label.setStyleSheet("color: red; padding: 5px; font-size: 11px;")
            self.open_folder_btn.setEnabled(False)
            return False

        if not os.path.isdir(path):
            self.path_status_label.setText("❌ La ruta no es una carpeta")
            self.path_status_label.setStyleSheet("color: red; padding: 5px; font-size: 11px;")
            self.open_folder_btn.setEnabled(False)
            return False

        # Verificar permisos de escritura
        if not os.access(path, os.W_OK):
            self.path_status_label.setText("⚠️ Sin permisos de escritura")
            self.path_status_label.setStyleSheet("color: orange; padding: 5px; font-size: 11px;")
            self.open_folder_btn.setEnabled(True)
            return False

        self.path_status_label.setText("✅ Ruta válida y con permisos")
        self.path_status_label.setStyleSheet("color: green; padding: 5px; font-size: 11px;")
        self.open_folder_btn.setEnabled(True)
        return True

    def _on_folder_name_edited(self, item: QTableWidgetItem):
        """Handler cuando se edita un nombre de carpeta"""
        # Validar que no esté vacío
        if item.column() == 1:  # Columna de nombre de carpeta
            folder_name = item.text().strip()
            if not folder_name:
                from PyQt6.QtGui import QColor, QBrush
                item.setBackground(QBrush(QColor("#8B0000")))  # Rojo oscuro para errores
                QMessageBox.warning(
                    self,
                    "Nombre Inválido",
                    "El nombre de la carpeta no puede estar vacío."
                )
            else:
                from PyQt6.QtGui import QColor, QBrush
                item.setBackground(QBrush(QColor("#2d2d2d")))  # Fondo oscuro normal

    def _on_options_changed(self):
        """Handler cuando cambian las opciones"""
        pass  # Por ahora solo detectar cambio

    def _reset_folders_to_default(self):
        """Restaurar nombres de carpetas a valores por defecto"""
        reply = QMessageBox.question(
            self,
            "Restaurar Valores por Defecto",
            "¿Deseas restaurar los nombres de las carpetas a los valores por defecto?\n\n"
            "Esto NO afectará los archivos ya guardados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            default_config = {
                'IMAGENES': 'IMAGENES',
                'VIDEOS': 'VIDEOS',
                'PDFS': 'PDFS',
                'WORDS': 'WORDS',
                'EXCELS': 'EXCELS',
                'TEXT': 'TEXT',
                'OTROS': 'OTROS'
            }
            self._populate_folders_table(default_config)

    def _update_statistics(self):
        """Actualizar estadísticas de almacenamiento"""
        # Contar archivos guardados (items con file_hash)
        # Esto requiere acceso a DBManager
        try:
            from database.db_manager import DBManager
            db_path = Path(__file__).parent.parent.parent / "widget_sidebar.db"
            db = DBManager(str(db_path))

            # Contar items con file_hash (archivos guardados)
            cursor = db.conn.execute(
                "SELECT COUNT(*) FROM items WHERE file_hash IS NOT NULL"
            )
            file_count = cursor.fetchone()[0]

            # Calcular espacio total
            cursor = db.conn.execute(
                "SELECT SUM(file_size) FROM items WHERE file_hash IS NOT NULL"
            )
            total_size = cursor.fetchone()[0] or 0

            db.close()

            self.stats_files_count.setText(f"{file_count} archivos")
            self.stats_total_size.setText(self.file_manager.format_file_size(total_size))

        except Exception as e:
            self.stats_files_count.setText("Error al cargar")
            self.stats_total_size.setText("Error al cargar")

        # Estado de ruta base
        base_path = self.base_path_input.text()
        if base_path and os.path.exists(base_path):
            self.stats_base_path_exists.setText(f"✅ {base_path}")
            self.stats_base_path_exists.setStyleSheet("color: green;")
        else:
            self.stats_base_path_exists.setText("❌ No configurada o no existe")
            self.stats_base_path_exists.setStyleSheet("color: red;")

    def _open_base_folder(self):
        """Abrir carpeta base en explorador de archivos"""
        base_path = self.base_path_input.text()

        if not base_path or not os.path.exists(base_path):
            QMessageBox.warning(
                self,
                "Carpeta No Encontrada",
                "La ruta base no existe o no está configurada."
            )
            return

        # Abrir en explorador de archivos de Windows
        os.startfile(base_path)

    def _save_settings(self):
        """Guardar configuración"""
        # Validar ruta base
        base_path = self.base_path_input.text().strip()

        if base_path and not self._validate_base_path(base_path):
            QMessageBox.warning(
                self,
                "Ruta Inválida",
                "La ruta base no es válida. Por favor, selecciona una carpeta existente con permisos de escritura."
            )
            return

        # Obtener configuración de carpetas
        folders_config = self._get_folders_config_from_table()

        # Validar que todas las carpetas tengan nombre
        if len(folders_config) < 7:
            QMessageBox.warning(
                self,
                "Configuración Incompleta",
                "Todas las carpetas deben tener un nombre asignado."
            )
            return

        try:
            # Guardar ruta base
            if base_path:
                self.config_manager.set_files_base_path(base_path)

            # Guardar configuración de carpetas
            self.config_manager.set_files_folders_config(folders_config)

            # Guardar opciones
            auto_create = self.auto_create_checkbox.isChecked()
            self.config_manager.set_files_auto_create_folders(auto_create)

            # Actualizar FileManager con nueva configuración
            self.file_manager = FileManager(self.config_manager)

            # Actualizar estadísticas
            self._update_statistics()

            # Emitir señal de cambio
            self.settings_changed.emit()

            QMessageBox.information(
                self,
                "Configuración Guardada",
                "La configuración de archivos se ha guardado correctamente."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al Guardar",
                f"No se pudo guardar la configuración:\n{str(e)}"
            )
