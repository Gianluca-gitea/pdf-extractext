"""Run against a real stack: API_URL=http://localhost:8000 python tests/integration/smoke.py."""

import json
import os
from urllib.request import Request, urlopen

BASE = os.getenv("API_URL", "http://localhost:8000")


def request(path, method="GET", body=None, content_type="application/json"):
    headers = {"Content-Type": content_type}
    with urlopen(
        Request(BASE + path, data=body, method=method, headers=headers), timeout=15
    ) as response:
        return response.read()


def pdf_bytes():
    stream = b"BT /F1 12 Tf 40 100 Td (Audit integration) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    content = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(content))
        content += str(index).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(content)
    content += b"xref\n0 6\n0000000000 65535 f \n"
    content += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return (
        content
        + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )


def main():
    assert json.loads(request("/ready")) == {"status": "ok"}
    pdf = pdf_bytes()
    extracted = json.loads(request("/extract", "POST", pdf, "application/pdf"))
    assert extracted["page_count"] == 1 and "Audit integration" in extracted["content"]
    boundary = "audit-boundary"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audit.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
        + pdf
        + f"\r\n--{boundary}--\r\n".encode()
    )
    content_type = "multipart/form-data; boundary=" + boundary
    uploaded = json.loads(request("/documents/upload", "POST", body, content_type))
    assert "Audit integration" in uploaded["extracted_text"]
    duplicate = json.loads(request("/documents/upload", "POST", body, content_type))
    assert duplicate["extracted_text"] == uploaded["extracted_text"]
    documents = json.loads(request("/documents?include_text=true"))["items"]
    matches = [doc for doc in documents if doc["pdf_nombre"] == "audit.pdf"]
    assert len(matches) == 1, "duplicate upload must persist one document"
    document = matches[0]
    path = "/documents/" + document["_id"]
    try:
        by_checksum = json.loads(
            request("/documents/by-checksum/" + document["checksum_archivo"])
        )
        assert by_checksum["document_id"] == document["_id"]
        renamed = json.loads(
            request(
                path, "PATCH", json.dumps({"pdf_nombre": "audit-renamed.pdf"}).encode()
            )
        )
        assert renamed["document"]["pdf_nombre"] == "audit-renamed.pdf"
        assert b"Audit integration" in request(path + "/download")
    finally:
        assert json.loads(request(path, "DELETE"))["status"] == "deleted"
    remaining = json.loads(request("/documents"))["items"]
    assert all(doc["_id"] != document["_id"] for doc in remaining)
    print(
        "PASS: readiness, extraction, persistence, deduplication, checksum, edit, download, soft delete"
    )


if __name__ == "__main__":
    main()
