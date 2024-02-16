from pprint import pprint

from db.database import Database
from tests.decorators import calculate_time
from usage.handler import get_usage_dict


@calculate_time("all_usage")
def all_usage():
    database = Database(echo=False)
    with database.get_session() as session:
        username = "docudive@yopmail.com"
        usage_dict = get_usage_dict(session, username)
        pprint(usage_dict)


if __name__ == '__main__':
    all_usage()