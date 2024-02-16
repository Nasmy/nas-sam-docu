from db.database import Database
from db.tables import Users, DocumentTypesTable, Documents, Chats, Models


# def add_usage_types():
#     database = Database(echo=True)
#     with database.get_session() as session:


def test_users():
    database = Database(echo=True)
    with database.get_session() as session:
        user = session.query(Users).filter(Users.username == "test@gmail.com").first()

        if not user:
            user = Users(username="test@gmail.com", password="test")
            session.add(user)
            session.commit()
        assert user.id is not None
        assert user.username == "test@gmail.com"

        document_type = DocumentTypesTable(
            name="Portable Document Format",
            document_type="pdf",
            mime_type="application/pdf",
        )
        session.add(document_type)
        session.commit()

        document = Documents(
            user_id=user.id,
            document_type_id=document_type.id,
            file_alias="my test file",
            file_name="test.pdf",
            file_size_kb=100,
            page_count=5,
        )
        session.add(document)
        session.commit()

        chat = Chats(
            document_id=document.id,
            chat_name="test chat",
        )
        session.add(chat)
        session.commit()


def test_retrieve_users():
    database = Database(echo=False)
    with database.get_session() as session:
        given_chat_id = "1d1f79fb-3bbe-4de0-84eb-e8016a712c41"
        result = (
            session.query(Users.username, Documents.file_size_kb)
            .join(Documents, Documents.user_id == Users.id)
            .join(Chats, Chats.document_id == Documents.id)
            .filter(Chats.id == given_chat_id)
            .first()
        )
        if result:
            print("User: ", result.username)
            print("File size: ", result.file_size_kb)
        else:
            print("No user found")


def test_retrieve_to_dict_list():
    database = Database(echo=False)
    with database.get_session() as session:
        results = session.query(Models.name, Models.prompt_1k_cost).all()
        print(results)
        for name, cost in results:
            print(name, cost)
