from pprint import pprint

from db.database import Database
from db.tables import Users, Documents
from utils.util import json_return


def test_retrieve_users():
    database = Database(echo=False)
    with database.get_session() as session:
        document_id = "17ed40ce-99da-40b1-bde2-677f78da3d28"
        result = (
            session.query(Users.username, Users.id, Documents.id)
            .join(Documents, Documents.user_id == Users.id)
            .filter(Documents.id == document_id)
            .first()
        )
        if not result:
            msg = {"status": "failed", "message": "document doesn't exist"}
            return json_return(404, msg)

        db_username, db_user_id, db_document_id = result
        pprint("User id: " + str(db_user_id))
        pprint("Document id: " + str(db_document_id))
        pprint("Username: " + str(db_username))
        return db_username
