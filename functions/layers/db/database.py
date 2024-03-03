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
        self.echo = echo

    def get_engine(self):
        return create_engine(self.get_database_connection_string(), echo=self.echo)

    def close_connection(self):
        """Close existing connection"""
        print("Closing connection")

    @contextlib.contextmanager
    def get_session(self, echo=False):
        """Create a session from db connection"""
        engine = self.get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()

    def get_database_connection_string(self):
        """Retrieve connection string"""
        endpoint = os.environ.get("database_endpoint")
        port = os.environ.get("database_port")
        username = os.environ.get("database_username")
        password = os.environ.get("database_password")
        database = os.environ.get("database_name")

        #endpoint = "docudive-backend-postgresdbinstance.cb0aukieofkq.us-east-1.rds.amazonaws.com"
        #port = 5432
        #username = "postgres"
        #password = "W4DWRdv8dKMmCYimKs9Z"
        #database = "postgres"

        db_url = f"postgresql+pg8000://{username}:{password}@{endpoint}:{port}/{database}"
        return db_url

    def create_all_tables(self, drop_existing: bool = False):
        engine = self.get_engine()
        """Creates database and schema"""
        try:
            if not database_exists(engine.url):
                create_database(engine.url)
            if drop_existing:
                Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)

        except Exception as exception:
            _error_id = uuid.uuid4()
            detail = f"error_id: {_error_id} error: {exception}"
            logging.error(detail)
            raise AssertionError(detail)
        finally:
            engine.dispose()


if __name__ == "__main__":
    database = Database()
    database.create_all_tables(drop_existing=False)
