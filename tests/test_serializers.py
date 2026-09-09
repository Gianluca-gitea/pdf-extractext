from datetime import datetime, timezone

from bson.objectid import ObjectId

from app.services.serializers import serialize_document, serialize_value


def test_serialize_value_converts_datetime_to_isoformat() -> None:
    value = datetime(2024, 1, 1, tzinfo=timezone.utc)

    assert serialize_value(value) == "2024-01-01T00:00:00+00:00"


def test_serialize_value_converts_object_id_to_str() -> None:
    object_id = ObjectId("507f1f77bcf86cd799439011")

    assert serialize_value(object_id) == "507f1f77bcf86cd799439011"


def test_serialize_value_leaves_other_values_intact() -> None:
    assert serialize_value(None) is None
    assert serialize_value("2024-01-01") == "2024-01-01"
    assert serialize_value(42) == 42


def test_serialize_document_converts_known_fields() -> None:
    document_id = ObjectId("507f1f77bcf86cd799439011")
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    document = {"_id": document_id, "created_at": created_at, "pdf_nombre": "doc.pdf"}

    result = serialize_document(document)

    assert result == {
        "_id": "507f1f77bcf86cd799439011",
        "created_at": "2024-01-01T00:00:00+00:00",
        "pdf_nombre": "doc.pdf",
    }


def test_serialize_document_does_not_mutate_input() -> None:
    document = {"_id": ObjectId("507f1f77bcf86cd799439011")}

    serialize_document(document)

    assert isinstance(document["_id"], ObjectId)


def test_serialize_document_handles_missing_fields() -> None:
    assert serialize_document({"pdf_nombre": "doc.pdf"}) == {"pdf_nombre": "doc.pdf"}
