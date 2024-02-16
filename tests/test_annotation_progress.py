from datetime import datetime
from pprint import pprint

from db.database import Database
from db.tables import Annotations, AnnotationTypesTable
from utils.annotation_types import AnnotationTypes
from utils.custom_exceptions import DocumentNotFoundError


def test_get_chat_list():
    document_id = "9b14f066-55f9-4bb7-9cdd-58c0bd94a10d"
    database = Database()
    with database.get_session() as session:
        all_annotations = (
            session.query(Annotations.status, AnnotationTypesTable.name)
            .join(AnnotationTypesTable, AnnotationTypesTable.id == Annotations.annotation_type_id)
            .filter(Annotations.document_id == document_id)
            .filter(AnnotationTypesTable.is_enabled == True)
            .all()
        )
        if not all_annotations:
            raise DocumentNotFoundError(document_id)

        annotation_status_list = []
        for status, annotation_type in all_annotations:
            annotation_status_list.append({"status": status, "annotation_type": annotation_type})

        output_dict = {
            "status": "success",
            "message": "all annotations retrieved",
            "details": {
                "annotations_list": annotation_status_list,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        pprint(output_dict)


def test_annotation_type_update():
    document_id = "9b14f066-55f9-4bb7-9cdd-58c0bd94a10d"
    annotation_type = AnnotationTypes.HEADINGS
    database = Database()
    with database.get_session() as session:
        db_annotations = (
            session.query(Annotations)
            .join(AnnotationTypesTable, AnnotationTypesTable.id == Annotations.annotation_type_id)
            .filter(Annotations.document_id == document_id)
            .filter(AnnotationTypesTable.name == annotation_type.value)
            .first()
        )
        print(db_annotations.created_at)
