import io
import os
import tempfile

import pytest

os.environ["STATSLEUTH_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["STATSLEUTH_RATE"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
client.__enter__()  # run startup (db init)

FLAWED = "Participants (N = 60). t(58) = 1.40, p = .012. 9/20 (46%)."


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_analyze_and_persist_roundtrip():
    r = client.post("/api/analyze", json={"text": FLAWED, "title": "demo"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] and body["summary"]["gross"] == 2
    got = client.get(f"/api/reports/{body['id']}").json()
    assert got["title"] == "demo" and len(got["findings"]) == 2
    assert any(x["id"] == body["id"] for x in client.get("/api/reports").json())
    for fmt, needle in [("json", '"findings"'), ("csv", "id,check,status"), ("md", "StatSleuth report")]:
        e = client.get(f"/api/reports/{body['id']}/export", params={"format": fmt})
        assert e.status_code == 200 and needle in e.text
    assert client.delete(f"/api/reports/{body['id']}").status_code == 200
    assert client.get(f"/api/reports/{body['id']}").status_code == 404
    assert client.delete(f"/api/reports/{body['id']}").status_code == 404


def test_persist_false_stores_nothing():
    before = len(client.get("/api/reports").json())
    r = client.post("/api/analyze", json={"text": FLAWED, "persist": False}).json()
    assert r["id"] is None
    assert len(client.get("/api/reports").json()) == before


@pytest.mark.parametrize("payload", [
    {"text": ""}, {"text": "   "}, {"text": "x" * 300_001},
    {"text": "a", "options": {"alpha": 5}}, {"text": "a", "options": {"items_per_scale": 0}},
    {"notext": 1},
])
def test_validation_errors(payload):
    assert client.post("/api/analyze", json=payload).status_code == 422


def test_file_upload_txt_and_rejections():
    files = {"file": ("m.txt", io.BytesIO(FLAWED.encode()), "text/plain")}
    r = client.post("/api/analyze/file", files=files, data={"persist": "false"})
    assert r.status_code == 200 and r.json()["summary"]["gross"] == 2
    assert client.post("/api/analyze/file", files={"file": ("m.exe", io.BytesIO(b"x"), "application/octet-stream")}).status_code == 415
    big = io.BytesIO(b"a" * (5 * 1024 * 1024 + 10))
    assert client.post("/api/analyze/file", files={"file": ("m.txt", big, "text/plain")}).status_code == 413
    assert client.post("/api/analyze/file", files={"file": ("m.txt", io.BytesIO(b"   "), "text/plain")}).status_code == 422
    assert client.post("/api/analyze/file", files={"file": ("m.pdf", io.BytesIO(b"not a pdf"), "application/pdf")}).status_code == 422


def test_pdf_upload_real_pdf():
    from pypdf import PdfWriter  # build a blank PDF: no text layer -> must be rejected cleanly
    w = PdfWriter()
    w.add_blank_page(200, 200)
    buf = io.BytesIO()
    w.write(buf)
    r = client.post("/api/analyze/file", files={"file": ("blank.pdf", io.BytesIO(buf.getvalue()), "application/pdf")})
    assert r.status_code == 422 and "scanned" in r.json()["detail"].lower()


def test_pdf_with_text_layer():
    """Build a PDF that really has a text layer using only stdlib (hand-written PDF)."""
    content = b"BT /F1 12 Tf 20 100 Td (t(58) = 1.40, p = .012) Tj ET"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out = b"%PDF-1.4\n"
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offs:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)
    r = client.post("/api/analyze/file", files={"file": ("t.pdf", io.BytesIO(out), "application/pdf")}, data={"persist": "false"})
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["gross"] == 1


def test_tools_grim():
    r = client.post("/api/tools/grim", json={"mean": "5.19", "n": 28}).json()
    assert r["grim_consistent"] is False
    r = client.post("/api/tools/grim", json={"mean": "5.19", "n": 32}).json()
    assert r["grim_consistent"] is True
    r = client.post("/api/tools/grim", json={"mean": "3.50", "n": 30, "sd": "1.00"}).json()
    assert r["grim_consistent"] and r["grimmer_consistent"] is False
    assert client.post("/api/tools/grim", json={"mean": "abc", "n": 5}).status_code == 422
    assert client.post("/api/tools/grim", json={"mean": "3.5", "n": 0}).status_code == 422
    assert client.post("/api/tools/grim", json={"mean": "3.5", "n": 10, "items": 2, "sd": "1.0"}).status_code == 422


def test_tools_pvalue():
    r = client.post("/api/tools/pvalue", json={"kind": "t", "stat": "2.20", "df1": 28, "p": ".036"}).json()
    assert r["consistent"] and abs(r["computed_p"] - 0.0362) < 5e-4
    r = client.post("/api/tools/pvalue", json={"kind": "t", "stat": "2.20", "df1": 28, "p": ".2"}).json()
    assert not r["consistent"]
    assert client.post("/api/tools/pvalue", json={"kind": "F", "stat": "2.0", "df1": 2, "p": ".1"}).status_code == 422
    assert client.post("/api/tools/pvalue", json={"kind": "r", "stat": "1.5", "df1": 20, "p": ".1"}).status_code == 422


def test_samples_endpoint():
    lst = client.get("/api/samples").json()
    assert {s["id"] for s in lst} == {"clean", "flawed", "corrections"}
    assert "text" in client.get("/api/samples/flawed").json()
    assert client.get("/api/samples/nope").status_code == 404


def test_sample_expectations():
    """The demo manuscripts must behave exactly as the docs claim."""
    for sid, expect in [("clean", {"gross": 0, "minor": 0}), ("flawed", {"gross": 6, "minor": 1})]:
        t = client.get(f"/api/samples/{sid}").json()["text"]
        s = client.post("/api/analyze", json={"text": t, "persist": False}).json()["summary"]["by_status"]
        for k, v in expect.items():
            assert s.get(k, 0) == v, (sid, k, s)


def test_rate_limit(monkeypatch):
    import app.main as m
    monkeypatch.setattr(m, "RATE", 3)
    m._hits.clear()
    codes = [client.post("/api/analyze", json={"text": FLAWED, "persist": False}).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429
    m._hits.clear()
