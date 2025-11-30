"""
Table Model
Modelo para representar tablas que agrupan items en estructura matricial
"""
from typing import Optional
from datetime import datetime


class Table:
    """Modelo para representar una tabla de items"""

    def __init__(
        self,
        table_id: Optional[int] = None,
        name: str = "",
        description: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = table_id
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self) -> dict:
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def from_dict(data: dict) -> 'Table':
        """Crea un modelo desde diccionario"""
        return Table(
            table_id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )

    def validate(self) -> bool:
        """Valida que el modelo tenga datos válidos"""
        if not self.name or len(self.name.strip()) == 0:
            return False
        return True

    def __repr__(self) -> str:
        return f"Table(id={self.id}, name='{self.name}')"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Table):
            return False
        return self.id == other.id
