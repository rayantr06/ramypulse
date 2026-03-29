"""Gestionnaire de base de données SQLite pour RamyPulse.

Fournit un DatabaseManager minimal gérant la connexion SQLite et
l'initialisation du schéma pour les modules métier.
"""
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/ramypulse.db"


class DatabaseManager:
    """Gestionnaire de connexion SQLite avec initialisation automatique du schéma.

    Utilisé par les modules métier (BusinessCatalog, etc.) pour persister
    les données localement sans dépendance cloud.

    Exemple :
        db = DatabaseManager()
        db.get_connection()  # connexion SQLite prête à l'emploi
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        """Initialise le gestionnaire avec le chemin vers la base SQLite.

        Args:
            db_path: Chemin vers le fichier SQLite. Utiliser ':memory:' pour
                     les tests. Crée les répertoires intermédiaires si nécessaire.
        """
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Retourne une connexion SQLite, en la créant si nécessaire.

        Active le mode WAL pour de meilleures performances en lecture concurrente
        et retourne les lignes sous forme de dict-like (Row).

        Returns:
            Connexion SQLite active.
        """
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            if self._db_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL")
            logger.debug("Connexion SQLite ouverte : %s", self._db_path)
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Exécute une requête SQL et retourne le curseur.

        Args:
            sql: Requête SQL à exécuter.
            params: Paramètres de la requête (protection injection SQL).

        Returns:
            Curseur SQLite après exécution.
        """
        return self.get_connection().execute(sql, params)

    def executemany(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """Exécute une requête SQL pour chaque jeu de paramètres.

        Args:
            sql: Requête SQL à exécuter.
            params_list: Liste de tuples de paramètres.

        Returns:
            Curseur SQLite après exécution.
        """
        return self.get_connection().executemany(sql, params_list)

    def commit(self) -> None:
        """Valide la transaction en cours."""
        if self._conn is not None:
            self._conn.commit()

    def close(self) -> None:
        """Ferme la connexion SQLite proprement."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.debug("Connexion SQLite fermée : %s", self._db_path)
