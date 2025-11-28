# -*- coding: utf-8 -*-
"""
Image Gallery Controller

Controlador para el visor de galería de imágenes.
Gestiona la lógica de negocio, paginación, filtros y caché de thumbnails.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from src.database.db_manager import DBManager
from src.utils.thumbnail_cache import ThumbnailCache

logger = logging.getLogger(__name__)


class ImageGalleryController(QObject):
    """
    Controlador para galería de imágenes

    Responsabilidades:
    - Cargar imágenes desde BD con filtros
    - Gestionar paginación
    - Coordinar caché de thumbnails
    - Aplicar filtros de búsqueda
    - Emitir señales para actualizar UI
    """

    # Señales
    images_loaded = pyqtSignal(list)  # Lista de imágenes cargadas
    page_changed = pyqtSignal(int, int)  # (página_actual, total_páginas)
    filters_applied = pyqtSignal(dict)  # Filtros aplicados
    loading_started = pyqtSignal()  # Inicia carga
    loading_finished = pyqtSignal()  # Termina carga
    error_occurred = pyqtSignal(str)  # Error con mensaje

    def __init__(self, db_manager: DBManager, main_controller=None):
        """
        Inicializar controller

        Args:
            db_manager: Instancia de DBManager
            main_controller: Referencia al MainController (opcional)
        """
        super().__init__()

        self.db = db_manager
        self.main_controller = main_controller

        # Thumbnail cache
        self.thumbnail_cache = ThumbnailCache()

        # Estado de paginación
        self.current_page = 1
        self.items_per_page = 50
        self.total_items = 0
        self.total_pages = 0

        # Estado de filtros
        self.active_filters = {
            'category_id': None,
            'search_text': None,
            'tags': None,
            'is_favorite': None,
            'date_from': None,
            'date_to': None,
            'min_size': None,
            'max_size': None
        }

        # Caché de imágenes cargadas
        self.current_images = []

        # Carpeta de imágenes relativa a files_base_path
        self.images_folder = "IMAGENES"

        logger.info("ImageGalleryController initialized")

    def _get_images_base_path(self) -> str:
        """
        Obtener la ruta base para imágenes (files_base_path + IMAGENES)

        Returns:
            str: Ruta base completa para imágenes
        """
        try:
            # Try to get config from main_controller (can be 'config' or 'config_manager')
            config = None
            if self.main_controller:
                if hasattr(self.main_controller, 'config_manager'):
                    config = self.main_controller.config_manager
                elif hasattr(self.main_controller, 'config'):
                    config = self.main_controller.config

            if config:
                files_base_path = config.get_files_base_path()
                if files_base_path:
                    return os.path.join(files_base_path, self.images_folder)

            # Fallback: usar directorio de la aplicación
            return os.path.join(os.getcwd(), self.images_folder)
        except Exception as e:
            logger.error(f"Error getting images base path: {e}")
            return os.path.join(os.getcwd(), self.images_folder)

    def _resolve_image_path(self, relative_path: str) -> str:
        """
        Convertir ruta relativa a ruta absoluta

        Args:
            relative_path: Ruta relativa almacenada en BD

        Returns:
            str: Ruta absoluta completa
        """
        try:
            base_path = self._get_images_base_path()
            absolute_path = os.path.join(base_path, relative_path)
            return os.path.normpath(absolute_path)
        except Exception as e:
            logger.error(f"Error resolving image path: {e}")
            return relative_path

    def _make_relative_path(self, absolute_path: str) -> str:
        """
        Convertir ruta absoluta a ruta relativa (para guardar en BD)

        Args:
            absolute_path: Ruta absoluta del archivo

        Returns:
            str: Ruta relativa desde images_base_path
        """
        try:
            base_path = self._get_images_base_path()
            relative = os.path.relpath(absolute_path, base_path)
            return relative
        except Exception as e:
            logger.error(f"Error making relative path: {e}")
            return absolute_path

    def _resolve_images_paths(self, images: List[Dict]) -> List[Dict]:
        """
        Resolver rutas relativas a absolutas para una lista de imágenes

        Args:
            images: Lista de dicts con rutas relativas en 'content'

        Returns:
            Lista de dicts con rutas absolutas en 'content' y relativas en 'relative_path'
        """
        for image in images:
            if 'content' in image:
                relative_path = image['content']
                absolute_path = self._resolve_image_path(relative_path)

                # Guardar ambas rutas
                image['relative_path'] = relative_path
                image['content'] = absolute_path

        return images

    def load_images(self, page: int = 1, apply_filters: bool = True) -> List[Dict]:
        """
        Cargar imágenes con paginación

        Args:
            page: Número de página (1-indexed)
            apply_filters: Si aplicar filtros activos

        Returns:
            Lista de diccionarios con datos de imágenes
        """
        try:
            self.loading_started.emit()

            # Validar página
            if page < 1:
                page = 1

            self.current_page = page

            # Calcular offset
            offset = (page - 1) * self.items_per_page

            # Preparar parámetros de query
            query_params = {
                'limit': self.items_per_page,
                'offset': offset
            }

            # Aplicar filtros si está habilitado
            if apply_filters:
                for key, value in self.active_filters.items():
                    if value is not None:
                        query_params[key] = value

            # Obtener imágenes desde BD
            logger.debug(f"Loading images: page={page}, offset={offset}, filters={apply_filters}")
            images = self.db.get_image_items(**query_params)

            # Resolver rutas relativas a absolutas
            images = self._resolve_images_paths(images)

            # Actualizar contador total
            count_params = {k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
            self.total_items = self.db.get_image_count(**count_params)
            self.total_pages = max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)

            # Guardar imágenes actuales
            self.current_images = images

            logger.info(f"Loaded {len(images)} images (page {page}/{self.total_pages})")

            # Emitir señales
            self.images_loaded.emit(images)
            self.page_changed.emit(self.current_page, self.total_pages)

            return images

        except Exception as e:
            logger.error(f"Error loading images: {e}", exc_info=True)
            self.error_occurred.emit(f"Error al cargar imágenes: {str(e)}")
            return []

        finally:
            self.loading_finished.emit()

    def next_page(self) -> List[Dict]:
        """
        Cargar siguiente página

        Returns:
            Lista de imágenes de la página siguiente
        """
        if self.current_page < self.total_pages:
            return self.load_images(self.current_page + 1)
        else:
            logger.debug("Already on last page")
            return self.current_images

    def previous_page(self) -> List[Dict]:
        """
        Cargar página anterior

        Returns:
            Lista de imágenes de la página anterior
        """
        if self.current_page > 1:
            return self.load_images(self.current_page - 1)
        else:
            logger.debug("Already on first page")
            return self.current_images

    def go_to_page(self, page: int) -> List[Dict]:
        """
        Ir a página específica

        Args:
            page: Número de página

        Returns:
            Lista de imágenes de la página
        """
        if 1 <= page <= self.total_pages:
            return self.load_images(page)
        else:
            logger.warning(f"Invalid page number: {page} (total: {self.total_pages})")
            return self.current_images

    def apply_filters(self, **filters) -> List[Dict]:
        """
        Aplicar filtros y recargar imágenes

        Args:
            **filters: Filtros a aplicar (category_id, search_text, tags, etc.)

        Returns:
            Lista de imágenes filtradas
        """
        # Actualizar filtros activos
        for key, value in filters.items():
            if key in self.active_filters:
                self.active_filters[key] = value

        logger.info(f"Filters applied: {filters}")
        self.filters_applied.emit(self.active_filters.copy())

        # Recargar desde página 1
        return self.load_images(page=1, apply_filters=True)

    def clear_filters(self) -> List[Dict]:
        """
        Limpiar todos los filtros

        Returns:
            Lista de todas las imágenes sin filtros
        """
        # Resetear filtros
        for key in self.active_filters:
            self.active_filters[key] = None

        logger.info("Filters cleared")
        self.filters_applied.emit(self.active_filters.copy())

        # Recargar desde página 1
        return self.load_images(page=1, apply_filters=False)

    def search_by_text(self, text: str) -> List[Dict]:
        """
        Buscar imágenes por texto

        Args:
            text: Texto a buscar en nombre/descripción

        Returns:
            Lista de imágenes que coinciden
        """
        search_text = text.strip() if text else None
        return self.apply_filters(search_text=search_text)

    def filter_by_category(self, category_id: Optional[int]) -> List[Dict]:
        """
        Filtrar por categoría

        Args:
            category_id: ID de categoría o None para todas

        Returns:
            Lista de imágenes de la categoría
        """
        return self.apply_filters(category_id=category_id)

    def filter_by_tags(self, tags: Optional[List[str]]) -> List[Dict]:
        """
        Filtrar por tags

        Args:
            tags: Lista de tags o None

        Returns:
            Lista de imágenes con los tags
        """
        return self.apply_filters(tags=tags)

    def filter_by_favorite(self, favorites_only: bool) -> List[Dict]:
        """
        Filtrar por favoritos

        Args:
            favorites_only: Si True, solo favoritos

        Returns:
            Lista de imágenes favoritas
        """
        is_favorite = True if favorites_only else None
        return self.apply_filters(is_favorite=is_favorite)

    def filter_by_date_range(self, date_from: Optional[str], date_to: Optional[str]) -> List[Dict]:
        """
        Filtrar por rango de fechas

        Args:
            date_from: Fecha inicio (YYYY-MM-DD)
            date_to: Fecha fin (YYYY-MM-DD)

        Returns:
            Lista de imágenes en el rango
        """
        return self.apply_filters(date_from=date_from, date_to=date_to)

    def filter_by_size_range(self, min_size: Optional[int], max_size: Optional[int]) -> List[Dict]:
        """
        Filtrar por tamaño de archivo

        Args:
            min_size: Tamaño mínimo en bytes
            max_size: Tamaño máximo en bytes

        Returns:
            Lista de imágenes en el rango
        """
        return self.apply_filters(min_size=min_size, max_size=max_size)

    def get_thumbnail(self, image_path: str, size: str = 'medium'):
        """
        Obtener thumbnail de imagen

        Args:
            image_path: Ruta a imagen original
            size: Tamaño ('small', 'medium', 'large')

        Returns:
            QPixmap con thumbnail o None
        """
        try:
            # Mapear string a tupla de tamaño
            size_map = {
                'small': self.thumbnail_cache.SIZE_SMALL,
                'medium': self.thumbnail_cache.SIZE_MEDIUM,
                'large': self.thumbnail_cache.SIZE_LARGE
            }

            size_tuple = size_map.get(size, self.thumbnail_cache.SIZE_MEDIUM)

            # Obtener desde caché
            return self.thumbnail_cache.get_thumbnail(image_path, size_tuple)

        except Exception as e:
            logger.error(f"Error getting thumbnail for {image_path}: {e}")
            return None

    def preload_thumbnails(self, images: Optional[List[Dict]] = None, size: str = 'medium'):
        """
        Pre-cargar thumbnails en background

        Args:
            images: Lista de imágenes (usa current_images si None)
            size: Tamaño de thumbnails
        """
        try:
            if images is None:
                images = self.current_images

            # Extraer paths
            image_paths = [img['content'] for img in images if img.get('content')]

            if not image_paths:
                return

            # Mapear tamaño
            size_map = {
                'small': self.thumbnail_cache.SIZE_SMALL,
                'medium': self.thumbnail_cache.SIZE_MEDIUM,
                'large': self.thumbnail_cache.SIZE_LARGE
            }
            size_tuple = size_map.get(size, self.thumbnail_cache.SIZE_MEDIUM)

            # Pre-cargar
            logger.info(f"Preloading {len(image_paths)} thumbnails ({size})...")
            self.thumbnail_cache.preload_thumbnails(image_paths, size_tuple)
            logger.info("Thumbnails preloaded")

        except Exception as e:
            logger.error(f"Error preloading thumbnails: {e}")

    def get_categories_with_images(self) -> List[Dict]:
        """
        Obtener categorías que contienen imágenes

        Returns:
            Lista de categorías con conteo
        """
        try:
            return self.db.get_image_categories()
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []

    def get_available_tags(self) -> List[str]:
        """
        Obtener todos los tags disponibles

        Returns:
            Lista de tags únicos
        """
        try:
            return self.db.get_image_tags()
        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            return []

    def get_cache_stats(self) -> Dict:
        """
        Obtener estadísticas del caché

        Returns:
            Dict con estadísticas
        """
        return self.thumbnail_cache.get_stats()

    def clear_cache(self):
        """Limpiar caché de thumbnails"""
        try:
            deleted = self.thumbnail_cache.clear_all()
            logger.info(f"Cache cleared: {deleted} files deleted")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def get_pagination_info(self) -> Dict:
        """
        Obtener información de paginación

        Returns:
            Dict con info de paginación
        """
        return {
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'total_items': self.total_items,
            'items_per_page': self.items_per_page,
            'has_previous': self.current_page > 1,
            'has_next': self.current_page < self.total_pages
        }

    def set_items_per_page(self, count: int):
        """
        Cambiar items por página

        Args:
            count: Nuevo número de items por página
        """
        if count > 0:
            self.items_per_page = count
            # Recargar página actual
            self.load_images(page=1)
            logger.info(f"Items per page set to: {count}")
