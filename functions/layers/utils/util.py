from datetime import datetime, date
from sqlalchemy.orm import class_mapper
from sqlalchemy.inspection import inspect


def sqlalchemy_obj_to_dict(obj):
    """ Convert sqlalchemy objet to dict """
    mapper = class_mapper(obj.__class__)
    columns = [column.key for column in mapper.columns]
    result = {}

    for column in columns:
        result[column] = getattr(obj, column)

    return result

def format_value(value):
    """Formats the value to make it JSON serializable."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, bytes):
        return value.decode('utf-8')
    else:
        return value

def object_as_dict(obj):
    """Converts an SQLAlchemy object to a dictionary."""
    # Convert a single instance
    if not isinstance(obj, list):
        return {c.key: format_value(getattr(obj, c.key))
                for c in inspect(obj).mapper.column_attrs}

    # Convert a list of instances
    return [{c.key: format_value(getattr(item, c.key))
             for c in inspect(item).mapper.column_attrs} for item in obj]
