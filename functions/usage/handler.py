import uuid
from datetime import datetime, timedelta

from loguru import logger

# Lambda layer
from db.database import Database
from db.tables import Users
from usage_calculations import get_daily_usage_dict
from utils.custom_exceptions import UserNotFoundError, RaiseCustomException, MissingQueryParameterError
from utils.util import json_return, get_query_parameter, iso_to_datetime


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            username = event["requestContext"]["authorizer"]["lambda"].get("user", None)

            logger.info(f"username: {username}")
            if not username:
                raise UserNotFoundError(username)

            db_user = session.query(Users).filter(Users.username == username).first()
            if not db_user:
                raise UserNotFoundError(username)
            user_id = db_user.id

            from_date = get_query_parameter(event, "from_date", required=False)
            to_date = get_query_parameter(event, "to_date", required=False)
            fill_all = get_query_parameter(event, "fill_all", required=False)

            try:
                from_date_dt = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
                to_date_dt = datetime.strptime(to_date, "%Y-%m-%d") if to_date else None
                # add 1 day to to_date_dt
                to_date_dt = to_date_dt + timedelta(days=1) - timedelta(seconds=1) if to_date_dt else None
            except ValueError as e:
                from_date_dt, to_date_dt = None, None

            from_date_dt = datetime.strptime("2023-01-01", "%Y-%m-%d") if not from_date_dt else from_date_dt
            to_date_dt = datetime.utcnow() if not to_date_dt else to_date_dt

            logger.info(f"from_date: {from_date_dt.isoformat()} to_date: {to_date_dt.isoformat()}")
            usage_dict = get_daily_usage_dict(session, user_id, from_date_dt, to_date_dt)
            logger.info(f"usage_dict: {usage_dict}")
            total_usage = usage_dict.pop("total", 0)
            usage_limit = (total_usage // 10)*10 + 10

            if fill_all:
                '''Fill all dates between from_date and to_date'''
                usage_dict_new = {}
                current_date = from_date_dt
                while current_date <= to_date_dt:
                    current_date_str = current_date.strftime("%Y-%m-%d")
                    if current_date_str not in usage_dict:
                        usage_dict_new[current_date.strftime("%Y-%m-%d")] = 0
                    else:
                        usage_dict_new[current_date_str] = usage_dict[current_date_str]
                    current_date = current_date + timedelta(days=1)
                usage_dict = usage_dict_new

            status_code, msg = 200, {
                "status": "success",
                "message": "Fetched usage information",
                "details": {
                    "from_date": from_date_dt.isoformat(),
                    "to_date": to_date_dt.isoformat(),
                    "total_usage": total_usage,
                    "usage_limit": usage_limit,
                    "usage_dict": usage_dict,
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
