from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PluginCandidate:
    plugin_id: str
    name: str
    version: str
    core_contract: str
    entrypoint: str | None
    manifest_path: str
    package_root: str
    status: str
    reasons: tuple[str, ...] = ()


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list:
            data.setdefault(current_list, []).append(line[4:].strip().strip('"\''))
            continue
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            data[key] = []
            current_list = key
        else:
            current_list = None
            data[key] = value.strip('"\'')
    return data


def _python_manifest_metadata(path: Path) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    plugin_id = None
    version = None
    for pattern in [r'PLUGIN_ID\s*=\s*["\']([^"\']+)', r'plugin_id\s*=\s*["\']([^"\']+)']:
        match = re.search(pattern, text)
        if match:
            plugin_id = match.group(1)
            break
    for pattern in [r'PLUGIN_VERSION\s*=\s*["\']([^"\']+)', r'plugin_version\s*=\s*["\']([^"\']+)', r'version\s*=\s*["\']([^"\']+)']:
        match = re.search(pattern, text)
        if match:
            version = match.group(1)
            break
    contract_match = re.search(r'core_contract\s*=\s*["\']([^"\']+)', text)
    if not plugin_id:
        return None
    return {
        "plugin_id": plugin_id,
        "name": plugin_id,
        "version": version or "unknown",
        "core_contract": contract_match.group(1) if contract_match else "unknown",
        "entrypoint": "python-manifest-only",
    }


def discover_plugin_candidates(repo_root: str | Path) -> list[PluginCandidate]:
    root = Path(repo_root)
    raw: list[dict[str, Any]] = []
    for manifest in sorted((root / "plugins").glob("*/plugin.toml")) + sorted(
        (root / "plugins").glob("*/manifest.toml")
    ):
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        raw.append({**data, "manifest_path": manifest, "package_root": manifest.parent})
    for manifest in sorted((root / "plugins").glob("*/plugin.yaml")):
        data = _parse_simple_yaml(manifest)
        pyproject = manifest.parent / "pyproject.toml"
        if pyproject.exists():
            pydata = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            entrypoints = pydata.get("project", {}).get("entry-points", {}).get("alpha_engine.plugins", {})
            if entrypoints and not data.get("entrypoint"):
                data["entrypoint"] = next(iter(entrypoints.values()))
        raw.append({**data, "manifest_path": manifest, "package_root": manifest.parent})

    python_manifests = list((root / "src").glob("*/manifest.py")) + list(
        (root / "src" / "alpha_engine" / "plugins").glob("*/manifest.py")
    )
    for manifest in sorted(python_manifests):
        data = _python_manifest_metadata(manifest)
        if data:
            raw.append({**data, "manifest_path": manifest, "package_root": manifest.parent})

    counts: dict[str, int] = {}
    for item in raw:
        pid = str(item.get("plugin_id", ""))
        counts[pid] = counts.get(pid, 0) + 1

    candidates: list[PluginCandidate] = []
    for item in raw:
        pid = str(item.get("plugin_id", ""))
        reasons: list[str] = []
        contract = str(item.get("core_contract", "unknown"))
        entrypoint = item.get("entrypoint")
        if counts.get(pid, 0) > 1:
            reasons.append("duplicate plugin_id implementation")
        if contract != "1.0":
            reasons.append(f"core contract is not exact frozen 1.0: {contract}")
        if not entrypoint or entrypoint == "python-manifest-only":
            reasons.append("no loadable public entrypoint declared")
        status = "CANDIDATE" if not reasons else "BLOCKED"
        candidates.append(
            PluginCandidate(
                plugin_id=pid,
                name=str(item.get("name") or pid),
                version=str(item.get("version") or item.get("plugin_version") or "unknown"),
                core_contract=contract,
                entrypoint=str(entrypoint) if entrypoint else None,
                manifest_path=str(Path(item["manifest_path"]).relative_to(root)),
                package_root=str(Path(item["package_root"]).relative_to(root)),
                status=status,
                reasons=tuple(reasons),
            )
        )
    return candidates
