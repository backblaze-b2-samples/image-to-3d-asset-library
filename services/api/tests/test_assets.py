"""Hermetic tests for the image -> 3D asset library.

No B2, no ML, no model download: the B2 boundary (asset_store + manifest) is
replaced with an in-memory fake, the generation engine is a fake returning tiny
deterministic bytes, and the background job runs inline. This exercises dedup,
write-amplification math, manifest read/write, prefix delete, key validation,
and every /assets route without touching the network.
"""

import pytest

from app.repo import asset_store, engines, jobs, manifest
from app.repo.engines.base import EngineResult
from app.types import Asset, EngineInfo, GenerationEngine


class _FakeEngine:
    """Returns tiny deterministic bytes — never loads a model."""

    def __init__(self):
        self.calls = 0

    def info(self):
        return EngineInfo(
            name=GenerationEngine.TRIPOSR,
            label="Fake",
            description="test",
            deployment="local",
            device_requirement="any",
            is_default=True,
            available=True,
        )

    def available(self):
        return True

    def generate(self, image_bytes, params):
        self.calls += 1
        return EngineResult(
            glb_bytes=b"GLB-BINARY",
            preview_png=b"PNG",
            texture_maps={params.texture_resolution: b"TEX-BIG", 512: b"TEX"},
            obj_bytes=b"OBJDATA",
            stats={"engine": "fake", "device_used": "cpu", "generation_seconds": 0.01},
        )


@pytest.fixture(autouse=True)
def fake_backend(monkeypatch):
    """In-memory B2 + fake engine + inline job execution."""
    objects: dict[str, bytes] = {"uploads/cube.png": b"PNG-SOURCE-BYTES" * 8}
    manifests: dict[str, Asset] = {}
    engine = _FakeEngine()

    # --- engine + jobs ---
    monkeypatch.setattr(engines, "get_engine", lambda name: engine)
    monkeypatch.setattr(jobs, "submit", lambda asset_id, run: run())  # inline
    jobs._reset_state()

    # --- asset_store (B2 objects) ---
    def head(key):
        return {"ContentType": "image/png"} if key in objects else None

    def put_bytes(key, data, content_type):
        objects[key] = bytes(data)
        return len(data)

    def delete_prefix(prefix):
        keys = [k for k in objects if k.startswith(prefix)]
        for k in keys:
            del objects[k]
        return len(keys)

    monkeypatch.setattr(asset_store, "object_head", head)
    monkeypatch.setattr(asset_store, "get_bytes", lambda key: objects[key])
    monkeypatch.setattr(asset_store, "put_bytes", put_bytes)
    monkeypatch.setattr(asset_store, "delete_prefix", delete_prefix)
    monkeypatch.setattr(asset_store, "presign_inline", lambda key, **_: f"https://signed/{key}")

    # --- manifest (B2 JSON records) ---
    monkeypatch.setattr(
        manifest, "save_manifest", lambda asset: manifests.__setitem__(asset.id, asset.model_copy(deep=True))
    )
    monkeypatch.setattr(
        manifest, "load_manifest", lambda aid: manifests[aid].model_copy(deep=True) if aid in manifests else None
    )
    monkeypatch.setattr(
        manifest,
        "list_manifests",
        lambda: sorted((m.model_copy(deep=True) for m in manifests.values()), key=lambda a: a.created_at, reverse=True),
    )

    return {"objects": objects, "manifests": manifests, "engine": engine}


def _create_body(**over):
    body = {
        "input_key": "uploads/cube.png",
        "name": "Cube",
        "engine": "triposr",
        "texture_resolution": 1024,
        "remove_background": True,
    }
    body.update(over)
    return body


async def test_create_generates_and_completes(client, fake_backend):
    res = await client.post("/assets", json=_create_body())
    assert res.status_code == 201
    asset = res.json()
    assert asset["status"] == "complete"
    kinds = {a["kind"] for a in asset["artifacts"]}
    assert {"source", "mesh_glb", "mesh_obj", "preview", "texture"} <= kinds
    assert fake_backend["engine"].calls == 1


async def test_write_amplification_math(client):
    asset = (await client.post("/assets", json=_create_body())).json()
    output = sum(a["size_bytes"] for a in asset["artifacts"] if a["kind"] != "source")
    inp = asset["input_bytes"]
    amp = asset["write_amplification"]
    assert amp["input_bytes"] == inp
    assert amp["output_bytes"] == output
    assert amp["ratio"] == round(output / inp, 2)
    # object_count includes every artifact plus the manifest.json.
    assert amp["object_count"] == len(asset["artifacts"]) + 1


async def test_create_dedups_same_content_and_params(client, fake_backend):
    first = (await client.post("/assets", json=_create_body())).json()
    second = (await client.post("/assets", json=_create_body())).json()
    assert first["id"] == second["id"]
    # Second call must NOT re-run the engine (dedup on content + params).
    assert fake_backend["engine"].calls == 1


async def test_different_params_regenerate_via_create(client, fake_backend):
    await client.post("/assets", json=_create_body(texture_resolution=1024))
    await client.post("/assets", json=_create_body(texture_resolution=512))
    assert fake_backend["engine"].calls == 2


async def test_list_and_get_asset(client):
    created = (await client.post("/assets", json=_create_body())).json()
    listed = (await client.get("/assets")).json()
    assert any(a["id"] == created["id"] for a in listed)
    # Grid presigns the preview only.
    preview = next(a for a in listed[0]["artifacts"] if a["kind"] == "preview")
    assert preview["url"].startswith("https://signed/")

    detail = (await client.get(f"/assets/{created['id']}")).json()
    assert all(a["url"] for a in detail["artifacts"])  # detail presigns all


async def test_update_name_and_tags(client):
    created = (await client.post("/assets", json=_create_body())).json()
    res = await client.patch(
        f"/assets/{created['id']}", json={"name": "Renamed", "tags": ["prop", "hero"]}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Renamed"
    assert body["tags"] == ["prop", "hero"]


async def test_delete_removes_prefix(client, fake_backend):
    created = (await client.post("/assets", json=_create_body())).json()
    res = await client.delete(f"/assets/{created['id']}")
    assert res.status_code == 200
    assert res.json()["deleted"] is True
    # Manifest gone from the fake store; a follow-up read is 404.
    del fake_backend["manifests"][created["id"]]
    assert (await client.get(f"/assets/{created['id']}")).status_code == 404


async def test_regenerate_bumps_version(client, fake_backend):
    created = (await client.post("/assets", json=_create_body())).json()
    assert created["version"] == 1
    res = await client.post(
        f"/assets/{created['id']}/regenerate", json={"texture_resolution": 512}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["version"] == 2
    assert body["params"]["texture_resolution"] == 512
    assert fake_backend["engine"].calls == 2


async def test_stats_aggregate(client):
    await client.post("/assets", json=_create_body())
    stats = (await client.get("/assets/stats")).json()
    assert stats["total_assets"] == 1
    assert stats["amplification_ratio"] > 0
    assert stats["avg_objects_per_generation"] > 0
    assert "mesh_glb" in stats["by_artifact_type"]


async def test_engines_catalog(client):
    engines_list = (await client.get("/assets/engines")).json()
    names = {e["name"]: e for e in engines_list}
    assert set(names) == {"triposr", "hunyuan3d", "procedural"}
    assert names["triposr"]["is_default"] is True
    assert names["hunyuan3d"]["device_requirement"] == "gpu"


async def test_missing_source_is_400(client):
    res = await client.post("/assets", json=_create_body(input_key="uploads/nope.png"))
    assert res.status_code == 400


async def test_invalid_texture_resolution_is_400(client):
    res = await client.post("/assets", json=_create_body(texture_resolution=999))
    assert res.status_code == 400


async def test_get_unknown_asset_is_404(client):
    assert (await client.get("/assets/deadbeef")).status_code == 404


def test_content_hash_is_stable():
    from app.service.assets_hash import short_content_hash

    assert short_content_hash(b"abc") == short_content_hash(b"abc")
    assert short_content_hash(b"abc") != short_content_hash(b"xyz")
    assert len(short_content_hash(b"abc")) == 16


def test_engine_registry_defaults():
    assert isinstance(engines.get_engine("triposr").info().is_default, bool)
    assert engines.get_engine(GenerationEngine.PROCEDURAL).available() is True
