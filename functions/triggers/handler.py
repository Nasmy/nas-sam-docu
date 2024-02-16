import uuid
from datetime import datetime, timedelta
from pprint import pprint

from loguru import logger

# Lambda layer
from db.database import Database
from db.tables import Users, DailyUsage
from usage_trigger import update_daily_usage
from utils.custom_exceptions import UserNotFoundError, RaiseCustomException, MissingQueryParameterError
from utils.event_types import LambdaTriggerEventTypes
from utils.util import json_return, get_request_user, get_event_type


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            event_type = get_event_type(event)

            if event_type == LambdaTriggerEventTypes.API_GATEWAY:
                username = get_request_user(event)
            elif event_type == LambdaTriggerEventTypes.EVENT_BRIDGE:
                username = event["detail"]["username"]
                logger.info(f"username: {username}")
            else:
                raise RaiseCustomException(status_code=500, message="Unknown event type")

            if not username:
                raise UserNotFoundError(username)

            db_user = session.query(Users).filter(Users.username == username).first()
            if not db_user:
                raise UserNotFoundError(username)
            user_id = db_user.id

            session.query(DailyUsage).filter(DailyUsage.user_id == user_id, DailyUsage.eod == False).delete()
            session.commit()

            last_updated_date = session.query(DailyUsage.date).filter(DailyUsage.user_id == user_id).order_by(
                DailyUsage.date.desc()).first()
            if last_updated_date:
                last_updated_date = last_updated_date.date + timedelta(days=1)
            logger.info(f"Last update date: {last_updated_date}")

            updated_rows = update_daily_usage(session, user_id, from_date=last_updated_date)
            pprint(updated_rows)

            status_code, msg = 200, {
                "status": "success",
                "message": "Updated usage information",
                "details": {
                    "updated_rows_count": updated_rows,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }

        except (UserNotFoundError, RaiseCustomException, MissingQueryParameterError) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            logger.exception(exception)
            error_id = uuid.uuid4()
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            return json_return(500, exception)
        else:
            session.commit()
            return json_return(status_code, msg)
