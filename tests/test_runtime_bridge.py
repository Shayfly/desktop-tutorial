from live_core.runtime_bridge import generate_export, runtime_request


def test_runtime_status_bridge():
    response = runtime_request("GET", "/api/status")
    assert response.status_code == 200, response.text
    assert response.json()["product"] == "148AI"


def test_generate_export_uses_real_packaged_runtime():
    blob = generate_export(
        prompt="Build a tiny Hebrew learning game with one clickable button",
        title="Hebrew Learning Game",
        target_markets=["IL"],
    )
    assert isinstance(blob, bytes)
    assert blob.startswith(b"PK")
    assert len(blob) > 100
