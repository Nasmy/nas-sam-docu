from datetime import timedelta
from pprint import pprint

from db.database import Database
from db.tables import DailyUsage
from triggers.usage_trigger import update_daily_usage
from usage.usage_calculations import get_usage_dict, get_daily_usage_dict, get_total_usage


def test_all_usage():
    database = Database(echo=False)
    with database.get_session() as session:
        username = "docudive@yopmail.com"
        usage_dict = get_usage_dict(session, username)
        pprint(usage_dict)

def test_daily_usage():
    database = Database(echo=False)
    with database.get_session() as session:
        user_id = "6f67ad51-3576-4a0c-9119-f725719ae0db"
        usage_dict = get_daily_usage_dict(session, user_id)
        pprint(usage_dict)

def test_total_usage():
    database = Database(echo=False)
    with database.get_session() as session:
        user_id = "6f67ad51-3576-4a0c-9119-f725719ae0db"
        total_usage = get_total_usage(session, user_id)
        pprint(f"Total usage: {total_usage}")


def test_update_usage():
    database = Database(echo=False)
    with database.get_session() as session:
        user_id = "6f67ad51-3576-4a0c-9119-f725719ae0db"
        session.query(DailyUsage).filter(DailyUsage.user_id == user_id, DailyUsage.eod == False).delete()
        session.commit()

        last_updated_date = session.query(DailyUsage.date).filter(DailyUsage.user_id == user_id).order_by(
            DailyUsage.date.desc()).first()
        if last_updated_date:
            last_updated_date = last_updated_date.date + timedelta(days=1)
        print(last_updated_date)

        usage_dict = update_daily_usage(session, user_id, from_date=last_updated_date)
        pprint(usage_dict)
