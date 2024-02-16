import csv

import pandas as pd

from db.database import Database
from db.tables import Models, DocumentTypesTable, UserAttributes, APIKeys, AnnotationTypesTable, Subscriptions, \
    UsageTypesTable
from utils.annotation_types import AnnotationTypes
from utils.usage_type import UsageTypes, get_credit_cost


def add_models():
    print("Adding models")
    from chat.model_info import OpenAIModels

    database = Database(echo=False)
    with database.get_session() as session:
        for model_name, model_dict in OpenAIModels.model_info.items():
            db_model = session.query(Models).filter(Models.name == model_name).first()
            if db_model:
                continue
            model = Models(
                name=model_name,
                prompt_1k_cost=model_dict["prompt_token_1k"],
                completion_1k_cost=model_dict["completion_token_1k"],
            )
            session.add(model)
            print(f"Added model {model_name}")
        session.commit()


def add_document_types():
    print("Adding document types")

    from utils.document_types import DocumentTypes as DocumentTypesData
    from utils.document_types import doc_type_to_mime_type, get_doc_type_to_supported_extensions

    database = Database(echo=False)
    with database.get_session() as session:
        for doc_type in DocumentTypesData:
            db_doc_type = session.query(DocumentTypesTable).filter(DocumentTypesTable.name == doc_type.value).first()
            if db_doc_type:
                continue
            new_db_doc_type = DocumentTypesTable(
                name=doc_type.value,
                document_type=doc_type.name,
                mime_type=doc_type_to_mime_type(doc_type),
                extensions=get_doc_type_to_supported_extensions(doc_type),
            )
            session.add(new_db_doc_type)
            print(f"Added document type {doc_type.value}")
        session.commit()


def add_user_attributes():
    print("Adding user attributes")

    database = Database(echo=False)
    with database.get_session() as session:
        with open("user_attributes.csv", "r") as f:
            reader = csv.reader(f)
            for row in reader:
                db_user_attribute = (
                    session.query(UserAttributes).filter(UserAttributes.attribute_name == row[0]).first()
                )
                if db_user_attribute:
                    continue
                user_attribute = UserAttributes(attribute_name=row[0])
                session.add(user_attribute)
                print(f"Added user attribute {row[0]}")
        session.commit()


def add_api_key():
    print("Adding api keys")

    database = Database(echo=False)
    with database.get_session() as session:
        for service_key, api_key in [("openai_key1", "sk-1234567890")]:
            db_api_key = session.query(APIKeys).filter(APIKeys.service_key == service_key).first()
            if db_api_key:
                continue
            api_key = APIKeys(
                service_key=service_key,
                api_key=api_key,
            )
            session.add(api_key)
            print(f"added api key - {service_key} - {api_key}")
        session.commit()


def add_annotation_types():
    print("Adding annotation types")

    database = Database(echo=False)
    with database.get_session() as session:
        for annotation_type in list(AnnotationTypes):
            db_anno_type = (
                session.query(AnnotationTypesTable).filter(AnnotationTypesTable.name == annotation_type.value).first()
            )
            if not db_anno_type:
                new_db_anno_type = AnnotationTypesTable(
                    name=annotation_type.value,
                    display_name=annotation_type.value.upper(),
                    is_enabled=annotation_type != AnnotationTypes.CHAT,
                )
                session.add(new_db_anno_type)
                print(f"Added annotation type {annotation_type.value}")
        session.commit()


def add_subscriptions():
    print("Adding subscriptions types")
    database = Database(echo=False)
    with database.get_session() as session:
        # read from csv, line by line
        df = pd.read_csv("subscriptions.csv", header=None)
        for index, row in df.iterrows():
            db_sub_type = (
                session.query(Subscriptions).filter(Subscriptions.name == row[0]).first()
            )
            if not db_sub_type:
                new_db_anno_type = Subscriptions(
                    name=row[0].strip(),
                    display_name=row[1].strip(),
                    description=row[2].strip(),
                    amount=row[3],
                    interval=row[4].strip(),
                    credits=row[5],
                    details=row[6].strip(),
                )
                session.add(new_db_anno_type)
                print(f"Added subscriptions type {row}")
        session.commit()


def add_usage_types():
    print("Adding usage types")
    database = Database(echo=False)
    with database.get_session() as session:
        for usage_type in list(UsageTypes):
            usage_type: UsageTypes
            db_sub_type = (
                session.query(UsageTypesTable).filter(UsageTypesTable.name == usage_type.value).first()
            )
            if not db_sub_type:
                new_db_usage_type = UsageTypesTable(
                    name=usage_type.value,
                    display_name=usage_type.value.capitalize(),
                    credits_per_unit=get_credit_cost(usage_type),
                )
                session.add(new_db_usage_type)
                print(f"Added usage type {usage_type.value}")
        session.commit()


def main():
    add_models()
    add_api_key()
    add_document_types()
    add_user_attributes()
    add_annotation_types()
    add_subscriptions()
    add_usage_types()


if __name__ == "__main__":
    main()
