"""
Item Model
"""
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ItemType(Enum):
    """Enum for different types of items"""
    TEXT = "text"
    URL = "url"
    CODE = "code"
    PATH = "path"
    WEB_STATIC = "web_static"


class Item:
    """Model representing a clipboard item"""

    def __init__(
        self,
        item_id: str,
        label: str,
        content: str,
        item_type: ItemType = ItemType.TEXT,
        icon: Optional[str] = None,
        is_sensitive: bool = False,
        is_favorite: bool = False,
        tags: Optional[list] = None,
        description: Optional[str] = None,
        working_dir: Optional[str] = None,
        color: Optional[str] = None,
        is_active: bool = True,
        is_archived: bool = False,
        # Campos para listas avanzadas (nueva arquitectura v3.1.0)
        list_id: Optional[int] = None,
        orden_lista: int = 0,
        # Campos legacy (deprecados - mantener para compatibilidad durante migración)
        is_list: bool = False,
        list_group: Optional[str] = None,
        # Campos de componentes visuales
        is_component: bool = False,
        name_component: Optional[str] = None,
        component_config: Optional[Dict[str, Any]] = None,
        # Campos de metadatos de archivos (TYPE PATH)
        file_size: Optional[int] = None,
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        original_filename: Optional[str] = None,
        file_hash: Optional[str] = None,
        # Campos para tablas (nueva arquitectura v3.1.0)
        table_id: Optional[int] = None,
        orden_table: Optional[str] = None
    ):
        self.id = item_id
        self.label = label
        self.content = content
        self.type = item_type if isinstance(item_type, ItemType) else ItemType(item_type)
        self.icon = icon
        self.is_sensitive = is_sensitive
        self.is_favorite = is_favorite
        self.tags = tags or []
        self.description = description
        self.working_dir = working_dir  # Directorio de trabajo para ejecutar comandos CODE
        self.color = color  # Color para identificación visual
        self.is_active = is_active  # Si el item está activo (puede usarse)
        self.is_archived = is_archived  # Si el item está archivado (oculto por defecto)
        # Campos de listas avanzadas (nueva arquitectura v3.1.0)
        self.list_id = list_id  # FK a tabla listas (None si no es parte de lista)
        self.orden_lista = orden_lista  # Posición del item dentro de la lista (1, 2, 3...)
        # Campos legacy (deprecados - solo para compatibilidad durante migración)
        self.is_list = is_list  # DEPRECADO: usar list_id is not None
        self.list_group = list_group  # DEPRECADO: nombre ahora en tabla listas
        # Campos de componentes visuales
        self.is_component = is_component  # Indica si este item es un componente visual
        self.name_component = name_component  # Tipo de componente (separador, nota, alerta, grupo)
        self.component_config = component_config or {}  # Configuración JSON del componente
        # Campos de metadatos de archivos
        self.file_size = file_size  # Tamaño del archivo en bytes
        self.file_type = file_type  # Tipo de archivo (IMAGEN, VIDEO, PDF, etc.)
        self.file_extension = file_extension  # Extensión con punto (.jpg, .mp4)
        self.original_filename = original_filename  # Nombre original del archivo
        self.file_hash = file_hash  # Hash SHA256 para detección de duplicados
        # Campos para tablas (nueva arquitectura v3.1.0)
        self.table_id = table_id  # FK a tabla tables (None si no es parte de tabla)
        self.orden_table = orden_table  # Coordenadas JSON [row, col] dentro de la tabla
        self.created_at = datetime.now()
        self.last_used = datetime.now()

    def update_last_used(self) -> None:
        """Update the last used timestamp"""
        self.last_used = datetime.now()

    def validate_content(self) -> bool:
        """Validate content based on type"""
        if not self.content:
            return False

        if self.type == ItemType.URL:
            return self.content.startswith(('http://', 'https://', 'www.'))

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert item to dictionary"""
        return {
            "id": self.id,
            "label": self.label,
            "content": self.content,
            "type": self.type.value if isinstance(self.type, ItemType) else self.type,
            "icon": self.icon,
            "is_sensitive": self.is_sensitive,
            "is_favorite": self.is_favorite,
            "tags": self.tags,
            "description": self.description,
            "working_dir": self.working_dir,
            "color": self.color,
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            # Campos de listas avanzadas (nueva arquitectura v3.1.0)
            "list_id": self.list_id,
            "orden_lista": self.orden_lista,
            # Campos legacy (deprecados)
            "is_list": self.is_list,
            "list_group": self.list_group,
            # Campos de componentes visuales
            "is_component": self.is_component,
            "name_component": self.name_component,
            "component_config": self.component_config,
            # Campos de metadatos de archivos
            "file_size": self.file_size,
            "file_type": self.file_type,
            "file_extension": self.file_extension,
            "original_filename": self.original_filename,
            "file_hash": self.file_hash,
            # Campos de tablas (nueva arquitectura v3.1.0)
            "table_id": self.table_id,
            "orden_table": self.orden_table
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Item':
        """Create an Item from a dictionary"""
        # Generate ID from label if not provided
        item_id = data.get("id", data.get("label", "").lower().replace(" ", "_"))

        item_type_str = data.get("type", "text")
        item_type = ItemType(item_type_str) if item_type_str in [t.value for t in ItemType] else ItemType.TEXT

        return cls(
            item_id=item_id,
            label=data.get("label", ""),
            content=data.get("content", ""),
            item_type=item_type,
            icon=data.get("icon"),
            is_sensitive=data.get("is_sensitive", False),
            is_favorite=data.get("is_favorite", False),
            tags=data.get("tags", []),
            description=data.get("description"),
            working_dir=data.get("working_dir"),
            color=data.get("color"),
            is_active=data.get("is_active", True),
            is_archived=data.get("is_archived", False),
            # Campos de listas avanzadas (nueva arquitectura v3.1.0)
            list_id=data.get("list_id"),
            orden_lista=data.get("orden_lista", 0),
            # Campos legacy (deprecados)
            is_list=data.get("is_list", False),
            list_group=data.get("list_group"),
            # Campos de componentes visuales
            is_component=data.get("is_component", False),
            name_component=data.get("name_component"),
            component_config=data.get("component_config"),
            # Campos de metadatos de archivos
            file_size=data.get("file_size"),
            file_type=data.get("file_type"),
            file_extension=data.get("file_extension"),
            original_filename=data.get("original_filename"),
            file_hash=data.get("file_hash"),
            # Campos de tablas (nueva arquitectura v3.1.0)
            table_id=data.get("table_id"),
            orden_table=data.get("orden_table")
        )

    # Estado y visibilidad
    def is_visible(self) -> bool:
        """Retorna True si el item está activo y NO archivado (visible por defecto)"""
        return self.is_active and not self.is_archived

    def can_use(self) -> bool:
        """Retorna True si el item puede ser usado (activo, independiente de si está archivado)"""
        return self.is_active

    def archive(self) -> None:
        """Archivar el item (ocultar de vista por defecto)"""
        self.is_archived = True

    def unarchive(self) -> None:
        """Desarchivar el item (volver a vista por defecto)"""
        self.is_archived = False

    def activate(self) -> None:
        """Activar el item (puede ser usado)"""
        self.is_active = True

    def deactivate(self) -> None:
        """Desactivar el item (no puede ser usado)"""
        self.is_active = False

    # Métodos para listas avanzadas (nueva arquitectura v3.1.0)
    def is_list_item(self) -> bool:
        """
        Retorna True si este item es parte de una lista

        Returns:
            bool: True si el item pertenece a una lista (list_id is not None)
        """
        return self.list_id is not None

    def get_list_id(self) -> Optional[int]:
        """
        Retorna el ID de la lista a la que pertenece este item

        Returns:
            Optional[int]: list_id o None si no pertenece a ninguna lista
        """
        return self.list_id if self.is_list_item() else None

    def get_orden_lista(self) -> int:
        """
        Retorna la posición de este item dentro de su lista

        Returns:
            int: Posición (1, 2, 3...) o 0 si no es parte de lista
        """
        return self.orden_lista if self.is_list_item() else 0

    def set_as_list_item(self, list_id: int, orden: int) -> None:
        """
        Configura este item como parte de una lista

        Args:
            list_id: ID de la lista (FK a tabla listas)
            orden: Posición del item dentro de la lista (1, 2, 3...)
        """
        self.list_id = list_id
        self.orden_lista = orden
        # Actualizar campos legacy para compatibilidad backward
        self.is_list = True

    def remove_from_list(self) -> None:
        """Remueve este item de cualquier lista (lo convierte en item normal)"""
        self.list_id = None
        self.orden_lista = 0
        # Actualizar campos legacy para compatibilidad backward
        self.is_list = False
        self.list_group = None

    # Métodos legacy (deprecados - mantener para compatibilidad durante migración)
    def get_list_group(self) -> Optional[str]:
        """
        DEPRECADO: Usar get_list_id() en su lugar
        Retorna el nombre del grupo de lista (campo legacy)
        """
        return self.list_group if self.is_list else None

    # Métodos para archivos (TYPE PATH)
    def get_formatted_file_size(self) -> str:
        """
        Retorna el tamaño del archivo formateado de forma legible

        Returns:
            str: Tamaño formateado (ej: "2.5 MB", "1.2 GB") o vacío si no hay file_size
        """
        if not self.file_size:
            return ""

        size = float(self.file_size)
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0

        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1

        # Formatear con decimales apropiados
        if unit_index == 0:  # Bytes
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"

    def get_file_type_icon(self) -> str:
        """
        Retorna el emoji correspondiente al tipo de archivo

        Returns:
            str: Emoji representativo del tipo de archivo
        """
        # Diccionario de iconos por tipo
        icons = {
            'IMAGEN': '🖼️',
            'VIDEO': '🎬',
            'PDF': '📕',
            'WORD': '📘',
            'EXCEL': '📊',
            'TEXT': '📄',
            'OTROS': '📎'
        }

        if not self.file_type:
            return '📎'  # Icono por defecto

        return icons.get(self.file_type.upper(), '📎')

    def is_file_item(self) -> bool:
        """
        Verifica si este item es un archivo (TYPE PATH con metadatos)

        Returns:
            bool: True si es un item de archivo con metadatos
        """
        return self.type == ItemType.PATH and self.file_hash is not None

    # Métodos para componentes visuales
    def is_component_item(self) -> bool:
        """Retorna True si este item es un componente visual"""
        return self.is_component == True or self.is_component == 1

    def get_component_type(self) -> Optional[str]:
        """Retorna el tipo de componente (separador, nota, alerta, grupo) o None"""
        return self.name_component if self.is_component_item() else None

    def get_component_config(self) -> Dict[str, Any]:
        """Retorna la configuración del componente (diccionario vacío si no es componente)"""
        return self.component_config if self.is_component_item() and self.component_config else {}

    def set_as_component(self, component_type: str, config: Dict[str, Any]) -> None:
        """
        Configura este item como componente visual

        Args:
            component_type: Tipo de componente (separador, nota, alerta, grupo)
            config: Diccionario de configuración del componente
        """
        self.is_component = True
        self.name_component = component_type
        self.component_config = config

    def remove_component_status(self) -> None:
        """Remueve el estado de componente de este item (lo convierte en item normal)"""
        self.is_component = False
        self.name_component = None
        self.component_config = {}

    # Métodos para tablas (nueva arquitectura v3.1.0)
    def is_table_item(self) -> bool:
        """
        Retorna True si este item es parte de una tabla

        Returns:
            bool: True si el item pertenece a una tabla (table_id is not None)
        """
        return self.table_id is not None

    def get_table_id(self) -> Optional[int]:
        """
        Retorna el ID de la tabla a la que pertenece este item

        Returns:
            Optional[int]: table_id o None si no pertenece a ninguna tabla
        """
        return self.table_id if self.is_table_item() else None

    def get_table_coordinates(self) -> Optional[list]:
        """
        Retorna las coordenadas [row, col] de este item en la tabla

        Returns:
            Optional[list]: [row, col] o None si no es parte de tabla o no tiene coordenadas
        """
        if not self.is_table_item() or not self.orden_table:
            return None
        try:
            import json
            return json.loads(self.orden_table)
        except:
            return None

    def set_as_table_item(self, table_id: int, row: int, col: int) -> None:
        """
        Configura este item como parte de una tabla

        Args:
            table_id: ID de la tabla (FK a tabla tables)
            row: Fila en la tabla (0-indexed)
            col: Columna en la tabla (0-indexed)
        """
        import json
        self.table_id = table_id
        self.orden_table = json.dumps([row, col])

    def remove_from_table(self) -> None:
        """Remueve este item de cualquier tabla (lo convierte en item normal)"""
        self.table_id = None
        self.orden_table = None

    def __repr__(self) -> str:
        list_info = f", list_id={self.list_id}[{self.orden_lista}]" if self.is_list_item() else ""
        component_info = f", component={self.name_component}" if self.is_component_item() else ""
        return f"Item(id={self.id}, label={self.label}, type={self.type.value}{list_info}{component_info})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Item):
            return False
        return self.id == other.id
