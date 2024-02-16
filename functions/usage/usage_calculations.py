import os
from datetime import datetime
from typing import Dict

from loguru import logger
from sqlalchemy import func, text

from db.tables import Queries, Chats, Documents, Users, DocumentTypesTable
from utils.decorators import calculate_time

current_schema = f"{os.getenv('database_schema', 'test')}"


def get_usage_dict(session, username) -> Dict:
    usage_dict = {
        "chat": {
            "total_cost_usd": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
        },
        "annotations": {
            "total_cost_usd": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
        },
        "document": {
            "total_documents": 0,
            "total_pages": 0,
            "document_type_counts": {},
        },
    }

    chats = (
        session.query(
            func.sum(Queries.total_amount),
            func.sum(Queries.prompt_tokens),
            func.sum(Queries.completion_tokens),
            Chats.chat_type,
        )
        .join(Chats, Queries.chat_id == Chats.id)
        .join(Documents, Chats.document_id == Documents.id)
        .join(Users, Documents.user_id == Users.id)
        .group_by(Chats.chat_type)
        .filter(Users.username == username)
        .all()
    )

    logger.info("Results length: " + str(len(chats)))

    for total_amount, prompt_tokens, completion_tokens, chat_type in chats:
        key = "chat" if chat_type == "user" else "annotations"
        usage_dict[key]["total_cost_usd"] = total_amount
        usage_dict[key]["total_prompt_tokens"] = prompt_tokens
        usage_dict[key]["total_completion_tokens"] = completion_tokens

    doc_type_counts = {}
    docs = (
        session.query(
            func.sum(Documents.page_count),
            DocumentTypesTable.document_type,
            func.count(DocumentTypesTable.document_type),
        )
        .join(DocumentTypesTable, Documents.document_type_id == DocumentTypesTable.id)
        .join(Users, Documents.user_id == Users.id)
        .group_by(DocumentTypesTable.document_type)
        .filter(Users.username == username)
        .all()
    )

    usage_dict["document"]["total_documents"] = len(docs)
    for doc_page_count, document_type, document_type_count in docs:
        usage_dict["document"]["total_pages"] += doc_page_count
        doc_type_counts[document_type] = document_type_count

    usage_dict["document"]["document_type_counts"] = doc_type_counts
    usage_dict["timestamp"] = datetime.utcnow().isoformat()

    usage_dict["chat"]["total_cost_usd"] = round(usage_dict["chat"]["total_cost_usd"] / 1000, 2)
    usage_dict["annotations"]["total_cost_usd"] = round(usage_dict["annotations"]["total_cost_usd"] / 1000, 2)

    return usage_dict


@calculate_time("get_daily_usage_dict")
def get_daily_usage_dict(session, user_id, from_date=None, to_date=None) -> Dict:
    from_date = from_date.isoformat() if from_date is not None else "2023-01-01"
    to_date = to_date.isoformat() if to_date is not None else datetime.utcnow().isoformat()
    chat_sql = text(f"""
    SELECT 
        DATE(du.date) AS date,
        SUM(du.credits) AS sum_total_credits
    FROM 
        {current_schema}.daily_usage du 
    WHERE 
        du.user_id = '{user_id}'
    AND
        du.date >= '{from_date}' 
    AND
        du.date <= '{to_date}'
    GROUP BY 
        date
    ORDER BY 
        date;
    """)
    results = session.execute(chat_sql)
    usage_dict = {}
    total_usage = 0
    if results:
        for row in results:
            rounded_credits = round(row.sum_total_credits, 2)
            usage_dict[row.date.isoformat()] = rounded_credits
            total_usage += rounded_credits
    usage_dict["total"] = total_usage
    return usage_dict


@calculate_time("get_total_usage")
def get_total_usage(session, user_id, from_date=None, to_date=None) -> float:
    from_date = from_date.isoformat() if from_date is not None else "2023-01-01"
    to_date = to_date.isoformat() if to_date is not None else datetime.utcnow().isoformat()

    chat_sql = text(f"""
    SELECT 
        SUM(du.credits) AS sum_total_credits
    FROM 
        {current_schema}.daily_usage du 
    WHERE 
        du.user_id = '{user_id}'
    AND
        du.date >= '{from_date}' 
    AND
        du.date <= '{to_date}';
    """)
    results = session.execute(chat_sql)
    return results.scalar() if results else 0
