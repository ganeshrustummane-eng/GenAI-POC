"""
Abstract base class for all database implementations
"""
from abc import ABC, abstractmethod
from typing import Any


class Database(ABC):
    """Abstract base class for database connections"""
    
    @abstractmethod
    def connect(self) -> Any:
        """Establish connection to database"""
        raise NotImplementedError

    @abstractmethod
    def execute_query(self, query: str) -> Any:
        """Execute SQL query and return DataFrame"""
        raise NotImplementedError
