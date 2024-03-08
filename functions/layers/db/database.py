import contextlib
import logging
import os
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from db.base import Base


class Database:
    """Database connection class"""

    def __init__(self, echo=False):
        self.engine = create_engine(self.get_database_connection_string(), echo=echo)

    def close_connection(self):
        """Close existing connection"""
        self.engine.dispose()

    @contextlib.contextmanager
    def get_session(self, echo=False):
        """Create a session from db connection"""
        Session = sessionmaker(bind=self.engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()

    def get_database_connection_string(self):
        """Retrieve connection string"""
        endpoint = os.environ.get("database_endpoint")
        port = os.environ.get("database_port")
        username = os.environ.get("database_username")
        password = os.environ.get("database_password")
        database = os.environ.get("database_name")

        db_url = f"postgresql+pg8000://{username}:{password}@{endpoint}:{port}/{database}"
        return db_url

    def create_all_tables(self, drop_existing: bool = False):

        """Creates database and schema"""
        try:
            if not database_exists(self.engine.url):
                create_database(self.engine.url)
            if drop_existing:
                Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)

        except Exception as exception:
            _error_id = uuid.uuid4()
            detail = f"error_id: {_error_id} error: {exception}"
            logging.error(detail)
            raise AssertionError(detail)


if __name__ == "__main__":

    database = Database()
    database.create_all_tables(drop_existing=False)
