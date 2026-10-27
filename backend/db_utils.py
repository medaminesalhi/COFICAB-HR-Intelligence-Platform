"""Utilitaires PostgreSQL avec fermeture et rollback garantis."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg2
from config import DATABASE_CONFIG


@contextmanager
def database_connection() -> Iterator[psycopg2.extensions.connection]:
    # Commit en cas de succès, rollback en cas d'erreur, fermeture garantie.
    connection = psycopg2.connect(**DATABASE_CONFIG)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
