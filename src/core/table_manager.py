"""
TableManager - Manager para operaciones de alto nivel con tablas
"""
import logging
from typing import Optional, Dict, List
from src.database.db_manager import DBManager

logger = logging.getLogger(__name__)


class TableManager:
    """Manager para operaciones de alto nivel con tablas"""

    def __init__(self, db_manager: DBManager):
        """
        Inicializa TableManager

        Args:
            db_manager: Instancia de DBManager
        """
        self.db = db_manager
        self._table_cache = {}  # Cache: name -> table_id

    def get_or_create_table(self, name: str, description: str = "") -> int:
        """
        Obtiene table_id o crea tabla si no existe

        Args:
            name: Nombre de la tabla
            description: Descripción de la tabla (opcional)

        Returns:
            int: ID de la tabla
        """
        # Check cache first
        if name in self._table_cache:
            table_id = self._table_cache[name]
            # Verify it still exists
            if self.db.get_table(table_id):
                return table_id
            else:
                # Cache outdated, remove
                del self._table_cache[name]

        # Check database
        table = self.db.get_table_by_name(name)
        if table:
            table_id = table['id']
            self._table_cache[name] = table_id
            return table_id

        # Create new table
        table_id = self.db.add_table(name, description)
        self._table_cache[name] = table_id
        logger.info(f"Table created: {name} (ID: {table_id})")
        return table_id

    def get_table_info(self, table_id: int) -> Optional[Dict]:
        """
        Obtiene información completa de una tabla con estadísticas

        Args:
            table_id: ID de la tabla

        Returns:
            Dict con info de tabla + estadísticas o None
        """
        table = self.db.get_table(table_id)
        if not table:
            return None

        items_count = self.db.count_items_in_table(table_id)

        return {
            **table,
            'items_count': items_count
        }

    def get_table_info_by_name(self, name: str) -> Optional[Dict]:
        """
        Obtiene información de tabla por nombre

        Args:
            name: Nombre de la tabla

        Returns:
            Dict con info de tabla o None
        """
        table = self.db.get_table_by_name(name)
        if not table:
            return None

        return self.get_table_info(table['id'])

    def rename_table(self, table_id: int, new_name: str) -> bool:
        """
        Renombra una tabla (afecta todos los items asociados)

        Args:
            table_id: ID de la tabla
            new_name: Nuevo nombre

        Returns:
            bool: True si tuvo éxito
        """
        try:
            # Get old name for cache invalidation
            table = self.db.get_table(table_id)
            if not table:
                logger.warning(f"Table {table_id} not found for rename")
                return False

            old_name = table['name']

            # Update in DB
            self.db.update_table(table_id, name=new_name)

            # Update cache
            if old_name in self._table_cache:
                del self._table_cache[old_name]
            self._table_cache[new_name] = table_id

            logger.info(f"Table renamed: '{old_name}' -> '{new_name}'")
            return True

        except Exception as e:
            logger.error(f"Error renaming table {table_id}: {e}")
            return False

    def delete_table(self, table_id: int) -> bool:
        """
        Elimina una tabla (CASCADE elimina items asociados)

        Args:
            table_id: ID de la tabla

        Returns:
            bool: True si tuvo éxito
        """
        try:
            # Get name for cache invalidation
            table = self.db.get_table(table_id)
            if table:
                name = table['name']
                if name in self._table_cache:
                    del self._table_cache[name]

            # Delete from DB (CASCADE will delete items)
            self.db.delete_table(table_id)
            logger.info(f"Table deleted: ID {table_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting table {table_id}: {e}")
            return False

    def get_all_tables(self) -> List[Dict]:
        """
        Obtiene todas las tablas con estadísticas

        Returns:
            List de diccionarios con info de tablas
        """
        tables = self.db.get_all_tables()

        # Enrich with stats
        for table in tables:
            table['items_count'] = self.db.count_items_in_table(table['id'])

        return tables

    def get_tables_by_category(self, category_id: int) -> List[Dict]:
        """
        Obtiene tablas de una categoría específica

        Args:
            category_id: ID de categoría

        Returns:
            List de diccionarios con info de tablas
        """
        return self.db.get_tables_by_category(category_id)

    def clear_cache(self):
        """Limpia el caché de tablas"""
        self._table_cache.clear()
        logger.debug("Table cache cleared")

    def invalidate_table(self, table_id: int):
        """
        Invalida una tabla específica del caché

        Args:
            table_id: ID de la tabla
        """
        # Find and remove from cache
        to_remove = []
        for name, cached_id in self._table_cache.items():
            if cached_id == table_id:
                to_remove.append(name)

        for name in to_remove:
            del self._table_cache[name]

        logger.debug(f"Table {table_id} invalidated from cache")
