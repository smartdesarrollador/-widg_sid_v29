"""
Project Element Tag Manager - Gestión de lógica de negocio de tags

Responsabilidades:
- Gestión de tags de elementos de proyecto con caché
- Validaciones de negocio
- Emisión de señales PyQt6
- Métodos de utilidad y estadísticas
- Gestión de asociaciones tag-elemento
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from PyQt6.QtCore import QObject, pyqtSignal

from src.database.db_manager import DBManager
from src.models.project_element_tag import (
    ProjectElementTag,
    create_tag_from_db_row,
    filter_tags_by_name,
    sort_tags_by_name
)

logger = logging.getLogger(__name__)


class ProjectElementTagManager(QObject):
    """
    Manager para gestión de tags de elementos de proyecto

    Maneja lógica de negocio, caché, validaciones y señales para tags
    que se asignan a elementos dentro de proyectos.
    """

    # Señales PyQt6
    tag_created = pyqtSignal(dict)      # tag_data
    tag_updated = pyqtSignal(dict)      # tag_data
    tag_deleted = pyqtSignal(int)       # tag_id
    tag_associated = pyqtSignal(int, int)  # relation_id, tag_id
    tag_removed = pyqtSignal(int, int)     # relation_id, tag_id
    cache_invalidated = pyqtSignal()

    def __init__(self, db_manager: DBManager):
        """
        Inicializa el manager

        Args:
            db_manager: Instancia de DBManager para operaciones de BD
        """
        super().__init__()
        self.db = db_manager
        self._tags_cache: Optional[Dict[int, ProjectElementTag]] = None  # Lazy loading
        self._cache_enabled = True
        logger.info("ProjectElementTagManager initialized")

    # ==================== CACHE ====================

    def invalidate_cache(self):
        """Invalida el caché de tags"""
        self._tags_cache = None
        self.cache_invalidated.emit()
        logger.debug("Tags cache invalidated")

    def _cache_tag(self, tag: ProjectElementTag):
        """
        Agrega un tag al caché

        Args:
            tag: Tag a agregar al caché
        """
        if self._cache_enabled and tag:
            if self._tags_cache is None:
                self._tags_cache = {}
            self._tags_cache[tag.id] = tag

    def _get_from_cache(self, tag_id: int) -> Optional[ProjectElementTag]:
        """
        Obtiene un tag del caché

        Args:
            tag_id: ID del tag

        Returns:
            Tag desde el caché o None si no existe
        """
        if self._cache_enabled and self._tags_cache is not None:
            return self._tags_cache.get(tag_id)
        return None

    def _load_cache(self, force: bool = False):
        """
        Carga todos los tags en el caché

        Args:
            force: Si True, fuerza la recarga aunque ya esté cargado
        """
        if not self._cache_enabled:
            return

        if self._tags_cache is not None and not force:
            return

        try:
            all_tags_data = self.db.get_all_project_element_tags()
            self._tags_cache = {}

            for tag_data in all_tags_data:
                tag = create_tag_from_db_row(tag_data)
                self._tags_cache[tag.id] = tag

            logger.debug(f"Tags cache loaded: {len(self._tags_cache)} tags")

        except Exception as e:
            logger.error(f"Error loading tags cache: {e}")

    # ==================== GESTIÓN DE TAGS ====================

    def create_tag(self, name: str, color: str = "#3498db",
                   description: str = "") -> Optional[ProjectElementTag]:
        """
        Crea un nuevo tag con validación

        Args:
            name: Nombre del tag (único)
            color: Color en formato hex
            description: Descripción del tag

        Returns:
            Tag creado o None si falla
        """
        # Validar nombre
        is_valid, error_msg = self.validate_tag_name(name)
        if not is_valid:
            logger.error(f"Validación fallida: {error_msg}")
            return None

        # Validar color
        if not self.validate_color(color):
            logger.error(f"Color inválido: {color}")
            return None

        try:
            tag_id = self.db.add_project_element_tag(name, color, description)
            tag_data = self.db.get_project_element_tag_by_id(tag_id)

            if tag_data:
                tag = create_tag_from_db_row(tag_data)
                self._cache_tag(tag)
                self.tag_created.emit(tag_data)
                logger.info(f"Tag creado: {name} (ID: {tag_id})")
                return tag

            return None

        except ValueError as e:
            # Ya existe un tag con ese nombre
            logger.error(f"Error creando tag: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creando tag: {e}")
            return None

    def get_all_tags(self, refresh: bool = False) -> List[ProjectElementTag]:
        """
        Obtiene todos los tags (con caché)

        Args:
            refresh: Si True, recarga desde BD

        Returns:
            Lista de tags
        """
        if refresh or self._tags_cache is None:
            self._load_cache(force=refresh)

        return list(self._tags_cache.values() if self._tags_cache else [])

    def get_tag(self, tag_id: int) -> Optional[ProjectElementTag]:
        """
        Obtiene un tag por ID (usa caché)

        Args:
            tag_id: ID del tag

        Returns:
            Tag o None si no existe
        """
        # Intentar desde caché
        cached = self._get_from_cache(tag_id)
        if cached:
            return cached

        # Obtener de BD
        tag_data = self.db.get_project_element_tag_by_id(tag_id)
        if tag_data:
            tag = create_tag_from_db_row(tag_data)
            self._cache_tag(tag)
            return tag

        return None

    def get_tag_by_name(self, name: str) -> Optional[ProjectElementTag]:
        """
        Obtiene un tag por nombre

        Args:
            name: Nombre del tag

        Returns:
            Tag o None si no existe
        """
        tag_data = self.db.get_project_element_tag_by_name(name)
        if tag_data:
            tag = create_tag_from_db_row(tag_data)
            self._cache_tag(tag)
            return tag

        return None

    def update_tag(self, tag_id: int, name: str = None,
                   color: str = None, description: str = None) -> bool:
        """
        Actualiza un tag con validación

        Args:
            tag_id: ID del tag
            name: Nuevo nombre (opcional)
            color: Nuevo color (opcional)
            description: Nueva descripción (opcional)

        Returns:
            True si se actualizó correctamente
        """
        # Validar nombre si se proporciona
        if name is not None:
            is_valid, error_msg = self.validate_tag_name(name)
            if not is_valid:
                logger.error(f"Validación fallida: {error_msg}")
                return False

        # Validar color si se proporciona
        if color is not None and not self.validate_color(color):
            logger.error(f"Color inválido: {color}")
            return False

        try:
            success = self.db.update_project_element_tag(tag_id, name, color, description)

            if success:
                # Invalidar caché de este tag
                if tag_id in self._tags_cache:
                    del self._tags_cache[tag_id]

                # Obtener tag actualizado y emitir señal
                tag_data = self.db.get_project_element_tag_by_id(tag_id)
                if tag_data:
                    tag = create_tag_from_db_row(tag_data)
                    self._cache_tag(tag)
                    self.tag_updated.emit(tag_data)

                logger.info(f"Tag {tag_id} actualizado")

            return success

        except ValueError as e:
            # Nombre duplicado
            logger.error(f"Error actualizando tag: {e}")
            return False
        except Exception as e:
            logger.error(f"Error actualizando tag: {e}")
            return False

    def delete_tag(self, tag_id: int) -> bool:
        """
        Elimina un tag (verifica uso antes de eliminar)

        Args:
            tag_id: ID del tag

        Returns:
            True si se eliminó correctamente
        """
        # Verificar uso del tag
        usage_count = self.db.get_tag_usage_count(tag_id)
        if usage_count > 0:
            logger.warning(f"Tag {tag_id} está en uso ({usage_count} relaciones)")
            # Nota: Aún así se puede eliminar gracias a CASCADE
            # pero advertimos al usuario

        try:
            success = self.db.delete_project_element_tag(tag_id)

            if success:
                # Remover del caché
                if tag_id in self._tags_cache:
                    del self._tags_cache[tag_id]

                self.tag_deleted.emit(tag_id)
                logger.info(f"Tag {tag_id} eliminado")

            return success

        except Exception as e:
            logger.error(f"Error eliminando tag {tag_id}: {e}")
            return False

    def search_tags(self, query: str) -> List[ProjectElementTag]:
        """
        Busca tags por nombre

        Args:
            query: Texto a buscar

        Returns:
            Lista de tags que coinciden
        """
        if not query:
            return self.get_all_tags()

        try:
            tags_data = self.db.search_project_element_tags(query)
            tags = [create_tag_from_db_row(tag_data) for tag_data in tags_data]

            # Agregar al caché
            for tag in tags:
                self._cache_tag(tag)

            return tags

        except Exception as e:
            logger.error(f"Error buscando tags: {e}")
            return []

    # ==================== ASOCIACIONES ====================

    def assign_tags_to_relation(self, relation_id: int, tag_ids: List[int]) -> bool:
        """
        Asigna múltiples tags a una relación de proyecto

        Args:
            relation_id: ID de la relación
            tag_ids: Lista de IDs de tags

        Returns:
            True si se asignaron correctamente
        """
        try:
            success = self.db.update_project_relation_tags(relation_id, tag_ids)

            if success:
                # Emitir señal por cada tag asociado
                for tag_id in tag_ids:
                    self.tag_associated.emit(relation_id, tag_id)

                logger.info(f"Tags asignados a relación {relation_id}: {len(tag_ids)} tags")

            return success

        except Exception as e:
            logger.error(f"Error asignando tags: {e}")
            return False

    def add_tag_to_relation(self, relation_id: int, tag_id: int) -> bool:
        """
        Agrega un tag a una relación

        Args:
            relation_id: ID de la relación
            tag_id: ID del tag

        Returns:
            True si se agregó correctamente
        """
        try:
            success = self.db.add_tag_to_project_relation(relation_id, tag_id)

            if success:
                self.tag_associated.emit(relation_id, tag_id)
                logger.info(f"Tag {tag_id} asociado a relación {relation_id}")

            return success

        except Exception as e:
            logger.error(f"Error agregando tag: {e}")
            return False

    def remove_tag_from_relation(self, relation_id: int, tag_id: int) -> bool:
        """
        Remueve un tag de una relación

        Args:
            relation_id: ID de la relación
            tag_id: ID del tag

        Returns:
            True si se removió correctamente
        """
        try:
            success = self.db.remove_tag_from_project_relation(relation_id, tag_id)

            if success:
                self.tag_removed.emit(relation_id, tag_id)
                logger.info(f"Tag {tag_id} removido de relación {relation_id}")

            return success

        except Exception as e:
            logger.error(f"Error removiendo tag: {e}")
            return False

    def get_relation_tags(self, relation_id: int) -> List[ProjectElementTag]:
        """
        Obtiene todos los tags de una relación

        Args:
            relation_id: ID de la relación

        Returns:
            Lista de tags
        """
        try:
            tags_data = self.db.get_tags_for_project_relation(relation_id)
            tags = [create_tag_from_db_row(tag_data) for tag_data in tags_data]

            # Agregar al caché
            for tag in tags:
                self._cache_tag(tag)

            return tags

        except Exception as e:
            logger.error(f"Error obteniendo tags de relación: {e}")
            return []

    def get_relations_by_tag(self, tag_id: int) -> List[int]:
        """
        Obtiene IDs de relaciones que tienen un tag

        Args:
            tag_id: ID del tag

        Returns:
            Lista de IDs de relaciones
        """
        try:
            relations = self.db.get_project_relations_by_tag(tag_id)
            return [rel['id'] for rel in relations]

        except Exception as e:
            logger.error(f"Error obteniendo relaciones por tag: {e}")
            return []

    # ==================== COMPONENTES ====================

    def assign_tags_to_component(self, component_id: int, tag_ids: List[int]) -> bool:
        """
        Asigna tags a un componente (reemplaza existentes)

        Args:
            component_id: ID del componente
            tag_ids: Lista de IDs de tags a asignar

        Returns:
            True si se asignaron correctamente
        """
        try:
            success = self.db.update_project_component_tags(component_id, tag_ids)

            if success:
                # Emitir señal por cada tag asociado
                for tag_id in tag_ids:
                    self.tag_associated.emit(component_id, tag_id)

                logger.info(f"Tags asignados a componente {component_id}: {len(tag_ids)} tags")

            return success

        except Exception as e:
            logger.error(f"Error asignando tags al componente: {e}")
            return False

    def add_tag_to_component(self, component_id: int, tag_id: int) -> bool:
        """
        Agrega un tag a un componente

        Args:
            component_id: ID del componente
            tag_id: ID del tag

        Returns:
            True si se agregó correctamente
        """
        try:
            success = self.db.add_tag_to_project_component(component_id, tag_id)

            if success:
                self.tag_associated.emit(component_id, tag_id)
                logger.info(f"Tag {tag_id} asociado a componente {component_id}")

            return success

        except Exception as e:
            logger.error(f"Error agregando tag al componente: {e}")
            return False

    def remove_tag_from_component(self, component_id: int, tag_id: int) -> bool:
        """
        Remueve un tag de un componente

        Args:
            component_id: ID del componente
            tag_id: ID del tag

        Returns:
            True si se removió correctamente
        """
        try:
            success = self.db.remove_tag_from_project_component(component_id, tag_id)

            if success:
                self.tag_removed.emit(component_id, tag_id)
                logger.info(f"Tag {tag_id} removido de componente {component_id}")

            return success

        except Exception as e:
            logger.error(f"Error removiendo tag del componente: {e}")
            return False

    def get_tags_for_component(self, component_id: int) -> List[ProjectElementTag]:
        """
        Obtiene tags de un componente

        Args:
            component_id: ID del componente

        Returns:
            Lista de tags del componente
        """
        try:
            tags_data = self.db.get_tags_for_project_component(component_id)
            return [create_tag_from_db_row(tag_data) for tag_data in tags_data]

        except Exception as e:
            logger.error(f"Error obteniendo tags del componente: {e}")
            return []

    def get_components_by_tag(self, tag_id: int) -> List[int]:
        """
        Obtiene IDs de componentes que tienen un tag

        Args:
            tag_id: ID del tag

        Returns:
            Lista de IDs de componentes
        """
        try:
            components = self.db.get_project_components_by_tag(tag_id)
            return [comp['id'] for comp in components]

        except Exception as e:
            logger.error(f"Error obteniendo componentes por tag: {e}")
            return []

    # ==================== UTILIDADES ====================

    def get_tag_usage_count(self, tag_id: int) -> int:
        """
        Obtiene el conteo de uso de un tag

        Args:
            tag_id: ID del tag

        Returns:
            Número de relaciones que usan el tag
        """
        try:
            return self.db.get_tag_usage_count(tag_id)
        except Exception as e:
            logger.error(f"Error obteniendo conteo de uso: {e}")
            return 0

    def get_popular_tags(self, limit: int = 10) -> List[Tuple[ProjectElementTag, int]]:
        """
        Obtiene los tags más usados

        Args:
            limit: Número máximo de tags a retornar

        Returns:
            Lista de tuplas (tag, conteo de uso)
        """
        try:
            popular_data = self.db.get_popular_project_element_tags(limit)
            result = []

            for tag_data in popular_data:
                tag = create_tag_from_db_row(tag_data)
                usage_count = tag_data.get('usage_count', 0)
                result.append((tag, usage_count))

                # Agregar al caché
                self._cache_tag(tag)

            return result

        except Exception as e:
            logger.error(f"Error obteniendo tags populares: {e}")
            return []

    def get_tags_sorted(self, reverse: bool = False) -> List[ProjectElementTag]:
        """
        Obtiene todos los tags ordenados alfabéticamente

        Args:
            reverse: Si True, orden descendente

        Returns:
            Lista de tags ordenados
        """
        tags = self.get_all_tags()
        return sort_tags_by_name(tags, reverse=reverse)

    def get_tags_for_project(self, project_id: int) -> List[ProjectElementTag]:
        """
        Obtiene los tags únicos usados en un proyecto específico
        (incluye tags de relaciones y componentes)

        Args:
            project_id: ID del proyecto

        Returns:
            Lista de tags únicos usados en el proyecto, ordenados por nombre
        """
        try:
            # Recopilar IDs de tags únicos
            tag_ids = set()

            # 1. Obtener tags de relaciones
            relations = self.db.get_project_relations(project_id)
            for relation in relations:
                tags_data = self.db.get_tags_for_project_relation(relation['id'])
                for tag_data in tags_data:
                    tag_ids.add(tag_data['id'])

            # 2. Obtener tags de componentes
            components = self.db.get_project_components(project_id)
            for component in components:
                tags_data = self.db.get_tags_for_project_component(component['id'])
                for tag_data in tags_data:
                    tag_ids.add(tag_data['id'])

            # Obtener objetos Tag completos
            tags = []
            for tag_id in tag_ids:
                tag = self.get_tag(tag_id)
                if tag:
                    tags.append(tag)

            # Ordenar por nombre
            return sort_tags_by_name(tags)

        except Exception as e:
            logger.error(f"Error obteniendo tags del proyecto {project_id}: {e}")
            return []

    def filter_tags(self, query: str) -> List[ProjectElementTag]:
        """
        Filtra tags desde el caché (más rápido que búsqueda en BD)

        Args:
            query: Texto a buscar

        Returns:
            Lista de tags filtrados
        """
        if not query:
            return self.get_all_tags()

        tags = self.get_all_tags()
        return filter_tags_by_name(tags, query)

    # ==================== VALIDACIONES ====================

    def validate_tag_name(self, name: str) -> Tuple[bool, str]:
        """
        Valida el nombre de un tag

        Args:
            name: Nombre a validar

        Returns:
            Tupla (es_válido, mensaje_error)
        """
        if not name or not name.strip():
            return False, "El nombre no puede estar vacío"

        if len(name) > 50:
            return False, "El nombre no puede exceder 50 caracteres"

        # Validar caracteres permitidos (alfanuméricos, espacios, guiones, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9\s_-]+$', name):
            return False, "El nombre solo puede contener letras, números, espacios, guiones y underscores"

        return True, ""

    def validate_color(self, color: str) -> bool:
        """
        Valida formato de color hex

        Args:
            color: Color a validar

        Returns:
            True si es válido
        """
        if not color:
            return False

        import re
        # Formato: #RRGGBB o #RGB
        pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
        return bool(re.match(pattern, color))

    # ==================== OPERACIONES BATCH ====================

    def create_tags_batch(self, tags_data: List[Dict[str, str]]) -> List[Optional[ProjectElementTag]]:
        """
        Crea múltiples tags en batch

        Args:
            tags_data: Lista de diccionarios con datos de tags
                      [{'name': 'python', 'color': '#3776ab', 'description': '...'}, ...]

        Returns:
            Lista de tags creados (None en posiciones donde falló)
        """
        results = []

        for tag_data in tags_data:
            name = tag_data.get('name')
            color = tag_data.get('color', '#3498db')
            description = tag_data.get('description', '')

            tag = self.create_tag(name, color, description)
            results.append(tag)

        logger.info(f"Batch creation: {len([t for t in results if t])} de {len(tags_data)} tags creados")
        return results

    def delete_tags_batch(self, tag_ids: List[int]) -> int:
        """
        Elimina múltiples tags

        Args:
            tag_ids: Lista de IDs de tags a eliminar

        Returns:
            Número de tags eliminados exitosamente
        """
        deleted_count = 0

        for tag_id in tag_ids:
            if self.delete_tag(tag_id):
                deleted_count += 1

        logger.info(f"Batch deletion: {deleted_count} de {len(tag_ids)} tags eliminados")
        return deleted_count
