from loguru import logger

from db.database import Database
from db.tables import Users, Documents, Chats
from utils.util import json_return


def test_get_chat_list():
    database = Database()
    with database.get_session() as session:
        username = "docudive@yopmail.com"
        document_id = "ec35c96b-cb07-4ae6-b787-75805c48315b"
        logger.info(f"username: {username}")
        logger.info(f"document_id: {document_id}")
        logger.info(f"doc id type: {type(document_id)}")

        result = (
            session.query(Users.username, Users.id, Documents.id)
            .join(Documents, Documents.user_id == Users.id)
            .filter(Documents.id == str(document_id))
            .first()
        )
        logger.info(f"result: {result}")

        if not result:
            msg = {"status": "failed", "message": "document doesn't exist"}
            return json_return(404, msg)

        db_username, db_user_id, db_document_id = result

        if username != db_username:
            msg = {"status": "failed", "message": f"user {username} not authorized to access this document"}
            return json_return(401, msg)

        db_chats = (
            session.query(Chats.id, Chats.chat_name, Chats.created_at)
            .filter(Chats.document_id == document_id)
            .order_by(Chats.created_at.desc())
            .all()
        )
        docs_dict_list = []
        if not db_chats:
            logger.info("No chats found")
        else:
            for chat_id, chat_name, created_at in db_chats:
                docs_dict_list.append(
                    {
                        "chat_id": chat_id,
                        "chat_name": chat_name,
                        "created_at": created_at.isoformat(),
                    }
                )

            logger.info(docs_dict_list)
