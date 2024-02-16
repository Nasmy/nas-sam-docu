import json
from datetime import datetime, timedelta

from db.database import Database
from db.tables import Users, UserAttributes, UserDetails, Annotations, AnnotationTypesTable, Subscriptions
from utils.annotation_types import AnnotationStatus


def query_test():
    database = Database(echo=False)
    with database.get_session() as session:
        all_subs = session.query(Subscriptions).filter(Subscriptions.is_active == True).all()
        list_of_subs = []
        for sub in all_subs:
            list_of_subs.append(
                {
                    "id": sub.id,
                    "name": sub.name,
                    "display_name": sub.display_name,
                    "description": sub.description,
                    "amount": sub.amount,
                    "interval": sub.interval,
                    "credits": sub.credits,
                    "details": sub.details.split(":"),
                }
            )
        print(json.dumps(list_of_subs, indent=4))


if __name__ == "__main__":
    query_test()
