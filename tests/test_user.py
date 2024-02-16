import json
from datetime import datetime
from pprint import pprint

from loguru import logger

from db.database import Database
from db.tables import UserAttributes, Users, UserDetails
from user.user_details import set_user_details
from utils.util import json_return


def test_retrieve_users():
    database = Database(echo=False)
    with database.get_session() as session:
        username = "docudive@yopmail.com"

        db_user = session.query(Users).filter(Users.username == username).first()
        if not db_user:
            msg = {"status": "failed", "message": "user does not exist"}
            return json_return(404, msg)

        user_id = db_user.id
        user_created_at = db_user.created_at

        result = (
            session.query(
                UserAttributes.attribute_name,
                UserDetails.value,
            )
            .join(UserAttributes, UserAttributes.id == UserDetails.user_attribute_id)
            .join(Users, Users.id == UserDetails.user_id)
            .filter(Users.username == username)
            .all()
        )

        user_details_dict = dict()
        user_data = dict()
        for db_attribute_name, db_value in result:
            user_data[db_attribute_name] = db_value

        print("User details dict: " + str(user_details_dict))
        user_details_dict["user_id"] = user_id
        user_details_dict["username"] = username
        user_details_dict["no_of_attributes"] = len(user_data.keys())
        user_details_dict["created_at"] = user_created_at.isoformat()
        user_details_dict["timestamp"] = datetime.utcnow().isoformat()
        user_details_dict["user_data"] = user_data

        pprint(json.dumps(user_details_dict, indent=4))
        return user_details_dict


def test_set_user_details():
    database = Database(echo=False)
    with database.get_session() as session:
        username = "docudive@yopmail.com"

        db_user = session.query(Users).filter(Users.username == username).first()
        if not db_user:
            msg = {"status": "failed", "message": "user does not exist"}
            return json_return(404, msg)

        body = {
            "first_name": "Docu",
            "middle_name": "Docu",
            "last_name": "Dive",
            "phone_number_2": "+919876543210",
            "address": "123, Main Street, City, State, Country",
            "company": "DocuDive",
        }
        logger.info(f"body: {body}")

        created_attributes, updated_attributes = set_user_details(session, username, body)

        pprint(created_attributes)
        pprint(updated_attributes)


if __name__ == "__main__":
    ret = test_retrieve_users()
    pprint(ret)
