from pprint import pprint

from loguru import logger

from db.database import Database
from db.tables import Users, Documents, DocumentTypesTable


def test_doc_list():
    database = Database()
    with database.get_session() as session:
        username = "docudive@yopmail.com"
        logger.info(f"username: {username}")
        if username:
            user = session.query(Users).filter(Users.username == username).first()
            if user:
                # order by updated_at desc
                docs = (
                    session.query(
                        Documents.id,
                        Documents.file_extension,
                        Documents.file_name,
                        DocumentTypesTable.mime_type,
                        Documents.page_count,
                        Documents.uploaded_at,
                    )
                    .join(DocumentTypesTable, DocumentTypesTable.id == Documents.document_type_id)
                    .filter(Documents.user_id == user.id)
                    .filter(Documents.is_deleted == False)
                    .order_by(Documents.uploaded_at.desc())
                    .all()
                )
                docs_dict_list = []
                for doc_id, file_ext, file_name, mime_type, page_count, uploaded_at in docs:
                    print(doc_id, file_ext, file_name, mime_type, page_count, uploaded_at)
                    docs_dict_list.append(
                        {
                            "document_id": f"{doc_id}",
                            "document_type": f"{file_ext}",
                            "file_name": f"{file_name}",
                            "mime_type": f"{mime_type}",
                            "page_count": page_count,
                            "uploaded_at": f"{uploaded_at.isoformat()}",
                        }
                    )

                # docs_dict_list = object_as_dict(docs)
                # keys_to_delete = ["user_id", "updated_at", "document_type_id", "is_deleted"]
                # # remove keys from dict list
                # for doc in docs_dict_list:
                #     for key in keys_to_delete:
                #         doc.pop(key, None)

        pprint(docs_dict_list)
