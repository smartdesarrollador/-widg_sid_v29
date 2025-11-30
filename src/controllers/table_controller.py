"""
Table Controller
Gestiona la lógica de negocio de tablas de items
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal

sys.path.insert(0, str(Path(__file__).parent.parent))
from database.db_manager import DBManager
from core.table_validator import TableValidator

logger = logging.getLogger(__name__)


class TableController(QObject):
    """
    Controlador para gestionar tablas de items

    Responsabilidades:
    - Validaciones de negocio
    - Creación y gestión de tablas
    - Actualización de celdas
    - Exportación de datos
    - Emisión de señales PyQt6
    - Logging de operaciones
    """

    # Señales PyQt6
    table_created = pyqtSignal(str, int, int)  # (table_name, items_created, category_id)
    table_updated = pyqtSignal(str, int)  # (table_name, category_id)
    table_deleted = pyqtSignal(str, int)  # (table_name, category_id)
    table_renamed = pyqtSignal(str, str, int)  # (old_name, new_name, category_id)

    # Señales de error
    error_occurred = pyqtSignal(str)  # (error_message)

    def __init__(self, db_manager: DBManager):
        """
        Inicializa el controlador de tablas

        Args:
            db_manager: Gestor de base de datos
        """
        super().__init__()
        self.db = db_manager

        logger.info("TableController initialized")

    # ========== VALIDACIONES ==========

    def validate_table_name(self, table_name: str, exclude_table: str = None) -> tuple:
        """
        Valida que el nombre de tabla sea válido y único

        Args:
            table_name: Nombre de la tabla a validar
            exclude_table: Nombre de tabla a excluir (para edición)

        Returns:
            Tuple (is_valid, error_message)
        """
        try:
            # Obtener lista de tablas existentes
            existing_tables = self._get_existing_table_names()

            # Usar TableValidator para validación
            is_valid, error_msg = TableValidator.validate_table_name(
                table_name,
                existing_tables=existing_tables,
                exclude_table=exclude_table
            )

            return is_valid, error_msg

        except Exception as e:
            logger.error(f"Error validating table name: {e}")
            return False, f"Error al validar nombre: {str(e)}"

    def validate_table_data(self, table_data: List[List[str]], min_filled: int = 1) -> tuple:
        """
        Valida que los datos de tabla tengan al menos N celdas llenas

        Args:
            table_data: Matriz de datos
            min_filled: Mínimo de celdas llenas requeridas

        Returns:
            Tuple (is_valid, error_message, filled_count)
        """
        # Usar TableValidator
        return TableValidator.validate_table_data(table_data, min_filled)

    def sanitize_cell_content(self, content: str) -> str:
        """
        Limpia y normaliza contenido de celda

        Args:
            content: Contenido a sanitizar

        Returns:
            Contenido sanitizado
        """
        # Usar TableValidator
        return TableValidator.sanitize_cell_content(content)

    # ========== OPERACIONES DE TABLA ==========

    def create_table(self, category_id: int, table_name: str, table_data: List[List[str]],
                    column_names: List[str], tags: List[str] = None, sensitive_columns: List[int] = None,
                    url_columns: List[int] = None) -> Dict[str, Any]:
        """
        Crea todos los items de una tabla

        Lógica:
        1. Validar nombre único
        2. Validar datos mínimos
        3. Iterar por cada celda con datos
        4. Crear item con:
           - label = nombre_columna
           - content = valor_celda (sanitizado)
           - is_table = 1
           - name_table = nombre_tabla
           - orden_table = [fila, columna]
           - is_list = 1
           - list_group = f"{nombre_tabla}_row_{fila}"
           - orden_lista = columna
           - is_sensitive = 1 si columna está en sensitive_columns
           - tags = tags + nombre_tabla
        5. Inserción en transacción única
        6. Retornar resumen (items creados, tiempo, etc.)

        Args:
            category_id: ID de categoría destino
            table_name: Nombre de la tabla
            table_data: Matriz de datos
            column_names: Lista de nombres de columnas
            tags: Tags opcionales
            sensitive_columns: Índices de columnas sensibles (opcional)
            url_columns: Índices de columnas tipo URL (opcional)

        Returns:
            Dict con 'success', 'items_created', 'table_name', 'errors', 'filled_cells'
        """
        try:
            logger.info(f"[TableController] Creating table '{table_name}'")

            # Validación 1: Nombre de tabla
            is_valid_name, error_msg = self.validate_table_name(table_name)
            if not is_valid_name:
                logger.error(f"Invalid table name: {error_msg}")
                self.error_occurred.emit(error_msg)
                return {
                    'success': False,
                    'items_created': 0,
                    'table_name': table_name,
                    'errors': [error_msg],
                    'filled_cells': 0
                }

            # Validación 2: Datos de tabla
            is_valid_data, error_msg, filled_count = self.validate_table_data(table_data, min_filled=1)
            if not is_valid_data:
                logger.error(f"Invalid table data: {error_msg}")
                self.error_occurred.emit(error_msg)
                return {
                    'success': False,
                    'items_created': 0,
                    'table_name': table_name,
                    'errors': [error_msg],
                    'filled_cells': filled_count
                }

            # Sanitizar datos usando TableValidator
            sanitized_data = TableValidator.sanitize_table_data(table_data)

            # Crear tabla en BD
            result = self.db.add_table_items(
                category_id=category_id,
                table_name=table_name,
                table_data=sanitized_data,
                column_names=column_names,
                tags=tags,
                sensitive_columns=sensitive_columns,
                url_columns=url_columns
            )

            if result['success']:
                logger.info(f"Table '{table_name}' created: {result['items_created']} items")

                # Emitir señal
                self.table_created.emit(table_name, result['items_created'], category_id)

                return {
                    'success': True,
                    'items_created': result['items_created'],
                    'table_name': table_name,
                    'errors': result.get('errors', []),
                    'filled_cells': filled_count
                }
            else:
                logger.error(f"Failed to create table: {result['errors']}")
                self.error_occurred.emit('; '.join(result['errors'][:3]))
                return result

        except Exception as e:
            logger.error(f"Error creating table: {e}", exc_info=True)
            self.error_occurred.emit(f"Error al crear tabla: {str(e)}")
            return {
                'success': False,
                'items_created': 0,
                'table_name': table_name,
                'errors': [str(e)],
                'filled_cells': 0
            }

    def get_table_structure(self, table_name: str) -> Dict[str, Any]:
        """
        Retorna estructura de tabla para reconstrucción

        Args:
            table_name: Nombre de la tabla

        Returns:
            Dict con estructura completa de la tabla
        """
        try:
            logger.info(f"Getting structure for table '{table_name}'")

            # Obtener datos exportados
            export_data = self.db.export_table_to_dict(table_name)

            if not export_data or not export_data.get('rows'):
                logger.warning(f"Table '{table_name}' not found or empty")
                return {
                    'success': False,
                    'table_name': table_name,
                    'error': 'Tabla no encontrada o vacía'
                }

            return {
                'success': True,
                'table_name': export_data['table_name'],
                'columns': export_data['columns'],
                'rows': export_data['rows'],
                'metadata': export_data['metadata']
            }

        except Exception as e:
            logger.error(f"Error getting table structure: {e}")
            return {
                'success': False,
                'table_name': table_name,
                'error': str(e)
            }

    def update_table(self, table_name: str, table_data: List[List[str]],
                    column_names: List[str] = None) -> Dict[str, Any]:
        """
        Actualiza todos los items de una tabla

        Args:
            table_name: Nombre de la tabla
            table_data: Nueva matriz de datos
            column_names: Nuevos nombres de columnas (opcional)

        Returns:
            Dict con resultado de operación
        """
        try:
            logger.info(f"Updating table '{table_name}'")

            # Validar que la tabla existe
            existing_items = self.db.get_table_items(table_name)
            if not existing_items:
                error_msg = f"Tabla '{table_name}' no encontrada"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return {
                    'success': False,
                    'table_name': table_name,
                    'error': error_msg
                }

            # Actualizar celdas una por una
            updates_count = 0
            errors = []

            for row_idx, row_data in enumerate(table_data):
                for col_idx, cell_value in enumerate(row_data):
                    sanitized_value = self.sanitize_cell_content(cell_value)

                    success = self.db.update_table_cell(
                        table_name=table_name,
                        row=row_idx,
                        col=col_idx,
                        new_content=sanitized_value
                    )

                    if success:
                        updates_count += 1
                    else:
                        errors.append(f"Error updating cell [{row_idx}, {col_idx}]")

            # Obtener category_id de la tabla
            category_id = existing_items[0].get('category_id') if existing_items else None

            # Emitir señal
            if category_id:
                self.table_updated.emit(table_name, category_id)

            logger.info(f"Table '{table_name}' updated: {updates_count} cells")

            return {
                'success': updates_count > 0,
                'table_name': table_name,
                'updates_count': updates_count,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Error updating table: {e}", exc_info=True)
            self.error_occurred.emit(f"Error al actualizar tabla: {str(e)}")
            return {
                'success': False,
                'table_name': table_name,
                'error': str(e)
            }

    def delete_table(self, table_name: str) -> Dict[str, Any]:
        """
        Elimina todos los items de una tabla

        Args:
            table_name: Nombre de la tabla a eliminar

        Returns:
            Dict con resultado de operación
        """
        try:
            logger.info(f"Deleting table '{table_name}'")

            # Obtener info antes de eliminar
            existing_items = self.db.get_table_items(table_name)
            if not existing_items:
                error_msg = f"Tabla '{table_name}' no encontrada"
                logger.warning(error_msg)
                return {
                    'success': False,
                    'table_name': table_name,
                    'error': error_msg
                }

            category_id = existing_items[0].get('category_id')

            # Eliminar tabla
            success = self.db.delete_table(table_name)

            if success:
                logger.info(f"Table '{table_name}' deleted successfully")

                # Emitir señal
                if category_id:
                    self.table_deleted.emit(table_name, category_id)

                return {
                    'success': True,
                    'table_name': table_name,
                    'items_deleted': len(existing_items)
                }
            else:
                error_msg = f"Error al eliminar tabla '{table_name}'"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return {
                    'success': False,
                    'table_name': table_name,
                    'error': error_msg
                }

        except Exception as e:
            logger.error(f"Error deleting table: {e}", exc_info=True)
            self.error_occurred.emit(f"Error al eliminar tabla: {str(e)}")
            return {
                'success': False,
                'table_name': table_name,
                'error': str(e)
            }

    # ========== UTILIDADES ==========

    def _get_existing_table_names(self) -> List[str]:
        """
        Obtiene lista de nombres de tablas existentes.

        Returns:
            Lista de nombres de tablas
        """
        try:
            # Obtener todas las tablas desde la BD usando la nueva estructura
            tables = self.db.get_all_tables()

            # Extraer nombres
            table_names = [table['name'] for table in tables]

            logger.debug(f"Found {len(table_names)} existing tables")
            return table_names

        except Exception as e:
            logger.error(f"Error getting existing table names: {e}")
            return []

    def get_tables_summary(self, category_id: int = None) -> List[Dict[str, Any]]:
        """
        Obtiene resumen de todas las tablas (opcionalmente filtradas por categoría)

        Args:
            category_id: ID de categoría (None = todas)

        Returns:
            Lista de diccionarios con info de tablas:
            {
                'table_name': str,
                'category_name': str,
                'rows': int,
                'cols': int,
                'item_count': int,
                'created_at': str
            }
        """
        try:
            # Obtener todas las categorías para mapear IDs a nombres
            categories = self.db.get_categories()
            category_map = {}
            for cat in categories:
                if isinstance(cat, dict):
                    category_map[cat.get('id')] = cat.get('name', 'Sin Categoría')
                else:
                    category_map[cat.id] = cat.name

            tables_summary = []

            if category_id:
                # Filtrar solo una categoría
                cat_tables = self.db.get_tables_by_category(category_id)
                for table in cat_tables:
                    tables_summary.append({
                        'table_name': table.get('name'),
                        'category_name': category_map.get(category_id, 'Sin Categoría'),
                        'rows': table.get('rows', 0),
                        'cols': table.get('cols', 0),
                        'item_count': table.get('item_count', 0),
                        'created_at': table.get('created_at')
                    })
            else:
                # Obtener de todas las categorías
                for cat in categories:
                    cat_id = cat.get('id') if isinstance(cat, dict) else cat.id
                    cat_name = category_map.get(cat_id, 'Sin Categoría')

                    cat_tables = self.db.get_tables_by_category(cat_id)
                    for table in cat_tables:
                        tables_summary.append({
                            'table_name': table.get('name'),
                            'category_name': cat_name,
                            'rows': table.get('rows', 0),
                            'cols': table.get('cols', 0),
                            'item_count': table.get('item_count', 0),
                            'created_at': table.get('created_at')
                        })

            logger.info(f"Found {len(tables_summary)} tables")
            return tables_summary

        except Exception as e:
            logger.error(f"Error getting tables summary: {e}", exc_info=True)
            return []
