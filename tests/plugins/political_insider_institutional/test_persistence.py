from alpha_engine.plugins.political_insider_institutional.persistence.ports import ProjectionRepository


class FakeHost:
    def __init__(self): self.data = {}; self.versions = {}
    def get(self, namespace, key): return self.data.get((namespace, key))
    def put(self, namespace, key, value, *, expected_version=None):
        cur = self.versions.get((namespace,key), 0)
        if expected_version is not None and expected_version != cur: raise RuntimeError("version_conflict")
        self.data[(namespace,key)] = dict(value); self.versions[(namespace,key)] = cur + 1; return cur + 1
    def delete(self, namespace, key, *, expected_version=None): self.data.pop((namespace,key), None)


def test_projection_uses_host_namespace_only():
    host = FakeHost(); repo = ProjectionRepository(host)
    v = repo.upsert_projection("x", {"status":"ok"})
    assert v == 1
    assert repo.get_projection("x") == {"status":"ok"}
    assert ("plugin_pii_projection_activity", "x") in host.data
