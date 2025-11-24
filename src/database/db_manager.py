"""
Database Manager for Widget Sidebar
Manages SQLite database operations for settings, categories, items, and clipboard history
"""

import sqlite3
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DBManager:
    """Gestor de base de datos SQLite para Widget Sidebar"""

    def __init__(self, db_path: str = "widget_sidebar.db"):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection = None
        self._ensure_database()
        logger.info(f"Database initialized at: {self.db_path}")

    def _ensure_database(self):
        """Create database and tables if they don't exist"""
        # Check if it's an in-memory database or file doesn't exist
        is_memory_db = str(self.db_path) == ":memory:"
        if is_memory_db or not self.db_path.exists():
            logger.info("Creating new database...")
            self._create_database()
        else:
            logger.info("Database already exists")

    def connect(self) -> sqlite3.Connection:
        """
        Establish connection to the database

        Returns:
            sqlite3.Connection: Database connection
        """
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions

        Usage:
            with db.transaction() as conn:
                conn.execute(...)
        """
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

    def _create_database(self):
        """Create database schema with all tables and indices - COMPLETE SCHEMA"""
        # Use self.connect() to ensure we use the same connection (important for :memory:)
        conn = self.connect()
        cursor = conn.cursor()

        # Read SQL schema from file if it exists, otherwise use embedded schema
        schema_file = Path(__file__).parent.parent.parent / "util" / "complete_schema.sql"

        if schema_file.exists():
            logger.info(f"Loading schema from file: {schema_file}")
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            cursor.executescript(schema_sql)
        else:
            # Embedded complete schema
            cursor.executescript("""
                -- Tabla de configuración general
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Tabla de categorías
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    icon TEXT,
                    order_index INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    is_predefined BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    color TEXT,
                    badge TEXT,
                    item_count INTEGER DEFAULT 0,
                    total_uses INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    is_pinned BOOLEAN DEFAULT 0,
                    pinned_order INTEGER DEFAULT 0
                );

                -- Tabla de items (COMPLETA con TODOS los campos)
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    content TEXT NOT NULL,
                    type TEXT CHECK(type IN ('TEXT', 'URL', 'CODE', 'PATH')) DEFAULT 'TEXT',
                    icon TEXT,
                    is_sensitive BOOLEAN DEFAULT 0,
                    is_favorite INTEGER DEFAULT 0,
                    favorite_order INTEGER DEFAULT 0,
                    use_count INTEGER DEFAULT 0,
                    tags TEXT,
                    description TEXT,
                    working_dir TEXT,
                    shortcut TEXT,
                    color TEXT,
                    badge TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_archived BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    is_list BOOLEAN DEFAULT 0,
                    list_group TEXT DEFAULT NULL,
                    orden_lista INTEGER DEFAULT 0,
                    file_size INTEGER DEFAULT NULL,
                    file_type VARCHAR(50) DEFAULT NULL,
                    file_extension VARCHAR(10) DEFAULT NULL,
                    original_filename VARCHAR(255) DEFAULT NULL,
                    file_hash VARCHAR(64) DEFAULT NULL,
                    is_table BOOLEAN DEFAULT 0,
                    name_table TEXT DEFAULT NULL,
                    orden_table TEXT DEFAULT NULL,
                    is_component BOOLEAN DEFAULT 0,
                    name_component VARCHAR(50) DEFAULT NULL,
                    component_config TEXT DEFAULT NULL,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                );

                -- Tabla de historial de portapapeles
                CREATE TABLE IF NOT EXISTS clipboard_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    content TEXT NOT NULL,
                    copied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE SET NULL
                );

                -- Tabla de historial de uso de items
                CREATE TABLE IF NOT EXISTS item_usage_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    used_at TEXT NOT NULL DEFAULT (datetime('now')),
                    execution_time_ms INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 1,
                    error_message TEXT,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
                );

                -- Tabla de paneles anclados (COMPLETA con campos de global search)
                CREATE TABLE IF NOT EXISTS pinned_panels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    custom_name TEXT,
                    custom_color TEXT,
                    x_position INTEGER NOT NULL,
                    y_position INTEGER NOT NULL,
                    width INTEGER NOT NULL DEFAULT 350,
                    height INTEGER NOT NULL DEFAULT 500,
                    is_minimized BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_opened TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    open_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    panel_type TEXT DEFAULT 'category',
                    search_query TEXT DEFAULT NULL,
                    advanced_filters TEXT DEFAULT NULL,
                    state_filter TEXT DEFAULT 'normal',
                    filter_config TEXT DEFAULT NULL,
                    keyboard_shortcut TEXT DEFAULT NULL,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                );

                -- Tabla de procesos
                CREATE TABLE IF NOT EXISTS processes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    icon TEXT DEFAULT '⚙',
                    color TEXT,
                    is_pinned BOOLEAN DEFAULT 0,
                    pinned_order INTEGER DEFAULT 0,
                    order_index INTEGER DEFAULT 0,
                    use_count INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    is_archived BOOLEAN DEFAULT 0,
                    auto_copy_results BOOLEAN DEFAULT 0,
                    execution_mode TEXT DEFAULT 'sequential',
                    delay_between_steps INTEGER DEFAULT 500,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,
                    category TEXT
                );

                -- Tabla de items de procesos
                CREATE TABLE IF NOT EXISTS process_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    process_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    step_order INTEGER NOT NULL,
                    group_name TEXT,
                    group_order INTEGER DEFAULT 0,
                    is_optional BOOLEAN DEFAULT 0,
                    is_enabled BOOLEAN DEFAULT 1,
                    wait_for_confirmation BOOLEAN DEFAULT 0,
                    custom_label TEXT,
                    notes TEXT,
                    condition_type TEXT DEFAULT 'always',
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (process_id) REFERENCES processes(id) ON DELETE CASCADE,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
                    UNIQUE(process_id, item_id, step_order)
                );

                -- Tabla de paneles anclados de procesos
                CREATE TABLE IF NOT EXISTS pinned_process_panels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    process_id INTEGER NOT NULL,
                    x_position INTEGER NOT NULL,
                    y_position INTEGER NOT NULL,
                    width INTEGER NOT NULL DEFAULT 500,
                    height INTEGER NOT NULL DEFAULT 600,
                    is_minimized BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_opened TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    open_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (process_id) REFERENCES processes(id) ON DELETE CASCADE
                );

                -- Tabla de historial de ejecución de procesos
                CREATE TABLE IF NOT EXISTS process_execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    process_id INTEGER NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration_ms INTEGER,
                    status TEXT DEFAULT 'running',
                    total_steps INTEGER,
                    completed_steps INTEGER DEFAULT 0,
                    failed_steps INTEGER DEFAULT 0,
                    error_message TEXT,
                    failed_step_id INTEGER,
                    FOREIGN KEY (process_id) REFERENCES processes(id) ON DELETE CASCADE
                );

                -- Tabla de configuración del navegador embebido
                CREATE TABLE IF NOT EXISTS browser_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    home_url TEXT DEFAULT 'https://www.google.com',
                    is_visible BOOLEAN DEFAULT 0,
                    width INTEGER DEFAULT 500,
                    height INTEGER DEFAULT 700,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Tabla de configuración de paneles (dimensiones y posición)
                CREATE TABLE IF NOT EXISTS panel_settings (
                    panel_name TEXT PRIMARY KEY,
                    width INTEGER NOT NULL DEFAULT 380,
                    height INTEGER NOT NULL DEFAULT 500,
                    pos_x INTEGER,
                    pos_y INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Tabla de perfiles de navegador
                CREATE TABLE IF NOT EXISTS browser_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    storage_path TEXT NOT NULL,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Tabla de sesiones de navegador
                CREATE TABLE IF NOT EXISTS browser_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    is_auto_save BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Tabla de pestañas de sesiones
                CREATE TABLE IF NOT EXISTS session_tabs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT DEFAULT 'Nueva pestaña',
                    position INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES browser_sessions(id) ON DELETE CASCADE
                );

                -- Tabla de marcadores del navegador
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    folder TEXT DEFAULT NULL,
                    icon TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_index INTEGER DEFAULT 0
                );

                -- Tabla de Speed Dial
                CREATE TABLE IF NOT EXISTS speed_dials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    thumbnail_path TEXT DEFAULT NULL,
                    background_color TEXT DEFAULT '#16213e',
                    icon TEXT DEFAULT '🌐',
                    position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Tabla de tipos de componentes
                CREATE TABLE IF NOT EXISTS component_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    description TEXT,
                    default_config TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Tabla de historial de búsqueda
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    search_mode TEXT NOT NULL CHECK(search_mode IN ('smart', 'fts5', 'fuzzy', 'exact')),
                    filters TEXT,
                    result_count INTEGER DEFAULT 0,
                    execution_time_ms REAL DEFAULT 0.0,
                    search_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                -- Tabla de estadísticas de búsqueda
                CREATE TABLE IF NOT EXISTS search_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL UNIQUE,
                    search_count INTEGER DEFAULT 1,
                    last_searched DATETIME DEFAULT CURRENT_TIMESTAMP,
                    avg_result_count REAL DEFAULT 0.0,
                    avg_execution_time_ms REAL DEFAULT 0.0
                );

                -- Tabla de colecciones inteligentes
                CREATE TABLE IF NOT EXISTS smart_collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    query_config TEXT NOT NULL,
                    icon TEXT DEFAULT '📂',
                    color TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    auto_update BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Tabla de items en colecciones inteligentes
                CREATE TABLE IF NOT EXISTS smart_collection_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    relevance_score REAL DEFAULT 1.0,
                    FOREIGN KEY (collection_id) REFERENCES smart_collections(id) ON DELETE CASCADE,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
                    UNIQUE(collection_id, item_id)
                );

                -- Tabla de sesiones de usuario
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id TEXT DEFAULT 'default_user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_valid BOOLEAN DEFAULT 1
                );

                -- Tabla de pestañas del notebook
                CREATE TABLE IF NOT EXISTS notebook_tabs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT,
                    category_id INTEGER,
                    item_type TEXT,
                    tags TEXT,
                    description TEXT,
                    is_sensitive BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    is_archived BOOLEAN DEFAULT 0,
                    position INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                );

                -- Tabla de grupos de tags
                CREATE TABLE IF NOT EXISTS tag_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    tags TEXT,
                    color TEXT,
                    icon TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                );

                -- ÍNDICES para optimización
                CREATE INDEX IF NOT EXISTS idx_categories_order ON categories(order_index);
                CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);
                CREATE INDEX IF NOT EXISTS idx_items_last_used ON items(last_used DESC);
                CREATE INDEX IF NOT EXISTS idx_items_favorite ON items(is_favorite) WHERE is_favorite = 1;
                CREATE INDEX IF NOT EXISTS idx_clipboard_history_date ON clipboard_history(copied_at DESC);
                CREATE INDEX IF NOT EXISTS idx_pinned_category ON pinned_panels(category_id);
                CREATE INDEX IF NOT EXISTS idx_pinned_last_opened ON pinned_panels(last_opened DESC);
                CREATE INDEX IF NOT EXISTS idx_pinned_active ON pinned_panels(is_active);
                CREATE INDEX IF NOT EXISTS idx_bookmarks_order ON bookmarks(order_index);
                CREATE INDEX IF NOT EXISTS idx_bookmarks_url ON bookmarks(url);
                CREATE INDEX IF NOT EXISTS idx_speed_dials_position ON speed_dials(position);
                CREATE INDEX IF NOT EXISTS idx_items_is_list ON items(is_list) WHERE is_list = 1;
                CREATE INDEX IF NOT EXISTS idx_items_list_group ON items(list_group) WHERE list_group IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_items_orden_lista ON items(category_id, list_group, orden_lista) WHERE is_list = 1;
                CREATE INDEX IF NOT EXISTS idx_processes_active ON processes(is_active) WHERE is_active = 1;
                CREATE INDEX IF NOT EXISTS idx_processes_pinned ON processes(is_pinned, pinned_order);
                CREATE INDEX IF NOT EXISTS idx_process_items_order ON process_items(process_id, step_order);
                CREATE INDEX IF NOT EXISTS idx_item_usage_history ON item_usage_history(item_id, used_at DESC);
                CREATE INDEX IF NOT EXISTS idx_sessions_valid ON sessions(is_valid, expires_at);
                CREATE INDEX IF NOT EXISTS idx_notebook_tabs_category ON notebook_tabs(category_id);
                CREATE INDEX IF NOT EXISTS idx_notebook_tabs_position ON notebook_tabs(position);
                CREATE INDEX IF NOT EXISTS idx_notebook_tabs_updated ON notebook_tabs(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_tag_groups_active ON tag_groups(is_active) WHERE is_active = 1;
                CREATE INDEX IF NOT EXISTS idx_tag_groups_name ON tag_groups(name);

                -- Configuración inicial por defecto
                INSERT OR IGNORE INTO settings (key, value) VALUES
                    ('theme', '"dark"'),
                    ('panel_width', '300'),
                    ('sidebar_width', '70'),
                    ('hotkey', '"ctrl+shift+v"'),
                    ('always_on_top', 'true'),
                    ('start_with_windows', 'false'),
                    ('animation_speed', '300'),
                    ('opacity', '0.95'),
                    ('max_history', '20');
            """)

        conn.commit()
        # Don't close the connection - it's managed by self.connection
        logger.info("Database schema created successfully with COMPLETE SCHEMA")

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """
        Execute SELECT query and return results as list of dictionaries

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            List[Dict]: Query results
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute INSERT/UPDATE/DELETE query

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            int: Last row ID for INSERT, or number of affected rows
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Update execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """
        Execute multiple INSERT queries in a single transaction

        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
            logger.info(f"Batch execution completed: {len(params_list)} rows")
        except sqlite3.Error as e:
            logger.error(f"Batch execution failed: {e}")
            raise

    # ========== SETTINGS ==========

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get configuration setting by key

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Any: Setting value (parsed from JSON)
        """
        query = "SELECT value FROM settings WHERE key = ?"
        result = self.execute_query(query, (key,))
        if result:
            try:
                return json.loads(result[0]['value'])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse setting '{key}': {e}")
                return default
        return default

    def set_setting(self, key: str, value: Any) -> None:
        """
        Save or update configuration setting

        Args:
            key: Setting key
            value: Setting value (will be JSON encoded)
        """
        value_json = json.dumps(value)
        query = """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """
        self.execute_update(query, (key, value_json))
        logger.debug(f"Setting saved: {key} = {value}")

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all configuration settings

        Returns:
            Dict[str, Any]: Dictionary of all settings
        """
        query = "SELECT key, value FROM settings"
        results = self.execute_query(query)
        settings = {}
        for row in results:
            try:
                settings[row['key']] = json.loads(row['value'])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse setting '{row['key']}': {e}")
        return settings

    # ========== CATEGORIES ==========

    def get_categories(self, include_inactive: bool = False) -> List[Dict]:
        """
        Get all categories ordered by order_index

        Args:
            include_inactive: Include inactive categories

        Returns:
            List[Dict]: List of category dictionaries
        """
        query = """
            SELECT * FROM categories
            WHERE is_active = 1 OR ? = 1
            ORDER BY order_index
        """
        return self.execute_query(query, (include_inactive,))

    def get_category(self, category_id: int) -> Optional[Dict]:
        """
        Get category by ID

        Args:
            category_id: Category ID

        Returns:
            Optional[Dict]: Category dictionary or None
        """
        query = "SELECT * FROM categories WHERE id = ?"
        result = self.execute_query(query, (category_id,))
        return result[0] if result else None

    def add_category(self, name: str, icon: str = None,
                     is_predefined: bool = False, order_index: int = None) -> int:
        """
        Add new category

        Args:
            name: Category name
            icon: Category icon (optional)
            is_predefined: Whether this is a predefined category
            order_index: Order index (optional, will auto-calculate if None)

        Returns:
            int: New category ID
        """
        # Use provided order_index or calculate next one
        if order_index is None:
            max_order = self.execute_query(
                "SELECT MAX(order_index) as max_order FROM categories"
            )
            order_index = (max_order[0]['max_order'] or 0) + 1

        query = """
            INSERT INTO categories (name, icon, order_index, is_predefined, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        category_id = self.execute_update(query, (name, icon, order_index, is_predefined))
        logger.info(f"Category added: {name} (ID: {category_id}, order_index: {order_index})")
        return category_id

    def update_category(self, category_id: int, name: str = None,
                        icon: str = None, order_index: int = None,
                        is_active: bool = None) -> None:
        """
        Update category fields

        Args:
            category_id: Category ID to update
            name: New name (optional)
            icon: New icon (optional)
            order_index: New order (optional)
            is_active: New active status (optional)
        """
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if icon is not None:
            updates.append("icon = ?")
            params.append(icon)
        if order_index is not None:
            updates.append("order_index = ?")
            params.append(order_index)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(category_id)
            query = f"UPDATE categories SET {', '.join(updates)} WHERE id = ?"
            self.execute_update(query, tuple(params))
            logger.info(f"Category updated: ID {category_id}")

    def delete_category(self, category_id: int) -> None:
        """
        Delete category (cascade deletes all items)

        Args:
            category_id: Category ID to delete
        """
        query = "DELETE FROM categories WHERE id = ?"
        self.execute_update(query, (category_id,))
        logger.info(f"Category deleted: ID {category_id}")

    def reorder_categories(self, category_ids: List[int]) -> None:
        """
        Reorder categories by providing ordered list of IDs

        Args:
            category_ids: List of category IDs in desired order
        """
        updates = [(i, cat_id) for i, cat_id in enumerate(category_ids)]
        query = "UPDATE categories SET order_index = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute_many(query, updates)
        logger.info(f"Categories reordered: {len(category_ids)} items")

    # ========== ITEMS ==========

    def get_items_by_category(self, category_id: int) -> List[Dict]:
        """
        Get all items for a specific category

        Args:
            category_id: Category ID

        Returns:
            List[Dict]: List of item dictionaries (content decrypted if sensitive)
        """
        query = """
            SELECT * FROM items
            WHERE category_id = ?
            ORDER BY created_at
        """
        results = self.execute_query(query, (category_id,))

        # Initialize encryption manager for decrypting sensitive items
        from core.encryption_manager import EncryptionManager
        encryption_manager = EncryptionManager()

        # Parse tags and decrypt sensitive content
        for item in results:
            # Parse tags from JSON or CSV format
            if item['tags']:
                try:
                    # Try to parse as JSON first
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, try CSV format (legacy)
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content
            if item.get('is_sensitive') and item.get('content'):
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item ID: {item['id']}")
                except Exception as e:
                    logger.error(f"Failed to decrypt item {item['id']}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

        return results

    def get_item(self, item_id: int) -> Optional[Dict]:
        """
        Get item by ID

        Args:
            item_id: Item ID

        Returns:
            Optional[Dict]: Item dictionary or None (content decrypted if sensitive)
        """
        query = "SELECT * FROM items WHERE id = ?"
        result = self.execute_query(query, (item_id,))
        if result:
            item = result[0]
            # Parse tags from JSON or CSV format
            if item['tags']:
                try:
                    # Try to parse as JSON first
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, try CSV format (legacy)
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content
            if item.get('is_sensitive') and item.get('content'):
                from core.encryption_manager import EncryptionManager
                encryption_manager = EncryptionManager()
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item ID: {item_id}")
                except Exception as e:
                    logger.error(f"Failed to decrypt item {item_id}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

            return item
        return None

    def get_item_by_hash(self, file_hash: str) -> Optional[Dict]:
        """
        Get item by file hash (for duplicate detection)

        Args:
            file_hash: SHA256 hash of the file

        Returns:
            Optional[Dict]: Item dictionary or None if not found
        """
        query = "SELECT * FROM items WHERE file_hash = ? LIMIT 1"
        result = self.execute_query(query, (file_hash,))
        if result:
            item = result[0]
            # Parse tags
            if item['tags']:
                try:
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content if needed
            if item.get('is_sensitive') and item.get('content'):
                from core.encryption_manager import EncryptionManager
                encryption_manager = EncryptionManager()
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item with hash: {file_hash[:16]}...")
                except Exception as e:
                    logger.error(f"Failed to decrypt item with hash {file_hash[:16]}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

            return item
        return None

    def get_all_items(self, active_only: bool = False, include_archived: bool = True) -> List[Dict]:
        """
        Get all items from all categories

        Args:
            active_only: If True, only return active items (default: False)
            include_archived: If True, include archived items (default: True)

        Returns:
            List[Dict]: List of all item dictionaries (content decrypted if sensitive)
        """
        # Build query based on filters
        conditions = []
        params = []

        if active_only:
            conditions.append("is_active = ?")
            params.append(1)

        if not include_archived:
            conditions.append("is_archived = ?")
            params.append(0)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT * FROM items
            {where_clause}
            ORDER BY last_used DESC, created_at DESC
        """

        results = self.execute_query(query, tuple(params)) if params else self.execute_query(query)

        # Initialize encryption manager for decrypting sensitive items
        from core.encryption_manager import EncryptionManager
        encryption_manager = EncryptionManager()

        # Parse tags and decrypt sensitive content
        for item in results:
            # Parse tags from JSON or CSV format
            if item['tags']:
                try:
                    # Try to parse as JSON first
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, try CSV format (legacy)
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content
            if item.get('is_sensitive') and item.get('content'):
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item ID: {item['id']}")
                except Exception as e:
                    logger.error(f"Failed to decrypt item {item['id']}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

        logger.debug(f"Retrieved {len(results)} items")
        return results

    def add_item(self, category_id: int, label: str, content: str,
                 item_type: str = 'TEXT', icon: str = None,
                 is_sensitive: bool = False, is_favorite: bool = False,
                 tags: List[str] = None, description: str = None,
                 working_dir: str = None, color: str = None,
                 badge: str = None,
                 is_active: bool = True, is_archived: bool = False,
                 is_list: bool = False, list_group: str = None,
                 orden_lista: int = 0,
                 # Component fields
                 is_component: bool = False,
                 name_component: str = None,
                 component_config: Dict[str, Any] = None,
                 # File metadata fields (for TYPE PATH)
                 file_size: int = None,
                 file_type: str = None,
                 file_extension: str = None,
                 original_filename: str = None,
                 file_hash: str = None) -> int:
        """
        Add new item to category

        Args:
            category_id: Category ID
            label: Item label
            content: Item content (will be encrypted if is_sensitive=True)
            item_type: Item type (TEXT, URL, CODE, PATH)
            icon: Item icon (optional)
            is_sensitive: Whether content is sensitive (will encrypt content)
            is_favorite: Whether item is marked as favorite
            tags: List of tags (optional)
            description: Item description (optional)
            working_dir: Working directory for CODE items (optional)
            color: Item color for visual identification (optional)
            badge: Item badge text (optional)
            is_active: Whether item is active (default True)
            is_archived: Whether item is archived (default False)
            is_list: Whether item is part of a list (default False)
            list_group: Name/identifier of the list group (optional)
            orden_lista: Position of item within the list (default 0)
            file_size: File size in bytes (for PATH items, optional)
            file_type: File type category (IMAGEN, VIDEO, PDF, etc., optional)
            file_extension: File extension with dot (.jpg, .mp4, optional)
            original_filename: Original filename (optional)
            file_hash: SHA256 hash for duplicate detection (optional)

        Returns:
            int: New item ID
        """
        # Encrypt content if sensitive
        if is_sensitive and content:
            from core.encryption_manager import EncryptionManager
            encryption_manager = EncryptionManager()
            content = encryption_manager.encrypt(content)
            logger.info(f"Content encrypted for sensitive item: {label}")

        tags_json = json.dumps(tags or [])
        component_config_json = json.dumps(component_config or {})

        query = """
            INSERT INTO items
            (category_id, label, content, type, icon, is_sensitive, is_favorite, tags, description, working_dir, color, badge, is_active, is_archived, is_list, list_group, orden_lista, is_component, name_component, component_config, file_size, file_type, file_extension, original_filename, file_hash, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        item_id = self.execute_update(
            query,
            (category_id, label, content, item_type, icon, is_sensitive, is_favorite, tags_json, description, working_dir, color, badge, is_active, is_archived, is_list, list_group, orden_lista, is_component, name_component, component_config_json, file_size, file_type, file_extension, original_filename, file_hash)
        )
        list_info = f", List: {list_group}[{orden_lista}]" if is_list else ""
        logger.info(f"Item added: {label} (ID: {item_id}, Sensitive: {is_sensitive}, Favorite: {is_favorite}, Active: {is_active}, Archived: {is_archived}{list_info})")
        return item_id

    def update_item(self, item_id: int, **kwargs) -> None:
        """
        Update item fields

        Args:
            item_id: Item ID to update
            **kwargs: Fields to update (label, content, type, icon, is_sensitive, is_favorite, tags, description, working_dir, color, badge, is_active, is_archived, is_list, list_group, orden_lista, file_size, file_type, file_extension, original_filename, file_hash)
        """
        allowed_fields = ['label', 'content', 'type', 'icon', 'is_sensitive', 'is_favorite', 'tags', 'description', 'working_dir', 'color', 'badge', 'is_active', 'is_archived', 'is_list', 'list_group', 'orden_lista', 'file_size', 'file_type', 'file_extension', 'original_filename', 'file_hash']
        updates = []
        params = []

        # Get current item to check if it's sensitive
        current_item = self.get_item(item_id)
        if not current_item:
            logger.warning(f"Item not found for update: ID {item_id}")
            return

        # Check if item is being marked as sensitive or if it's already sensitive
        is_currently_sensitive = current_item.get('is_sensitive', False)
        will_be_sensitive = kwargs.get('is_sensitive', is_currently_sensitive)

        for field, value in kwargs.items():
            if field in allowed_fields:
                # Handle tags serialization
                if field == 'tags':
                    value = json.dumps(value)
                # Handle content encryption for sensitive items
                elif field == 'content' and will_be_sensitive and value:
                    from core.encryption_manager import EncryptionManager
                    encryption_manager = EncryptionManager()
                    # Only encrypt if not already encrypted
                    if not encryption_manager.is_encrypted(value):
                        value = encryption_manager.encrypt(value)
                        logger.info(f"Content encrypted for item ID: {item_id}")

                updates.append(f"{field} = ?")
                params.append(value)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(item_id)
            query = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
            self.execute_update(query, tuple(params))
            logger.info(f"Item updated: ID {item_id}")

    def delete_item(self, item_id: int) -> None:
        """
        Delete item

        Args:
            item_id: Item ID to delete
        """
        query = "DELETE FROM items WHERE id = ?"
        self.execute_update(query, (item_id,))
        logger.info(f"Item deleted: ID {item_id}")

    def update_last_used(self, item_id: int) -> None:
        """
        Update item's last_used timestamp

        Args:
            item_id: Item ID
        """
        query = "UPDATE items SET last_used = CURRENT_TIMESTAMP WHERE id = ?"
        self.execute_update(query, (item_id,))
        logger.debug(f"Last used updated: ID {item_id}")

    def get_all_items(self, include_inactive: bool = False) -> List[Dict]:
        """
        Get ALL items from ALL categories with category info

        Args:
            include_inactive: Include items from inactive categories

        Returns:
            List[Dict]: List of all items with category_name, category_icon, category_color
        """
        query = """
            SELECT
                i.*,
                c.name as category_name,
                c.icon as category_icon,
                c.color as category_color,
                c.id as category_id
            FROM items i
            JOIN categories c ON i.category_id = c.id
            WHERE c.is_active = 1 OR ? = 1
            ORDER BY i.created_at DESC
        """
        results = self.execute_query(query, (include_inactive,))

        # Initialize encryption manager for decrypting sensitive items
        from core.encryption_manager import EncryptionManager
        encryption_manager = EncryptionManager()

        # Parse tags and decrypt sensitive content
        for item in results:
            # Parse tags from JSON or CSV format
            if item['tags']:
                try:
                    # Try to parse as JSON first
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, try CSV format (legacy)
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content
            if item.get('is_sensitive') and item.get('content'):
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item ID: {item['id']}")
                except Exception as e:
                    logger.error(f"Failed to decrypt item {item['id']}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

        return results

    def search_items(self, search_query: str, limit: int = 50) -> List[Dict]:
        """
        Search items by label or content

        Args:
            search_query: Search text
            limit: Maximum results

        Returns:
            List[Dict]: List of matching items with category name
        """
        query = """
            SELECT i.*, c.name as category_name
            FROM items i
            JOIN categories c ON i.category_id = c.id
            WHERE i.label LIKE ? OR i.content LIKE ? OR i.tags LIKE ?
            ORDER BY i.last_used DESC
            LIMIT ?
        """
        search_pattern = f"%{search_query}%"
        results = self.execute_query(
            query,
            (search_pattern, search_pattern, search_pattern, limit)
        )

        # Parse tags
        for item in results:
            if item['tags']:
                try:
                    # Try to parse as JSON first
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    # If JSON parsing fails, try CSV format (legacy)
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

        return results

    # ========== LISTAS AVANZADAS ==========

    def create_list(self, category_id: int, list_name: str, items_data: List[Dict[str, Any]]) -> List[int]:
        """
        Crea una lista completa con múltiples items

        Args:
            category_id: ID de la categoría
            list_name: Nombre de la lista (list_group)
            items_data: Lista de dicts con datos de cada paso
                [
                    {'label': 'Paso 1', 'content': '...', 'type': 'TEXT'},
                    {'label': 'Paso 2', 'content': '...', 'type': 'CODE'},
                ]

        Returns:
            List[int]: Lista de IDs de los items creados
        """
        if not items_data or len(items_data) < 1:
            raise ValueError("La lista debe tener al menos 1 item")

        # Validar que el nombre de lista sea único
        if not self.is_list_name_unique(category_id, list_name):
            raise ValueError(f"El nombre de lista '{list_name}' ya existe en esta categoría")

        item_ids = []

        try:
            with self.transaction() as conn:
                for orden, item_data in enumerate(items_data, start=1):
                    # Agregar item con campos de lista
                    item_id = self.add_item(
                        category_id=category_id,
                        label=item_data.get('label', f'Paso {orden}'),
                        content=item_data.get('content', ''),
                        item_type=item_data.get('type', 'TEXT'),
                        icon=item_data.get('icon'),
                        is_sensitive=item_data.get('is_sensitive', False),
                        tags=item_data.get('tags'),
                        description=item_data.get('description'),
                        working_dir=item_data.get('working_dir'),
                        color=item_data.get('color'),
                        # Campos de lista
                        is_list=True,
                        list_group=list_name,
                        orden_lista=orden
                    )
                    item_ids.append(item_id)

                logger.info(f"Lista creada: '{list_name}' con {len(item_ids)} items en categoría {category_id}")

            return item_ids

        except Exception as e:
            logger.error(f"Error al crear lista '{list_name}': {e}")
            raise

    def get_lists_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene resumen de todas las listas en una categoría

        Args:
            category_id: ID de la categoría

        Returns:
            List[Dict]: Lista de diccionarios con info de cada lista
                [
                    {
                        'list_group': 'Deploy Producción',
                        'item_count': 5,
                        'first_label': 'Pull cambios',
                        'created_at': '2025-10-31 10:00:00'
                    },
                    ...
                ]
        """
        query = """
            SELECT
                list_group,
                COUNT(*) as item_count,
                MIN(label) as first_label,
                MIN(created_at) as created_at,
                MAX(last_used) as last_used
            FROM items
            WHERE category_id = ?
            AND is_list = 1
            AND is_active = 1
            GROUP BY list_group
            ORDER BY created_at DESC
        """
        results = self.execute_query(query, (category_id,))
        logger.debug(f"Encontradas {len(results)} listas en categoría {category_id}")
        return results

    def get_list_items(self, category_id: int, list_group: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los items de una lista específica, ordenados por orden_lista

        Args:
            category_id: ID de la categoría
            list_group: Nombre de la lista

        Returns:
            List[Dict]: Lista de items ordenados (con contenido desencriptado si es sensible)
        """
        query = """
            SELECT * FROM items
            WHERE category_id = ?
            AND is_list = 1
            AND list_group = ?
            AND is_active = 1
            ORDER BY orden_lista ASC
        """
        results = self.execute_query(query, (category_id, list_group))

        # Desencriptar y parsear tags (mismo proceso que en get_items_by_category)
        from core.encryption_manager import EncryptionManager
        encryption_manager = EncryptionManager()

        for item in results:
            # Parse tags
            if item['tags']:
                try:
                    item['tags'] = json.loads(item['tags'])
                except json.JSONDecodeError:
                    if isinstance(item['tags'], str):
                        item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                    else:
                        item['tags'] = []
            else:
                item['tags'] = []

            # Decrypt sensitive content
            if item.get('is_sensitive') and item.get('content'):
                try:
                    item['content'] = encryption_manager.decrypt(item['content'])
                    logger.debug(f"Content decrypted for item ID: {item['id']}")
                except Exception as e:
                    logger.error(f"Failed to decrypt item {item['id']}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"

        logger.debug(f"Obtenidos {len(results)} items de lista '{list_group}'")
        return results

    def reorder_list_item(self, item_id: int, new_orden: int) -> bool:
        """
        Cambia el orden de un item dentro de su lista
        También reordena los demás items afectados

        Args:
            item_id: ID del item a reordenar
            new_orden: Nueva posición (1, 2, 3...)

        Returns:
            bool: True si se reordenó exitosamente
        """
        # Obtener info del item
        item = self.get_item(item_id)
        if not item or not item.get('is_list'):
            logger.warning(f"Item {item_id} no encontrado o no es parte de una lista")
            return False

        category_id = item['category_id']
        list_group = item['list_group']
        old_orden = item['orden_lista']

        if old_orden == new_orden:
            logger.debug(f"Item {item_id} ya está en la posición {new_orden}")
            return True

        try:
            with self.transaction() as conn:
                cursor = conn.cursor()

                # Si movemos hacia arriba (new_orden < old_orden)
                # Incrementar orden de los items entre new_orden y old_orden
                if new_orden < old_orden:
                    cursor.execute("""
                        UPDATE items
                        SET orden_lista = orden_lista + 1
                        WHERE category_id = ?
                        AND list_group = ?
                        AND orden_lista >= ?
                        AND orden_lista < ?
                    """, (category_id, list_group, new_orden, old_orden))

                # Si movemos hacia abajo (new_orden > old_orden)
                # Decrementar orden de los items entre old_orden y new_orden
                else:
                    cursor.execute("""
                        UPDATE items
                        SET orden_lista = orden_lista - 1
                        WHERE category_id = ?
                        AND list_group = ?
                        AND orden_lista > ?
                        AND orden_lista <= ?
                    """, (category_id, list_group, old_orden, new_orden))

                # Actualizar el item movido
                cursor.execute("""
                    UPDATE items
                    SET orden_lista = ?
                    WHERE id = ?
                """, (new_orden, item_id))

                logger.info(f"Item {item_id} reordenado de posición {old_orden} a {new_orden} en lista '{list_group}'")
                return True

        except Exception as e:
            logger.error(f"Error al reordenar item {item_id}: {e}")
            return False

    def delete_list(self, category_id: int, list_group: str) -> bool:
        """
        Elimina TODOS los items de una lista

        Args:
            category_id: ID de la categoría
            list_group: Nombre de la lista a eliminar

        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            query = """
                DELETE FROM items
                WHERE category_id = ?
                AND list_group = ?
                AND is_list = 1
            """
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (category_id, list_group))
                deleted_count = cursor.rowcount

                logger.info(f"Lista '{list_group}' eliminada ({deleted_count} items) de categoría {category_id}")
                return True

        except Exception as e:
            logger.error(f"Error al eliminar lista '{list_group}': {e}")
            return False

    def update_list(self, category_id: int, old_list_group: str,
                   new_list_group: str = None, items_data: List[Dict[str, Any]] = None) -> bool:
        """
        Actualiza una lista existente

        Permite:
        - Renombrar la lista (cambiar list_group)
        - Actualizar los items de la lista (agregar/eliminar/modificar pasos)

        Args:
            category_id: ID de la categoría
            old_list_group: Nombre actual de la lista
            new_list_group: Nuevo nombre (opcional, si se quiere renombrar)
            items_data: Nuevos datos de items (opcional, si se quiere actualizar contenido)

        Returns:
            bool: True si se actualizó exitosamente
        """
        try:
            with self.transaction() as conn:
                # Caso 1: Solo renombrar
                if new_list_group and new_list_group != old_list_group:
                    # Validar que el nuevo nombre sea único
                    if not self.is_list_name_unique(category_id, new_list_group, exclude_list=old_list_group):
                        raise ValueError(f"El nombre '{new_list_group}' ya existe en esta categoría")

                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE items
                        SET list_group = ?
                        WHERE category_id = ?
                        AND list_group = ?
                        AND is_list = 1
                    """, (new_list_group, category_id, old_list_group))

                    logger.info(f"Lista renombrada: '{old_list_group}' → '{new_list_group}'")

                # Caso 2: Actualizar items de la lista
                if items_data is not None:
                    # Eliminar items actuales
                    final_list_name = new_list_group if new_list_group else old_list_group
                    self.delete_list(category_id, final_list_name)

                    # Crear nuevos items
                    self.create_list(category_id, final_list_name, items_data)

                    logger.info(f"Lista '{final_list_name}' actualizada con {len(items_data)} items")

                return True

        except Exception as e:
            logger.error(f"Error al actualizar lista '{old_list_group}': {e}")
            return False

    def is_list_name_unique(self, category_id: int, list_name: str, exclude_list: str = None) -> bool:
        """
        Verifica si el nombre de lista es único en la categoría

        Args:
            category_id: ID de la categoría
            list_name: Nombre de lista a verificar
            exclude_list: Nombre de lista a excluir (útil para edición)

        Returns:
            bool: True si el nombre es único, False si ya existe
        """
        if exclude_list:
            query = """
                SELECT COUNT(*) as count
                FROM items
                WHERE category_id = ?
                AND list_group = ?
                AND is_list = 1
                AND list_group != ?
            """
            result = self.execute_query(query, (category_id, list_name, exclude_list))
        else:
            query = """
                SELECT COUNT(*) as count
                FROM items
                WHERE category_id = ?
                AND list_group = ?
                AND is_list = 1
            """
            result = self.execute_query(query, (category_id, list_name))

        count = result[0]['count'] if result else 0
        is_unique = count == 0

        logger.debug(f"Nombre de lista '{list_name}' en categoría {category_id}: {'único' if is_unique else 'ya existe'}")
        return is_unique

    # ========== CLIPBOARD HISTORY ==========

    def add_to_history(self, item_id: Optional[int], content: str) -> int:
        """
        Add entry to clipboard history

        Args:
            item_id: Associated item ID (optional)
            content: Copied content

        Returns:
            int: History entry ID
        """
        query = """
            INSERT INTO clipboard_history (item_id, content)
            VALUES (?, ?)
        """
        history_id = self.execute_update(query, (item_id, content))
        logger.debug(f"History entry added: ID {history_id}")

        # Auto-trim history to max_history setting
        max_history = self.get_setting('max_history', 20)
        self.trim_history(keep_latest=max_history)

        return history_id

    def get_history(self, limit: int = 20) -> List[Dict]:
        """
        Get recent clipboard history

        Args:
            limit: Maximum entries to retrieve

        Returns:
            List[Dict]: List of history entries
        """
        query = """
            SELECT h.*, i.label, i.type
            FROM clipboard_history h
            LEFT JOIN items i ON h.item_id = i.id
            ORDER BY h.copied_at DESC
            LIMIT ?
        """
        return self.execute_query(query, (limit,))

    def clear_history(self) -> None:
        """Clear all clipboard history"""
        query = "DELETE FROM clipboard_history"
        self.execute_update(query)
        logger.info("Clipboard history cleared")

    def trim_history(self, keep_latest: int = 20) -> None:
        """
        Keep only the latest N history entries

        Args:
            keep_latest: Number of entries to keep
        """
        query = """
            DELETE FROM clipboard_history
            WHERE id NOT IN (
                SELECT id FROM clipboard_history
                ORDER BY copied_at DESC
                LIMIT ?
            )
        """
        self.execute_update(query, (keep_latest,))
        logger.debug(f"History trimmed to {keep_latest} entries")

    # ========== PINNED PANELS ==========

    def save_pinned_panel(self, category_id: int = None, x_pos: int = 0, y_pos: int = 0,
                         width: int = 350, height: int = 500, is_minimized: bool = False,
                         custom_name: str = None, custom_color: str = None,
                         filter_config: str = None, keyboard_shortcut: str = None,
                         panel_type: str = 'category', search_query: str = None,
                         advanced_filters: str = None, state_filter: str = 'normal') -> int:
        """
        Save a pinned panel configuration to database

        Args:
            category_id: Category ID for category panels (None for global_search)
            x_pos: X position on screen
            y_pos: Y position on screen
            width: Panel width
            height: Panel height
            is_minimized: Whether panel is minimized
            custom_name: Custom name for panel (optional)
            custom_color: Custom header color (optional, hex format)
            filter_config: Filter configuration as JSON string (optional)
            keyboard_shortcut: Keyboard shortcut string like 'Ctrl+Shift+1' (optional)
            panel_type: Panel type ('category' or 'global_search')
            search_query: Search query text for global_search panels (optional)
            advanced_filters: Advanced filters as JSON string (optional)
            state_filter: State filter ('normal', 'archived', 'inactive', 'all')

        Returns:
            int: New panel ID
        """
        query = """
            INSERT INTO pinned_panels
            (category_id, x_position, y_position, width, height, is_minimized,
             custom_name, custom_color, filter_config, keyboard_shortcut,
             panel_type, search_query, advanced_filters, state_filter, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """
        panel_id = self.execute_update(
            query,
            (category_id, x_pos, y_pos, width, height, is_minimized, custom_name,
             custom_color, filter_config, keyboard_shortcut, panel_type, search_query,
             advanced_filters, state_filter)
        )
        logger.info(f"Pinned panel saved: Type={panel_type}, Category={category_id}, Query='{search_query}' (ID: {panel_id})")
        return panel_id

    def get_pinned_panels(self, active_only: bool = True) -> List[Dict]:
        """
        Retrieve all pinned panels

        Args:
            active_only: Only return panels marked as active

        Returns:
            List[Dict]: List of panel dictionaries with category info
        """
        if active_only:
            query = """
                SELECT p.*, c.name as category_name, c.icon as category_icon
                FROM pinned_panels p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = 1
                ORDER BY p.last_opened DESC
            """
            panels = self.execute_query(query)
        else:
            query = """
                SELECT p.*, c.name as category_name, c.icon as category_icon
                FROM pinned_panels p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.last_opened DESC
            """
            panels = self.execute_query(query)
        logger.debug(f"Retrieved {len(panels)} pinned panels (active_only={active_only})")
        return panels

    def get_panel_by_id(self, panel_id: int) -> Optional[Dict]:
        """
        Get specific panel by ID

        Args:
            panel_id: Panel ID

        Returns:
            Optional[Dict]: Panel dictionary with category info, or None
        """
        query = """
            SELECT p.*, c.name as category_name, c.icon as category_icon
            FROM pinned_panels p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = ?
        """
        result = self.execute_query(query, (panel_id,))
        return result[0] if result else None

    def update_pinned_panel(self, panel_id: int, **kwargs) -> bool:
        """
        Update panel configuration

        Args:
            panel_id: Panel ID to update
            **kwargs: Fields to update (x_position, y_position, width, height,
                     is_minimized, custom_name, custom_color, filter_config,
                     keyboard_shortcut, panel_type, search_query, advanced_filters,
                     state_filter, is_active)

        Returns:
            bool: True if update successful
        """
        allowed_fields = [
            'x_position', 'y_position', 'width', 'height', 'is_minimized',
            'custom_name', 'custom_color', 'filter_config', 'keyboard_shortcut',
            'panel_type', 'search_query', 'advanced_filters', 'state_filter', 'is_active'
        ]
        updates = []
        params = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                params.append(value)

        if updates:
            params.append(panel_id)
            query = f"UPDATE pinned_panels SET {', '.join(updates)} WHERE id = ?"
            self.execute_update(query, tuple(params))
            logger.info(f"Pinned panel updated: ID {panel_id}")
            return True
        return False

    def update_panel_last_opened(self, panel_id: int) -> None:
        """
        Update last_opened timestamp and increment open_count

        Args:
            panel_id: Panel ID
        """
        query = """
            UPDATE pinned_panels
            SET last_opened = CURRENT_TIMESTAMP,
                open_count = open_count + 1
            WHERE id = ?
        """
        self.execute_update(query, (panel_id,))
        logger.debug(f"Panel {panel_id} opened - statistics updated")

    def delete_pinned_panel(self, panel_id: int) -> bool:
        """
        Remove a pinned panel from database

        Args:
            panel_id: Panel ID to delete

        Returns:
            bool: True if deletion successful
        """
        query = "DELETE FROM pinned_panels WHERE id = ?"
        self.execute_update(query, (panel_id,))
        logger.info(f"Pinned panel deleted: ID {panel_id}")
        return True

    def get_recent_panels(self, limit: int = 10) -> List[Dict]:
        """
        Get recently opened panels ordered by last_opened DESC

        Args:
            limit: Maximum number of panels to return

        Returns:
            List[Dict]: List of panel dictionaries with category info
        """
        query = """
            SELECT p.*, c.name as category_name, c.icon as category_icon
            FROM pinned_panels p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.last_opened DESC
            LIMIT ?
        """
        panels = self.execute_query(query, (limit,))
        logger.debug(f"Retrieved {len(panels)} recent panels")
        return panels

    def deactivate_all_panels(self) -> None:
        """
        Set is_active=0 for all panels (called on app shutdown)
        """
        query = "UPDATE pinned_panels SET is_active = 0"
        self.execute_update(query)
        logger.info("All pinned panels marked as inactive")

    # ========== PINNED PROCESS PANELS ==========

    def save_pinned_process_panel(self, process_id: int, x_pos: int = 0, y_pos: int = 0,
                                   width: int = 500, height: int = 600,
                                   is_minimized: bool = False) -> int:
        """
        Save a pinned process panel configuration to database

        Args:
            process_id: Process ID
            x_pos: X position on screen
            y_pos: Y position on screen
            width: Panel width
            height: Panel height
            is_minimized: Whether panel is minimized

        Returns:
            int: New panel ID
        """
        query = """
            INSERT INTO pinned_process_panels
            (process_id, x_position, y_position, width, height, is_minimized, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """
        panel_id = self.execute_update(
            query,
            (process_id, x_pos, y_pos, width, height, is_minimized)
        )
        logger.info(f"Pinned process panel saved: Process={process_id} (ID: {panel_id})")
        return panel_id

    def get_pinned_process_panels(self, active_only: bool = True) -> List[Dict]:
        """
        Retrieve all pinned process panels

        Args:
            active_only: Only return panels marked as active

        Returns:
            List[Dict]: List of panel dictionaries with process info
        """
        query = """
            SELECT pp.*, p.name as process_name, p.icon as process_icon
            FROM pinned_process_panels pp
            INNER JOIN processes p ON pp.process_id = p.id
        """
        if active_only:
            query += " WHERE pp.is_active = 1"

        query += " ORDER BY pp.last_opened DESC"

        panels = self.execute_query(query)
        logger.debug(f"Retrieved {len(panels)} pinned process panels")
        return panels

    def update_pinned_process_panel(self, panel_id: int, **kwargs) -> bool:
        """
        Update pinned process panel configuration

        Args:
            panel_id: Panel ID to update
            **kwargs: Fields to update (x_position, y_position, width, height, is_minimized)

        Returns:
            bool: True if update successful
        """
        allowed_fields = {'x_position', 'y_position', 'width', 'height', 'is_minimized'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        query = f"UPDATE pinned_process_panels SET {set_clause} WHERE id = ?"
        params = list(updates.values()) + [panel_id]

        self.execute_update(query, tuple(params))
        logger.info(f"Pinned process panel updated: ID {panel_id}")
        return True

    def update_process_panel_last_opened(self, panel_id: int) -> None:
        """
        Update last_opened timestamp and increment open_count

        Args:
            panel_id: Panel ID
        """
        query = """
            UPDATE pinned_process_panels
            SET last_opened = CURRENT_TIMESTAMP,
                open_count = open_count + 1
            WHERE id = ?
        """
        self.execute_update(query, (panel_id,))
        logger.debug(f"Process panel {panel_id} opened - statistics updated")

    def delete_pinned_process_panel(self, panel_id: int) -> bool:
        """
        Remove a pinned process panel from database

        Args:
            panel_id: Panel ID to delete

        Returns:
            bool: True if deletion successful
        """
        query = "DELETE FROM pinned_process_panels WHERE id = ?"
        self.execute_update(query, (panel_id,))
        logger.info(f"Pinned process panel deleted: ID {panel_id}")
        return True

    def deactivate_all_process_panels(self) -> None:
        """
        Set is_active=0 for all process panels (called on app shutdown)
        """
        query = "UPDATE pinned_process_panels SET is_active = 0"
        self.execute_update(query)
        logger.info("All pinned process panels marked as inactive")

    def get_panel_by_category(self, category_id: int) -> Optional[Dict]:
        """
        Check if an active panel for this category already exists

        Args:
            category_id: Category ID

        Returns:
            Optional[Dict]: Panel dictionary if exists, None otherwise
        """
        query = """
            SELECT p.*, c.name as category_name, c.icon as category_icon
            FROM pinned_panels p
            JOIN categories c ON p.category_id = c.id
            WHERE p.category_id = ? AND p.is_active = 1
            LIMIT 1
        """
        result = self.execute_query(query, (category_id,))
        return result[0] if result else None

    # ========== BROWSER CONFIG ==========

    def get_browser_config(self) -> Dict:
        """
        Get browser configuration from database.

        Returns:
            Dict: Browser configuration or default values if not exists
        """
        query = "SELECT * FROM browser_config LIMIT 1"
        try:
            result = self.execute_query(query)
            if result:
                config = result[0]
                logger.debug(f"Browser config loaded: {config}")
                return config
            else:
                # No config exists, insert default
                logger.info("No browser config found, creating default")
                default_config = {
                    'home_url': 'https://www.google.com',
                    'is_visible': False,
                    'width': 500,
                    'height': 700
                }
                self.save_browser_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Error loading browser config: {e}")
            # Return default config on error
            return {
                'home_url': 'https://www.google.com',
                'is_visible': False,
                'width': 500,
                'height': 700
            }

    def save_browser_config(self, config: Dict) -> bool:
        """
        Save browser configuration to database.

        Args:
            config: Dictionary with browser settings
                   (home_url, is_visible, width, height)

        Returns:
            bool: True if save successful
        """
        try:
            # Check if config exists
            query = "SELECT id FROM browser_config LIMIT 1"
            result = self.execute_query(query)

            if result:
                # Update existing config
                config_id = result[0]['id']
                update_query = """
                    UPDATE browser_config
                    SET home_url = ?,
                        is_visible = ?,
                        width = ?,
                        height = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
                self.execute_update(
                    update_query,
                    (
                        config.get('home_url', 'https://www.google.com'),
                        config.get('is_visible', False),
                        config.get('width', 500),
                        config.get('height', 700),
                        config_id
                    )
                )
                logger.info(f"Browser config updated: ID {config_id}")
            else:
                # Insert new config
                insert_query = """
                    INSERT INTO browser_config (home_url, is_visible, width, height)
                    VALUES (?, ?, ?, ?)
                """
                self.execute_update(
                    insert_query,
                    (
                        config.get('home_url', 'https://www.google.com'),
                        config.get('is_visible', False),
                        config.get('width', 500),
                        config.get('height', 700)
                    )
                )
                logger.info("Browser config created")

            return True

        except Exception as e:
            logger.error(f"Error saving browser config: {e}")
            return False

    # ==================== Browser Profiles Management ====================

    def get_browser_profiles(self) -> List[Dict]:
        """
        Get all browser profiles.

        Returns:
            List[Dict]: List of browser profiles
        """
        query = """
            SELECT id, name, storage_path, is_default, created_at, last_used
            FROM browser_profiles
            ORDER BY is_default DESC, last_used DESC
        """
        try:
            result = self.execute_query(query)
            logger.debug(f"Retrieved {len(result) if result else 0} browser profiles")
            return result if result else []
        except Exception as e:
            logger.error(f"Error getting browser profiles: {e}")
            return []

    def get_default_profile(self) -> Optional[Dict]:
        """
        Get the default browser profile.

        Returns:
            Dict: Default profile or None
        """
        query = """
            SELECT id, name, storage_path, is_default, created_at, last_used
            FROM browser_profiles
            WHERE is_default = 1
            LIMIT 1
        """
        try:
            result = self.execute_query(query)
            if result:
                logger.debug(f"Default profile: {result[0]['name']}")
                return result[0]
            else:
                logger.warning("No default profile found")
                return None
        except Exception as e:
            logger.error(f"Error getting default profile: {e}")
            return None

    def get_profile_by_id(self, profile_id: int) -> Optional[Dict]:
        """
        Get browser profile by ID.

        Args:
            profile_id: Profile ID

        Returns:
            Dict: Profile data or None
        """
        query = """
            SELECT id, name, storage_path, is_default, created_at, last_used
            FROM browser_profiles
            WHERE id = ?
        """
        try:
            result = self.execute_query(query, (profile_id,))
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting profile {profile_id}: {e}")
            return None

    def add_browser_profile(self, name: str, storage_path: str = None) -> Optional[int]:
        """
        Add a new browser profile.

        Args:
            name: Profile name
            storage_path: Custom storage path (optional, auto-generated if None)

        Returns:
            int: Profile ID or None if failed
        """
        try:
            # Auto-generate storage path if not provided
            if not storage_path:
                # Sanitize name for path
                import re
                safe_name = re.sub(r'[^\w\-]', '_', name.lower())
                storage_path = f"browser_data/{safe_name}"

            # Check if name already exists
            check_query = "SELECT id FROM browser_profiles WHERE name = ?"
            existing = self.execute_query(check_query, (name,))

            if existing:
                logger.warning(f"Profile with name '{name}' already exists")
                return None

            # Insert new profile
            insert_query = """
                INSERT INTO browser_profiles (name, storage_path, is_default)
                VALUES (?, ?, 0)
            """
            self.execute_update(insert_query, (name, storage_path))

            # Get inserted ID
            last_id_query = "SELECT last_insert_rowid() as id"
            result = self.execute_query(last_id_query)
            profile_id = result[0]['id'] if result else None

            logger.info(f"Browser profile created: '{name}' (ID: {profile_id})")
            return profile_id

        except Exception as e:
            logger.error(f"Error adding browser profile: {e}")
            return None

    def delete_browser_profile(self, profile_id: int) -> bool:
        """
        Delete a browser profile.

        Args:
            profile_id: Profile ID

        Returns:
            bool: True if deleted successfully
        """
        try:
            # Check if it's the default profile
            profile = self.get_profile_by_id(profile_id)
            if not profile:
                logger.warning(f"Profile {profile_id} not found")
                return False

            if profile['is_default']:
                logger.warning("Cannot delete default profile")
                return False

            # Delete profile
            delete_query = "DELETE FROM browser_profiles WHERE id = ?"
            self.execute_update(delete_query, (profile_id,))

            logger.info(f"Browser profile {profile_id} deleted")
            return True

        except Exception as e:
            logger.error(f"Error deleting browser profile: {e}")
            return False

    def set_default_profile(self, profile_id: int) -> bool:
        """
        Set a profile as default.

        Args:
            profile_id: Profile ID

        Returns:
            bool: True if successful
        """
        try:
            # Remove default from all profiles
            update_all_query = "UPDATE browser_profiles SET is_default = 0"
            self.execute_update(update_all_query)

            # Set new default
            update_query = "UPDATE browser_profiles SET is_default = 1 WHERE id = ?"
            self.execute_update(update_query, (profile_id,))

            logger.info(f"Profile {profile_id} set as default")
            return True

        except Exception as e:
            logger.error(f"Error setting default profile: {e}")
            return False

    def update_profile_last_used(self, profile_id: int) -> bool:
        """
        Update the last_used timestamp for a profile.

        Args:
            profile_id: Profile ID

        Returns:
            bool: True if successful
        """
        try:
            update_query = """
                UPDATE browser_profiles
                SET last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            self.execute_update(update_query, (profile_id,))
            logger.debug(f"Profile {profile_id} last_used updated")
            return True

        except Exception as e:
            logger.error(f"Error updating profile last_used: {e}")
            return False

    # ==================== Bookmarks Management ====================

    def add_bookmark(self, title: str, url: str, folder: str = None) -> Optional[int]:
        """
        Agrega un marcador a la base de datos.

        Args:
            title: Título de la página
            url: URL completa
            folder: Carpeta/grupo opcional

        Returns:
            int: ID del marcador creado, o None si falla
        """
        try:
            # Verificar si el marcador ya existe
            check_query = "SELECT id FROM bookmarks WHERE url = ?"
            existing = self.execute_query(check_query, (url,))

            if existing:
                logger.warning(f"Marcador ya existe para URL: {url}")
                return existing[0]['id']

            # Obtener el siguiente order_index
            max_order_query = "SELECT COALESCE(MAX(order_index), -1) + 1 as next_order FROM bookmarks"
            result = self.execute_query(max_order_query)
            next_order = result[0]['next_order'] if result else 0

            # Insertar marcador
            insert_query = """
                INSERT INTO bookmarks (title, url, folder, order_index)
                VALUES (?, ?, ?, ?)
            """
            self.execute_update(insert_query, (title, url, folder, next_order))

            # Obtener el ID insertado
            last_id_query = "SELECT last_insert_rowid() as id"
            result = self.execute_query(last_id_query)
            bookmark_id = result[0]['id'] if result else None

            logger.info(f"Marcador agregado: '{title}' - {url}")
            return bookmark_id

        except Exception as e:
            logger.error(f"Error al agregar marcador: {e}")
            return None

    def get_bookmarks(self, folder: str = None) -> List[Dict]:
        """
        Obtiene todos los marcadores, opcionalmente filtrados por carpeta.

        Args:
            folder: Carpeta para filtrar (None = todos)

        Returns:
            List[Dict]: Lista de marcadores
        """
        try:
            if folder is not None:
                query = """
                    SELECT id, title, url, folder, icon, created_at, order_index
                    FROM bookmarks
                    WHERE folder = ?
                    ORDER BY order_index ASC, created_at DESC
                """
                result = self.execute_query(query, (folder,))
            else:
                query = """
                    SELECT id, title, url, folder, icon, created_at, order_index
                    FROM bookmarks
                    ORDER BY order_index ASC, created_at DESC
                """
                result = self.execute_query(query)

            return result if result else []

        except Exception as e:
            logger.error(f"Error al obtener marcadores: {e}")
            return []

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """
        Elimina un marcador por su ID.

        Args:
            bookmark_id: ID del marcador

        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            delete_query = "DELETE FROM bookmarks WHERE id = ?"
            self.execute_update(delete_query, (bookmark_id,))
            logger.info(f"Marcador eliminado: ID {bookmark_id}")
            return True

        except Exception as e:
            logger.error(f"Error al eliminar marcador: {e}")
            return False

    def update_bookmark(self, bookmark_id: int, title: str = None, url: str = None,
                       folder: str = None) -> bool:
        """
        Actualiza un marcador existente.

        Args:
            bookmark_id: ID del marcador
            title: Nuevo título (opcional)
            url: Nueva URL (opcional)
            folder: Nueva carpeta (opcional)

        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            # Construir query dinámicamente solo con campos no-None
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)

            if url is not None:
                updates.append("url = ?")
                params.append(url)

            if folder is not None:
                updates.append("folder = ?")
                params.append(folder)

            if not updates:
                logger.warning("No se especificaron campos para actualizar")
                return False

            params.append(bookmark_id)
            update_query = f"UPDATE bookmarks SET {', '.join(updates)} WHERE id = ?"

            self.execute_update(update_query, tuple(params))
            logger.info(f"Marcador actualizado: ID {bookmark_id}")
            return True

        except Exception as e:
            logger.error(f"Error al actualizar marcador: {e}")
            return False

    def is_bookmark_exists(self, url: str) -> bool:
        """
        Verifica si ya existe un marcador con la URL dada.

        Args:
            url: URL a verificar

        Returns:
            bool: True si el marcador existe
        """
        try:
            query = "SELECT id FROM bookmarks WHERE url = ?"
            result = self.execute_query(query, (url,))
            return len(result) > 0 if result else False

        except Exception as e:
            logger.error(f"Error al verificar marcador: {e}")
            return False

    # ==================== Speed Dial Management ====================

    def add_speed_dial(self, title: str, url: str, icon: str = '🌐',
                      background_color: str = '#16213e', thumbnail_path: str = None) -> Optional[int]:
        """
        Agrega un acceso rápido (speed dial) a la base de datos.

        Args:
            title: Título del sitio
            url: URL completa
            icon: Emoji o icono (default: 🌐)
            background_color: Color de fondo del tile (default: #16213e)
            thumbnail_path: Ruta a thumbnail/screenshot (opcional)

        Returns:
            int: ID del speed dial creado, o None si falla
        """
        try:
            # Obtener la siguiente posición
            max_pos_query = "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM speed_dials"
            result = self.execute_query(max_pos_query)
            next_position = result[0]['next_pos'] if result else 0

            # Insertar speed dial
            insert_query = """
                INSERT INTO speed_dials (title, url, icon, background_color, thumbnail_path, position)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            self.execute_update(insert_query, (title, url, icon, background_color, thumbnail_path, next_position))

            # Obtener el ID insertado
            last_id_query = "SELECT last_insert_rowid() as id"
            result = self.execute_query(last_id_query)
            speed_dial_id = result[0]['id'] if result else None

            logger.info(f"Speed dial agregado: '{title}' - {url}")
            return speed_dial_id

        except Exception as e:
            logger.error(f"Error al agregar speed dial: {e}")
            return None

    def get_speed_dials(self) -> List[Dict]:
        """
        Obtiene todos los accesos rápidos ordenados por posición.

        Returns:
            List[Dict]: Lista de speed dials
        """
        try:
            query = """
                SELECT id, title, url, icon, background_color, thumbnail_path, position, created_at
                FROM speed_dials
                ORDER BY position ASC
            """
            result = self.execute_query(query)
            return result if result else []

        except Exception as e:
            logger.error(f"Error al obtener speed dials: {e}")
            return []

    def update_speed_dial(self, speed_dial_id: int, title: str = None, url: str = None,
                         icon: str = None, background_color: str = None,
                         thumbnail_path: str = None) -> bool:
        """
        Actualiza un speed dial existente.

        Args:
            speed_dial_id: ID del speed dial
            title: Nuevo título (opcional)
            url: Nueva URL (opcional)
            icon: Nuevo icono (opcional)
            background_color: Nuevo color de fondo (opcional)
            thumbnail_path: Nueva ruta de thumbnail (opcional)

        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            # Construir query dinámicamente solo con campos no-None
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)

            if url is not None:
                updates.append("url = ?")
                params.append(url)

            if icon is not None:
                updates.append("icon = ?")
                params.append(icon)

            if background_color is not None:
                updates.append("background_color = ?")
                params.append(background_color)

            if thumbnail_path is not None:
                updates.append("thumbnail_path = ?")
                params.append(thumbnail_path)

            if not updates:
                logger.warning("No se especificaron campos para actualizar")
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(speed_dial_id)

            update_query = f"UPDATE speed_dials SET {', '.join(updates)} WHERE id = ?"
            self.execute_update(update_query, tuple(params))
            logger.info(f"Speed dial actualizado: ID {speed_dial_id}")
            return True

        except Exception as e:
            logger.error(f"Error al actualizar speed dial: {e}")
            return False

    def delete_speed_dial(self, speed_dial_id: int) -> bool:
        """
        Elimina un speed dial por su ID.

        Args:
            speed_dial_id: ID del speed dial

        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            delete_query = "DELETE FROM speed_dials WHERE id = ?"
            self.execute_update(delete_query, (speed_dial_id,))
            logger.info(f"Speed dial eliminado: ID {speed_dial_id}")

            # Reorganizar posiciones
            self._reorder_speed_dials()
            return True

        except Exception as e:
            logger.error(f"Error al eliminar speed dial: {e}")
            return False

    def reorder_speed_dial(self, speed_dial_id: int, new_position: int) -> bool:
        """
        Cambia la posición de un speed dial.

        Args:
            speed_dial_id: ID del speed dial
            new_position: Nueva posición (0-based)

        Returns:
            bool: True si se reordenó correctamente
        """
        try:
            update_query = "UPDATE speed_dials SET position = ? WHERE id = ?"
            self.execute_update(update_query, (new_position, speed_dial_id))
            self._reorder_speed_dials()
            logger.info(f"Speed dial reordenado: ID {speed_dial_id} -> posición {new_position}")
            return True

        except Exception as e:
            logger.error(f"Error al reordenar speed dial: {e}")
            return False

    def _reorder_speed_dials(self):
        """Reorganiza las posiciones de speed dials para que sean consecutivas (0, 1, 2, ...)."""
        try:
            # Obtener todos los speed dials ordenados por posición actual
            speed_dials = self.get_speed_dials()

            # Actualizar posiciones para que sean consecutivas
            for index, sd in enumerate(speed_dials):
                if sd['position'] != index:
                    update_query = "UPDATE speed_dials SET position = ? WHERE id = ?"
                    self.execute_update(update_query, (index, sd['id']))

        except Exception as e:
            logger.error(f"Error al reorganizar speed dials: {e}")

    # ==================== Browser Sessions Management ====================

    def save_session(self, name: str, tabs_data: list, is_auto_save: bool = False) -> Optional[int]:
        """
        Guarda una sesión del navegador con todas sus pestañas.

        Args:
            name: Nombre de la sesión
            tabs_data: Lista de diccionarios con datos de pestañas [{url, title, position, is_active}]
            is_auto_save: Si es una sesión de auto-guardado (True) o guardada manualmente (False)

        Returns:
            int: ID de la sesión creada o None si falla
        """
        try:
            # Si es auto-save, eliminar sesiones auto-save anteriores
            if is_auto_save:
                delete_query = "DELETE FROM browser_sessions WHERE is_auto_save = 1"
                self.execute_update(delete_query)

            # Crear sesión
            insert_query = """
                INSERT INTO browser_sessions (name, is_auto_save)
                VALUES (?, ?)
            """
            self.execute_update(insert_query, (name, 1 if is_auto_save else 0))

            # Obtener ID de la sesión creada
            session_id_query = "SELECT last_insert_rowid() as id"
            result = self.execute_query(session_id_query)
            if not result:
                logger.error("No se pudo obtener el ID de la sesión")
                return None

            session_id = result[0]['id']

            # Guardar pestañas
            for tab in tabs_data:
                tab_query = """
                    INSERT INTO session_tabs (session_id, url, title, position, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """
                self.execute_update(tab_query, (
                    session_id,
                    tab.get('url', ''),
                    tab.get('title', 'Nueva pestaña'),
                    tab.get('position', 0),
                    1 if tab.get('is_active', False) else 0
                ))

            logger.info(f"Sesión guardada: {name} (ID: {session_id}) con {len(tabs_data)} pestañas")
            return session_id

        except Exception as e:
            logger.error(f"Error al guardar sesión: {e}")
            return None

    def get_sessions(self, include_auto_save: bool = False) -> List[Dict]:
        """
        Obtiene todas las sesiones guardadas.

        Args:
            include_auto_save: Si incluir sesiones de auto-guardado

        Returns:
            Lista de diccionarios con información de sesiones
        """
        try:
            if include_auto_save:
                query = """
                    SELECT id, name, is_auto_save, created_at, updated_at,
                           (SELECT COUNT(*) FROM session_tabs WHERE session_id = browser_sessions.id) as tab_count
                    FROM browser_sessions
                    ORDER BY created_at DESC
                """
            else:
                query = """
                    SELECT id, name, is_auto_save, created_at, updated_at,
                           (SELECT COUNT(*) FROM session_tabs WHERE session_id = browser_sessions.id) as tab_count
                    FROM browser_sessions
                    WHERE is_auto_save = 0
                    ORDER BY created_at DESC
                """

            result = self.execute_query(query)
            return result if result else []

        except Exception as e:
            logger.error(f"Error al obtener sesiones: {e}")
            return []

    def get_session_tabs(self, session_id: int) -> List[Dict]:
        """
        Obtiene todas las pestañas de una sesión.

        Args:
            session_id: ID de la sesión

        Returns:
            Lista de diccionarios con información de pestañas
        """
        try:
            query = """
                SELECT id, url, title, position, is_active
                FROM session_tabs
                WHERE session_id = ?
                ORDER BY position ASC
            """
            result = self.execute_query(query, (session_id,))
            return result if result else []

        except Exception as e:
            logger.error(f"Error al obtener pestañas de sesión: {e}")
            return []

    def get_last_auto_save_session(self) -> Optional[Dict]:
        """
        Obtiene la última sesión guardada automáticamente.

        Returns:
            Diccionario con información de la sesión o None
        """
        try:
            query = """
                SELECT id, name, is_auto_save, created_at, updated_at
                FROM browser_sessions
                WHERE is_auto_save = 1
                ORDER BY created_at DESC
                LIMIT 1
            """
            result = self.execute_query(query)
            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error al obtener última sesión auto-guardada: {e}")
            return None

    def delete_session(self, session_id: int) -> bool:
        """
        Elimina una sesión y todas sus pestañas.

        Args:
            session_id: ID de la sesión

        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            # Las pestañas se eliminan automáticamente por la cláusula ON DELETE CASCADE
            delete_query = "DELETE FROM browser_sessions WHERE id = ?"
            self.execute_update(delete_query, (session_id,))
            logger.info(f"Sesión eliminada: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error al eliminar sesión: {e}")
            return False

    def rename_session(self, session_id: int, new_name: str) -> bool:
        """
        Renombra una sesión.

        Args:
            session_id: ID de la sesión
            new_name: Nuevo nombre de la sesión

        Returns:
            True si se renombró correctamente, False en caso contrario
        """
        try:
            update_query = """
                UPDATE browser_sessions
                SET name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            self.execute_update(update_query, (new_name, session_id))
            logger.info(f"Sesión {session_id} renombrada a: {new_name}")
            return True

        except Exception as e:
            logger.error(f"Error al renombrar sesión: {e}")
            return False

    # ==================== NOTEBOOK TABS MANAGEMENT ====================

    def get_notebook_tabs(self, order_by='position'):
        """
        Obtener todas las pestañas del notebook ordenadas

        Args:
            order_by: Campo por el cual ordenar (default: 'position')

        Returns:
            List[Dict]: Lista de pestañas
        """
        query = f"SELECT * FROM notebook_tabs ORDER BY {order_by} ASC"
        return self.execute_query(query)

    def get_notebook_tab(self, tab_id):
        """
        Obtener una pestaña específica

        Args:
            tab_id: ID de la pestaña

        Returns:
            Optional[Dict]: Datos de la pestaña o None
        """
        query = "SELECT * FROM notebook_tabs WHERE id = ?"
        result = self.execute_query(query, (tab_id,))
        return result[0] if result else None

    def add_notebook_tab(self, title='Sin título', position=None):
        """
        Crear nueva pestaña del notebook

        Args:
            title: Título de la pestaña
            position: Posición de la pestaña (auto-calculada si es None)

        Returns:
            int: ID de la pestaña creada
        """
        if position is None:
            # Obtener última posición
            result = self.execute_query(
                "SELECT MAX(position) as max_pos FROM notebook_tabs"
            )
            max_pos = result[0]['max_pos'] if result and result[0]['max_pos'] is not None else -1
            position = max_pos + 1

        query = """
            INSERT INTO notebook_tabs (title, position, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """
        tab_id = self.execute_update(query, (title, position))
        logger.info(f"Notebook tab created: '{title}' (ID: {tab_id}, position: {position})")
        return tab_id

    def update_notebook_tab(self, tab_id, **fields):
        """
        Actualizar campos de una pestaña del notebook

        Args:
            tab_id: ID de la pestaña
            **fields: Campos a actualizar (title, content, category_id, item_type,
                     tags, description, is_sensitive, is_active, is_archived, position)

        Returns:
            bool: True si se actualizó correctamente
        """
        allowed_fields = [
            'title', 'content', 'category_id', 'item_type', 'tags',
            'description', 'is_sensitive', 'is_active', 'is_archived', 'position'
        ]

        updates = []
        values = []

        for field, value in fields.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)

        if not updates:
            logger.warning(f"No valid fields to update for notebook tab {tab_id}")
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(tab_id)

        query = f"UPDATE notebook_tabs SET {', '.join(updates)} WHERE id = ?"

        try:
            self.execute_update(query, tuple(values))
            logger.debug(f"Notebook tab updated: ID {tab_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating notebook tab {tab_id}: {e}")
            return False

    def delete_notebook_tab(self, tab_id):
        """
        Eliminar una pestaña del notebook

        Args:
            tab_id: ID de la pestaña

        Returns:
            bool: True si se eliminó correctamente
        """
        query = "DELETE FROM notebook_tabs WHERE id = ?"
        try:
            self.execute_update(query, (tab_id,))
            logger.info(f"Notebook tab deleted: ID {tab_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting notebook tab {tab_id}: {e}")
            return False

    def reorder_notebook_tabs(self, tab_ids_in_order):
        """
        Reordenar pestañas según lista de IDs

        Args:
            tab_ids_in_order: Lista de IDs en el orden deseado

        Returns:
            bool: True si se reordenó correctamente
        """
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                for position, tab_id in enumerate(tab_ids_in_order):
                    cursor.execute(
                        "UPDATE notebook_tabs SET position = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (position, tab_id)
                    )
            logger.info(f"Notebook tabs reordered: {len(tab_ids_in_order)} tabs")
            return True
        except Exception as e:
            logger.error(f"Error reordering notebook tabs: {e}")
            return False

    def count_notebook_tabs(self):
        """
        Contar número de pestañas del notebook

        Returns:
            int: Número de pestañas
        """
        query = "SELECT COUNT(*) as count FROM notebook_tabs"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0

    # ==================== AI Bulk Import Support ====================

    def get_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """
        Get category by ID.

        Args:
            category_id: ID of the category

        Returns:
            Dictionary with category data or None if not found
        """
        query = "SELECT * FROM categories WHERE id = ?"
        result = self.execute_query(query, (category_id,))

        if result:
            category = dict(result[0])
            logger.debug(f"Category found: {category['name']} (ID: {category_id})")
            return category
        else:
            logger.warning(f"Category not found: ID {category_id}")
            return None

    def update_category_item_count(self, category_id: int) -> None:
        """
        Update item_count field of a category based on active items.

        This method counts all active items in the category and updates
        the item_count field accordingly.

        Args:
            category_id: ID of the category to update
        """
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()

                # Count active items in category
                cursor.execute(
                    "SELECT COUNT(*) as count FROM items WHERE category_id = ? AND is_active = 1",
                    (category_id,)
                )
                count = cursor.fetchone()['count']

                # Update category item_count
                cursor.execute(
                    "UPDATE categories SET item_count = ? WHERE id = ?",
                    (count, category_id)
                )

            logger.info(f"Updated item_count for category {category_id}: {count} items")

        except Exception as e:
            logger.error(f"Error updating category item_count for {category_id}: {e}")
            raise

    # ==================== Table Operations ====================

    def add_table_items(self, category_id: str, table_name: str, table_data: list,
                       column_names: list, tags: list = None, sensitive_columns: list = None,
                       url_columns: list = None) -> dict:
        """
        Create all items for a table in a single transaction

        Args:
            category_id: Category ID where table belongs
            table_name: Unique name for the table
            table_data: 2D list of cell values [[row1_col1, row1_col2], [row2_col1, row2_col2]]
            column_names: List of column names
            tags: Optional list of tags to apply to all items
            sensitive_columns: Optional list of column indices that should be marked as sensitive
            url_columns: Optional list of column indices that should be marked as type URL

        Returns:
            dict with 'success', 'items_created', 'table_name', 'errors'
        """
        try:
            logger.info(f"Creating table '{table_name}' in category {category_id}")
            logger.info(f"  Rows: {len(table_data)}, Columns: {len(column_names)}")

            items_created = 0
            errors = []

            with self.transaction() as conn:
                cursor = conn.cursor()

                # Validate table name is unique
                cursor.execute(
                    "SELECT COUNT(*) as count FROM items WHERE name_table = ?",
                    (table_name,)
                )
                if cursor.fetchone()['count'] > 0:
                    logger.error(f"Table name '{table_name}' already exists")
                    return {
                        'success': False,
                        'items_created': 0,
                        'table_name': table_name,
                        'errors': [f"Table name '{table_name}' already exists"]
                    }

                # Preparar tags base (los que vienen del usuario)
                base_tags = tags if tags else []

                # Prepare sensitive columns set for fast lookup
                sensitive_cols_set = set(sensitive_columns) if sensitive_columns else set()

                # Prepare URL columns set for fast lookup
                url_cols_set = set(url_columns) if url_columns else set()

                # Insert each cell as an item
                for row_idx, row_data in enumerate(table_data):
                    # Obtener el valor de la primera celda (nombre de fila)
                    first_cell_value = ""
                    first_cell_original = ""  # Valor original sin sanitizar para el tag

                    if len(row_data) > 0 and row_data[0]:
                        first_cell_original = str(row_data[0]).strip()
                        first_cell_value = first_cell_original

                        # Sanitizar el valor para usarlo en list_group (remover caracteres especiales)
                        first_cell_value = first_cell_value.replace(' ', '_')
                        first_cell_value = ''.join(c for c in first_cell_value if c.isalnum() or c in ('_', '-'))
                        # Limitar longitud
                        if len(first_cell_value) > 50:
                            first_cell_value = first_cell_value[:50]

                    # Si la primera celda está vacía, usar row_N como fallback
                    if not first_cell_value:
                        first_cell_value = f"row_{row_idx}"
                        first_cell_original = f"row_{row_idx}"

                    # Generar list_group: solo el nombre de la primera celda (sin prefijo de tabla)
                    list_group_name = first_cell_value

                    for col_idx, cell_value in enumerate(row_data):
                        # Skip empty cells
                        if not cell_value or str(cell_value).strip() == '':
                            continue

                        try:
                            # Create item for this cell
                            column_name = column_names[col_idx] if col_idx < len(column_names) else f"COL_{col_idx}"

                            # Generar tags automáticos para esta celda
                            # Formato: ["tabla", "lista", "nombre_tabla", "nombre_fila", "nombre_columna"]
                            # Nota: Se incluye "lista" porque cada fila de una tabla también es una lista
                            cell_tags = ["tabla", "lista", table_name, first_cell_original, column_name]

                            # Agregar tags base del usuario (si existen)
                            for tag in base_tags:
                                if tag and tag not in cell_tags:
                                    cell_tags.append(tag)

                            # Convertir a JSON para almacenar
                            tags_json = json.dumps(cell_tags)

                            # Determinar si esta columna es sensible
                            is_sensitive = 1 if col_idx in sensitive_cols_set else 0

                            # Determinar el tipo de item
                            item_type = 'URL' if col_idx in url_cols_set else 'TEXT'

                            # Cifrar contenido si es sensible
                            content_to_store = str(cell_value)
                            if is_sensitive and content_to_store:
                                from core.encryption_manager import EncryptionManager
                                encryption_manager = EncryptionManager()
                                content_to_store = encryption_manager.encrypt(content_to_store)
                                logger.debug(f"Content encrypted for sensitive column '{column_name}' at [{row_idx}, {col_idx}]")

                            cursor.execute("""
                                INSERT INTO items (
                                    category_id, label, content, type,
                                    is_table, name_table, orden_table,
                                    is_list, list_group, orden_lista,
                                    is_sensitive, tags, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                            """, (
                                int(category_id),  # Convert to INTEGER
                                column_name,  # Label = column name
                                content_to_store,  # Content = cell value (cifrado si es sensible)
                                item_type,  # Type (URL si está en url_columns, TEXT por defecto)
                                1,  # is_table = True
                                table_name,  # name_table
                                json.dumps([row_idx, col_idx]),  # orden_table as JSON [row, col]
                                1,  # is_list = True (for row grouping)
                                list_group_name,  # list_group = {table_name}_{primera_celda}
                                col_idx + 1,  # orden_lista = column index + 1 (empieza en 1)
                                is_sensitive,  # is_sensitive (1 si columna marcada como sensible)
                                tags_json  # tags en formato JSON: ["tabla", "nombre_tabla", "nombre_fila", "nombre_columna"]
                            ))

                            items_created += 1

                        except Exception as e:
                            error_msg = f"Error creating item at [{row_idx}, {col_idx}]: {e}"
                            logger.error(error_msg)
                            errors.append(error_msg)

            # Update category item_count (outside transaction)
            self.update_category_item_count(category_id)

            logger.info(f"✓ Table '{table_name}' created: {items_created} items")

            return {
                'success': items_created > 0,
                'items_created': items_created,
                'table_name': table_name,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Error creating table '{table_name}': {e}", exc_info=True)
            return {
                'success': False,
                'items_created': 0,
                'table_name': table_name,
                'errors': [str(e)]
            }

    def get_table_items(self, table_name: str) -> list:
        """
        Retrieve all items belonging to a specific table

        Args:
            table_name: Name of the table

        Returns:
            List of item dictionaries ordered by [row, col]
        """
        try:
            logger.info(f"Retrieving items for table '{table_name}'")

            query = """
                SELECT * FROM items
                WHERE name_table = ? AND is_table = 1
                ORDER BY orden_table
            """
            results = self.execute_query(query, (table_name,))

            # Parse tags for each item
            for item in results:
                if item['tags']:
                    try:
                        item['tags'] = json.loads(item['tags'])
                    except json.JSONDecodeError:
                        if isinstance(item['tags'], str):
                            item['tags'] = [tag.strip() for tag in item['tags'].split(',') if tag.strip()]
                        else:
                            item['tags'] = []
                else:
                    item['tags'] = []

            logger.info(f"Found {len(results)} items for table '{table_name}'")
            return results

        except Exception as e:
            logger.error(f"Error retrieving table items for '{table_name}': {e}")
            return []

    def get_tables_by_category(self, category_id: str) -> list:
        """
        Get list of all tables in a category

        Args:
            category_id: Category ID

        Returns:
            List of dicts with table info: {'name', 'rows', 'cols', 'item_count', 'created_at'}
        """
        try:
            logger.info(f"Getting tables for category {category_id}")

            with self.transaction() as conn:
                cursor = conn.cursor()

                # Get unique table names in this category
                cursor.execute("""
                    SELECT
                        name_table,
                        COUNT(*) as item_count,
                        MIN(created_at) as created_at
                    FROM items
                    WHERE category_id = ? AND is_table = 1 AND name_table IS NOT NULL
                    GROUP BY name_table
                    ORDER BY created_at DESC
                """, (category_id,))

                tables = []
                for row in cursor.fetchall():
                    table_name = row['name_table']

                    # Get dimensions (max row and col from orden_table)
                    cursor.execute("""
                        SELECT orden_table FROM items
                        WHERE name_table = ? AND is_table = 1
                    """, (table_name,))

                    coords = []
                    for item_row in cursor.fetchall():
                        try:
                            coord = json.loads(item_row['orden_table'])
                            coords.append(coord)
                        except:
                            continue

                    max_row = max([c[0] for c in coords]) + 1 if coords else 0
                    max_col = max([c[1] for c in coords]) + 1 if coords else 0

                    tables.append({
                        'name': table_name,
                        'rows': max_row,
                        'cols': max_col,
                        'item_count': row['item_count'],
                        'created_at': row['created_at']
                    })

                logger.info(f"Found {len(tables)} tables in category {category_id}")
                return tables

        except Exception as e:
            logger.error(f"Error getting tables for category {category_id}: {e}")
            return []

    def update_table_cell(self, table_name: str, row: int, col: int, new_content: str) -> bool:
        """
        Update content of a specific table cell

        Args:
            table_name: Name of the table
            row: Row index (0-based)
            col: Column index (0-based)
            new_content: New content for the cell

        Returns:
            True if successful
        """
        try:
            logger.info(f"Updating table '{table_name}' cell [{row}, {col}]")

            orden_json = json.dumps([row, col])

            with self.transaction() as conn:
                cursor = conn.cursor()

                # Find item at this position
                cursor.execute("""
                    SELECT id FROM items
                    WHERE name_table = ? AND orden_table = ? AND is_table = 1
                """, (table_name, orden_json))

                result = cursor.fetchone()

                if result:
                    # Update existing item
                    item_id = result['id']
                    cursor.execute("""
                        UPDATE items
                        SET content = ?, updated_at = datetime('now')
                        WHERE id = ?
                    """, (new_content, item_id))

                    # Si se actualizó la primera columna, actualizar list_group y tags de toda la fila
                    if col == 0 and new_content and new_content.strip():
                        # Sanitizar el nuevo valor para list_group y tag
                        first_cell_value = new_content.strip()
                        first_cell_value = first_cell_value.replace(' ', '_')
                        first_cell_value = ''.join(c for c in first_cell_value if c.isalnum() or c in ('_', '-'))
                        if len(first_cell_value) > 50:
                            first_cell_value = first_cell_value[:50]

                        if first_cell_value:
                            new_list_group = f"{table_name}_{first_cell_value}"

                            # Obtener el tag anterior de la primera celda para reemplazarlo
                            cursor.execute("""
                                SELECT tags FROM items
                                WHERE name_table = ? AND is_table = 1
                                AND json_extract(orden_table, '$[0]') = ?
                                LIMIT 1
                            """, (table_name, row))

                            old_tags_result = cursor.fetchone()
                            if old_tags_result and old_tags_result['tags']:
                                old_tags = old_tags_result['tags']
                                # Separar tags existentes
                                tag_list = [t.strip() for t in old_tags.split(',') if t.strip()]

                                # Remover el tag anterior de la primera celda (el último tag que no sea table_name)
                                # Mantener solo table_name y otros tags, agregar el nuevo
                                filtered_tags = [t for t in tag_list if t == table_name or not any(c in t for c in ['_', '-']) or t == table_name]
                                # Simplemente agregar el nuevo tag
                                if table_name in tag_list:
                                    new_tags = f"{table_name},{first_cell_value}"
                                else:
                                    new_tags = f"{table_name},{first_cell_value}"
                            else:
                                new_tags = f"{table_name},{first_cell_value}"

                            # Actualizar list_group y tags de todos los items de esta fila
                            cursor.execute("""
                                UPDATE items
                                SET list_group = ?, tags = ?, updated_at = datetime('now')
                                WHERE name_table = ? AND is_table = 1
                                AND json_extract(orden_table, '$[0]') = ?
                            """, (new_list_group, new_tags, table_name, row))

                            logger.info(f"✓ Updated list_group and tags for row {row} to '{new_list_group}' and '{new_tags}'")

                    logger.info(f"✓ Cell updated successfully")
                    return True
                else:
                    logger.warning(f"No item found at table '{table_name}' position [{row}, {col}]")
                    return False

        except Exception as e:
            logger.error(f"Error updating table cell: {e}")
            return False

    def delete_table(self, table_name: str) -> bool:
        """
        Delete all items belonging to a table

        Args:
            table_name: Name of the table to delete

        Returns:
            True if successful
        """
        try:
            logger.info(f"Deleting table '{table_name}'")

            with self.transaction() as conn:
                cursor = conn.cursor()

                # Get category_id before deleting (for updating item_count)
                cursor.execute("""
                    SELECT DISTINCT category_id FROM items
                    WHERE name_table = ? AND is_table = 1
                    LIMIT 1
                """, (table_name,))

                result = cursor.fetchone()
                category_id = result['category_id'] if result else None

                # Delete all items from this table
                cursor.execute("""
                    DELETE FROM items
                    WHERE name_table = ? AND is_table = 1
                """, (table_name,))

                deleted_count = cursor.rowcount

            # Update category item_count if needed (outside transaction)
            if category_id:
                self.update_category_item_count(category_id)

            logger.info(f"✓ Table '{table_name}' deleted: {deleted_count} items removed")
            return True

        except Exception as e:
            logger.error(f"Error deleting table '{table_name}': {e}")
            return False

    def export_table_to_dict(self, table_name: str) -> dict:
        """
        Export table structure and data to dictionary

        Args:
            table_name: Name of the table

        Returns:
            Dict with table metadata and data:
            {
                'table_name': str,
                'columns': list[str],
                'rows': list[list[str]],
                'metadata': {
                    'created_at': str,
                    'total_rows': int,
                    'total_cols': int,
                    'total_items': int
                }
            }
        """
        try:
            logger.info(f"Exporting table '{table_name}' to dict")

            items = self.get_table_items(table_name)

            if not items:
                logger.warning(f"No items found for table '{table_name}'")
                return {
                    'table_name': table_name,
                    'columns': [],
                    'rows': [],
                    'metadata': {
                        'created_at': None,
                        'total_rows': 0,
                        'total_cols': 0,
                        'total_items': 0
                    }
                }

            # Build coordinate map
            cells = {}  # {(row, col): {'label': str, 'content': str}}
            max_row = 0
            max_col = 0
            created_at = None

            for item in items:
                try:
                    coord = json.loads(item['orden_table'])
                    row, col = coord[0], coord[1]
                    cells[(row, col)] = {
                        'label': item['label'],
                        'content': item['content']
                    }
                    max_row = max(max_row, row)
                    max_col = max(max_col, col)

                    if created_at is None or item['created_at'] < created_at:
                        created_at = item['created_at']
                except Exception as e:
                    logger.warning(f"Error parsing item coordinates: {e}")
                    continue

            # Extract column names (from row 0 labels or generate)
            columns = []
            for col in range(max_col + 1):
                if (0, col) in cells:
                    columns.append(cells[(0, col)]['label'])
                else:
                    columns.append(f"COL_{col}")

            # Build rows matrix
            rows = []
            for row in range(max_row + 1):
                row_data = []
                for col in range(max_col + 1):
                    if (row, col) in cells:
                        row_data.append(cells[(row, col)]['content'])
                    else:
                        row_data.append('')  # Empty cell
                rows.append(row_data)

            result = {
                'table_name': table_name,
                'columns': columns,
                'rows': rows,
                'metadata': {
                    'created_at': str(created_at) if created_at else None,
                    'total_rows': max_row + 1,
                    'total_cols': max_col + 1,
                    'total_items': len(items)
                }
            }

            logger.info(f"✓ Table '{table_name}' exported: {len(rows)} rows × {len(columns)} cols")
            return result

        except Exception as e:
            logger.error(f"Error exporting table '{table_name}': {e}", exc_info=True)
            return {
                'table_name': table_name,
                'columns': [],
                'rows': [],
                'metadata': {
                    'created_at': None,
                    'total_rows': 0,
                    'total_cols': 0,
                    'total_items': 0
                }
            }

    # ==================== PROCESSES CRUD ====================

    def add_process(self, name: str, description: str = None, icon: str = None,
                    color: str = None, execution_mode: str = 'sequential',
                    delay_between_steps: int = 500, tags: str = None,
                    category: str = None) -> int:
        """
        Create a new process

        Args:
            name: Process name
            description: Process description
            icon: Process icon (emoji)
            color: Process color (hex)
            execution_mode: Execution mode (sequential, parallel, manual)
            delay_between_steps: Delay in milliseconds between steps
            tags: Comma-separated tags
            category: Category name

        Returns:
            int: ID of created process
        """
        with self.transaction() as conn:
            cursor = conn.execute("""
                INSERT INTO processes (
                    name, description, icon, color, execution_mode,
                    delay_between_steps, tags, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, description, icon or '⚙️', color, execution_mode,
                  delay_between_steps, tags, category))

            process_id = cursor.lastrowid
            logger.info(f"Process created: {name} (ID: {process_id})")
            return process_id

    def get_process(self, process_id: int) -> Optional[Dict[str, Any]]:
        """
        Get process by ID

        Args:
            process_id: Process ID

        Returns:
            Dict with process data or None
        """
        conn = self.connect()
        cursor = conn.execute("""
            SELECT * FROM processes WHERE id = ?
        """, (process_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all_processes(self, include_archived: bool = False,
                          include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all processes

        Args:
            include_archived: Include archived processes
            include_inactive: Include inactive processes

        Returns:
            List of process dicts
        """
        conn = self.connect()

        query = "SELECT * FROM processes WHERE 1=1"
        params = []

        if not include_archived:
            query += " AND is_archived = 0"

        if not include_inactive:
            query += " AND is_active = 1"

        query += " ORDER BY pinned_order ASC, order_index ASC, name ASC"

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_process(self, process_id: int, **kwargs) -> bool:
        """
        Update process fields

        Args:
            process_id: Process ID
            **kwargs: Fields to update

        Returns:
            bool: Success status
        """
        if not kwargs:
            return True

        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.now().isoformat()

        # Build UPDATE query
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [process_id]

        with self.transaction() as conn:
            conn.execute(f"""
                UPDATE processes SET {fields} WHERE id = ?
            """, values)

        logger.info(f"Process {process_id} updated: {list(kwargs.keys())}")
        return True

    def delete_process(self, process_id: int) -> bool:
        """
        Delete process and all its steps (CASCADE)

        Args:
            process_id: Process ID

        Returns:
            bool: Success status
        """
        with self.transaction() as conn:
            conn.execute("DELETE FROM processes WHERE id = ?", (process_id,))

        logger.info(f"Process {process_id} deleted")
        return True

    def search_processes(self, query: str) -> List[Dict[str, Any]]:
        """
        Search processes by name, description, or tags

        Args:
            query: Search query

        Returns:
            List of matching processes
        """
        conn = self.connect()
        search_pattern = f"%{query}%"

        cursor = conn.execute("""
            SELECT * FROM processes
            WHERE (name LIKE ? OR description LIKE ? OR tags LIKE ?)
                AND is_active = 1 AND is_archived = 0
            ORDER BY use_count DESC, name ASC
        """, (search_pattern, search_pattern, search_pattern))

        return [dict(row) for row in cursor.fetchall()]

    def get_pinned_processes(self) -> List[Dict[str, Any]]:
        """
        Get all pinned processes

        Returns:
            List of pinned processes ordered by pinned_order
        """
        conn = self.connect()
        cursor = conn.execute("""
            SELECT * FROM processes
            WHERE is_pinned = 1 AND is_active = 1 AND is_archived = 0
            ORDER BY pinned_order ASC
        """)

        return [dict(row) for row in cursor.fetchall()]

    # ==================== PROCESS STEPS (process_items) ====================

    def add_process_step(self, process_id: int, item_id: int, step_order: int,
                         custom_label: str = None, is_optional: bool = False,
                         is_enabled: bool = True, wait_for_confirmation: bool = False,
                         notes: str = None, group_name: str = None) -> int:
        """
        Add a step to a process

        Args:
            process_id: Process ID
            item_id: Item ID
            step_order: Order of this step in the process
            custom_label: Custom label for this step
            is_optional: Whether this step is optional
            is_enabled: Whether this step is enabled
            wait_for_confirmation: Whether to wait for user confirmation
            notes: Additional notes for this step
            group_name: Group name for organizing steps

        Returns:
            int: ID of created process_item
        """
        with self.transaction() as conn:
            cursor = conn.execute("""
                INSERT INTO process_items (
                    process_id, item_id, step_order, custom_label,
                    is_optional, is_enabled, wait_for_confirmation,
                    notes, group_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (process_id, item_id, step_order, custom_label,
                  int(is_optional), int(is_enabled), int(wait_for_confirmation),
                  notes, group_name))

            step_id = cursor.lastrowid
            logger.info(f"Step added to process {process_id}: item {item_id} at order {step_order}")
            return step_id

    def get_process_steps(self, process_id: int) -> List[Dict[str, Any]]:
        """
        Get all steps of a process with item details

        Args:
            process_id: Process ID

        Returns:
            List of steps with item information
        """
        conn = self.connect()
        cursor = conn.execute("""
            SELECT
                pi.*,
                i.label as item_label,
                i.content as item_content,
                i.type as item_type,
                i.icon as item_icon,
                i.is_sensitive as item_is_sensitive
            FROM process_items pi
            JOIN items i ON pi.item_id = i.id
            WHERE pi.process_id = ?
            ORDER BY pi.step_order ASC
        """, (process_id,))

        return [dict(row) for row in cursor.fetchall()]

    def update_process_step(self, step_id: int, **kwargs) -> bool:
        """
        Update a process step

        Args:
            step_id: Process step ID
            **kwargs: Fields to update

        Returns:
            bool: Success status
        """
        if not kwargs:
            return True

        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [step_id]

        with self.transaction() as conn:
            conn.execute(f"""
                UPDATE process_items SET {fields} WHERE id = ?
            """, values)

        logger.info(f"Process step {step_id} updated")
        return True

    def delete_process_step(self, step_id: int) -> bool:
        """
        Delete a process step

        Args:
            step_id: Process step ID

        Returns:
            bool: Success status
        """
        with self.transaction() as conn:
            conn.execute("DELETE FROM process_items WHERE id = ?", (step_id,))

        logger.info(f"Process step {step_id} deleted")
        return True

    def delete_process_steps(self, process_id: int) -> bool:
        """
        Delete all steps for a process

        Args:
            process_id: Process ID

        Returns:
            bool: Success status
        """
        with self.transaction() as conn:
            cursor = conn.execute("DELETE FROM process_items WHERE process_id = ?", (process_id,))
            deleted_count = cursor.rowcount

        logger.info(f"Deleted {deleted_count} steps for process {process_id}")
        return True

    def reorder_process_steps(self, process_id: int, step_ids_in_order: List[int]) -> bool:
        """
        Reorder steps of a process

        Args:
            process_id: Process ID
            step_ids_in_order: List of step IDs in desired order

        Returns:
            bool: Success status
        """
        with self.transaction() as conn:
            for new_order, step_id in enumerate(step_ids_in_order, start=1):
                conn.execute("""
                    UPDATE process_items
                    SET step_order = ?
                    WHERE id = ? AND process_id = ?
                """, (new_order, step_id, process_id))

        logger.info(f"Reordered {len(step_ids_in_order)} steps for process {process_id}")
        return True

    # ==================== PROCESS EXECUTION HISTORY ====================

    def add_execution_history(self, process_id: int, total_steps: int) -> int:
        """
        Start tracking a process execution

        Args:
            process_id: Process ID
            total_steps: Total number of steps

        Returns:
            int: Execution history ID
        """
        with self.transaction() as conn:
            cursor = conn.execute("""
                INSERT INTO process_execution_history (
                    process_id, total_steps, status
                ) VALUES (?, ?, 'running')
            """, (process_id, total_steps))

            execution_id = cursor.lastrowid
            logger.info(f"Started execution tracking for process {process_id} (ID: {execution_id})")
            return execution_id

    def update_execution_history(self, execution_id: int, **kwargs) -> bool:
        """
        Update execution history

        Args:
            execution_id: Execution history ID
            **kwargs: Fields to update (status, completed_steps, failed_steps, error_message, etc.)

        Returns:
            bool: Success status
        """
        if not kwargs:
            return True

        # If status is being set to completed, set completed_at
        if 'status' in kwargs and kwargs['status'] in ('completed', 'failed', 'cancelled'):
            kwargs['completed_at'] = datetime.now().isoformat()

        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [execution_id]

        with self.transaction() as conn:
            conn.execute(f"""
                UPDATE process_execution_history SET {fields} WHERE id = ?
            """, values)

        return True

    def get_process_execution_history(self, process_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get execution history for a process

        Args:
            process_id: Process ID
            limit: Maximum number of records

        Returns:
            List of execution history records
        """
        conn = self.connect()
        cursor = conn.execute("""
            SELECT * FROM process_execution_history
            WHERE process_id = ?
            ORDER BY started_at DESC
            LIMIT ?
        """, (process_id, limit))

        return [dict(row) for row in cursor.fetchall()]

    # ==================== Component Types Management ====================

    def get_component_types(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all component types from database

        Args:
            active_only: If True, return only active component types

        Returns:
            List of component type dictionaries
        """
        conn = self.connect()
        query = "SELECT * FROM component_types"

        if active_only:
            query += " WHERE is_active = 1"

        query += " ORDER BY name"

        cursor = conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def get_component_type_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific component type by name

        Args:
            name: Component type name

        Returns:
            Component type dictionary or None if not found
        """
        conn = self.connect()
        cursor = conn.execute("""
            SELECT * FROM component_types
            WHERE name = ?
        """, (name,))

        row = cursor.fetchone()
        return dict(row) if row else None

    def add_component_type(
        self,
        name: str,
        description: str,
        default_config: str,
        is_active: bool = True
    ) -> Optional[int]:
        """
        Add a new component type to database

        Args:
            name: Component type name
            description: Description of the component
            default_config: Default configuration as JSON string
            is_active: Whether the component is active

        Returns:
            ID of created component type, or None if failed
        """
        try:
            with self.transaction() as conn:
                cursor = conn.execute("""
                    INSERT INTO component_types (name, description, default_config, is_active)
                    VALUES (?, ?, ?, ?)
                """, (name, description, default_config, is_active))

                return cursor.lastrowid

        except sqlite3.IntegrityError as e:
            logger.error(f"Component type '{name}' already exists: {e}")
            return None
        except Exception as e:
            logger.error(f"Error adding component type: {e}")
            return None

    def update_component_type(self, component_type_id: int, **kwargs) -> bool:
        """
        Update a component type in database

        Args:
            component_type_id: ID of component type to update
            **kwargs: Fields to update (name, description, default_config, is_active)

        Returns:
            True if successful, False otherwise
        """
        if not kwargs:
            return False

        try:
            # Build UPDATE query dynamically
            fields = []
            values = []

            for key, value in kwargs.items():
                if key in ['name', 'description', 'default_config', 'is_active']:
                    fields.append(f"{key} = ?")
                    values.append(value)

            if not fields:
                return False

            values.append(component_type_id)

            with self.transaction() as conn:
                conn.execute(f"""
                    UPDATE component_types
                    SET {', '.join(fields)}
                    WHERE id = ?
                """, values)

            return True

        except Exception as e:
            logger.error(f"Error updating component type: {e}")
            return False

    def delete_component_type(self, component_type_id: int) -> bool:
        """
        Delete a component type from database

        Args:
            component_type_id: ID of component type to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.transaction() as conn:
                conn.execute("""
                    DELETE FROM component_types
                    WHERE id = ?
                """, (component_type_id,))

            return True

        except Exception as e:
            logger.error(f"Error deleting component type: {e}")
            return False

    # ==================== Panel Settings (Dimensions & Position) ====================

    def save_panel_settings(self, panel_name: str, width: int, height: int, x: int = None, y: int = None):
        """
        Save panel dimensions and position to database

        Args:
            panel_name: Unique identifier for the panel (e.g., 'floating_panel', 'global_search')
            width: Panel width in pixels
            height: Panel height in pixels
            x: X position (optional)
            y: Y position (optional)
        """
        try:
            with self.transaction() as conn:
                conn.execute("""
                    INSERT INTO panel_settings (panel_name, width, height, pos_x, pos_y, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(panel_name)
                    DO UPDATE SET
                        width = excluded.width,
                        height = excluded.height,
                        pos_x = COALESCE(excluded.pos_x, pos_x),
                        pos_y = COALESCE(excluded.pos_y, pos_y),
                        updated_at = CURRENT_TIMESTAMP
                """, (panel_name, width, height, x, y))

            logger.info(f"Panel settings saved: {panel_name} ({width}x{height})")
        except Exception as e:
            logger.error(f"Error saving panel settings: {e}")

    def get_panel_settings(self, panel_name: str) -> Optional[Dict[str, Any]]:
        """
        Get panel dimensions and position from database

        Args:
            panel_name: Unique identifier for the panel

        Returns:
            Dictionary with panel settings or None if not found
            Format: {'width': int, 'height': int, 'pos_x': int, 'pos_y': int}
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT width, height, pos_x, pos_y, updated_at
                FROM panel_settings
                WHERE panel_name = ?
            """, (panel_name,))

            row = cursor.fetchone()

            if row:
                return {
                    'width': row['width'],
                    'height': row['height'],
                    'pos_x': row['pos_x'],
                    'pos_y': row['pos_y'],
                    'updated_at': row['updated_at']
                }

            return None

        except Exception as e:
            logger.error(f"Error getting panel settings: {e}")
            return None

    def reset_panel_settings(self, panel_name: str):
        """
        Reset panel settings to defaults by removing from database

        Args:
            panel_name: Unique identifier for the panel
        """
        try:
            with self.transaction() as conn:
                conn.execute("DELETE FROM panel_settings WHERE panel_name = ?", (panel_name,))

            logger.info(f"Panel settings reset: {panel_name}")
        except Exception as e:
            logger.error(f"Error resetting panel settings: {e}")

    # ==================== Context Manager ====================

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False
