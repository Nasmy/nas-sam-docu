import os
from datetime import datetime

from loguru import logger
from sqlalchemy import text


from db.tables import UsageTypesTable, DailyUsage
from utils.decorators import calculate_time
from utils.usage_type import UsageTypes

current_schema = f"{os.getenv('database_schema', 'test')}"


@calculate_time("update_daily_usage")
def update_daily_usage(session, user_id, from_date=None, to_date=None) -> int:
    from_date = from_date or "2023-01-01"
    to_date = to_date or datetime.utcnow().isoformat()
    logger.info(f"from_date: {from_date} to_date: {to_date}")

    chat_sql = text(f"""
    SELECT 
        DATE(c.created_at) AS date,
        SUM(q.total_amount) AS sum_total_amount,
        SUM(q.prompt_tokens) AS sum_prompt_tokens,
        SUM(q.completion_tokens) AS sum_completion_tokens,
        c.chat_type
    FROM 
        {current_schema}.queries q 
    JOIN 
        {current_schema}.chats c ON q.chat_id = c.id
    JOIN 
        {current_schema}.documents d ON c.document_id = d.id
    WHERE 
        d.user_id = '{user_id}'
    AND
        c.created_at >= '{from_date}' 
    AND
        c.created_at <= '{to_date}'
    GROUP BY 
        date,
        c.chat_type
    ORDER BY 
        date;
    """)

    document_sql = text(f"""
    SELECT 
        DATE(d.uploaded_at) AS date,
        SUM(d.page_count) AS total_pages
    FROM
        {current_schema}.documents d
    WHERE 
        d.user_id = '{user_id}'
    AND
        d.uploaded_at >= '{from_date}' 
    AND
        d.uploaded_at <= '{to_date}'
    GROUP BY 
        date
    ORDER BY 
        date;
    """)

    current_date = datetime.utcnow().date()
    results = session.execute(document_sql)
    usage_types_dict = {result.name: (result.id, result.credits_per_unit) for result in
                        session.query(UsageTypesTable).all()}

    updated_rows = 0
    for row in results:
        date_difference = (current_date - row.date).days
        units = row.total_pages
        usage_tuple = usage_types_dict[f"{UsageTypes.PAGES.value}"]
        new_daily_usage = DailyUsage(
            user_id=user_id,
            usage_type_id=usage_tuple[0],
            units=units,
            credits=units * usage_tuple[1],
            eod=True if date_difference > 0 else False,
            date=row.date,
            timestamp=datetime.utcnow(),
        )
        session.add(new_daily_usage)
        print(f"Date : {row.date} Total Pages: {row.total_pages}")
        updated_rows += 1

    results = session.execute(chat_sql)
    for row in results:
        date_difference = (current_date - row.date).days
        units = row.sum_total_amount
        usage_type_key = f"{UsageTypes.USER_CHAT.value}" if row.chat_type == "user" else f"{UsageTypes.ANNOTATIONS.value}"
        usage_tuple = usage_types_dict[f"{usage_type_key}"]
        new_daily_usage = DailyUsage(
            user_id=user_id,
            usage_type_id=usage_tuple[0],
            units=units,
            credits=units * usage_tuple[1],
            eod=True if date_difference > 0 else False,
            date=row.date,
            timestamp=datetime.utcnow(),
        )
        session.add(new_daily_usage)
        print(row)
        updated_rows += 1
    session.commit()
    return updated_rows


if __name__ == '__main__':
    from db.database import Database
    database = Database()
    with database.get_session() as session:
        urc = update_daily_usage(session, '6f67ad51-3576-4a0c-9119-f725719ae0db', from_date='2023-10-31', to_date=None)
        print("Updated rows count: ", urc)