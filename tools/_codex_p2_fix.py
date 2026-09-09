#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one anchor in {path}: {old[:80]!r}; found {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# P2: preserve every ancestor clip in SVG text visibility.
visual = ROOT / "tools/check_visual_evidence_semantics.py"
replace_once(
    visual,
    """        inherited_clip: str | None,\n    ) -> tuple[float | None, float | None]:""",
    """        inherited_clips: tuple[str, ...],\n    ) -> tuple[float | None, float | None]:""",
)
replace_once(
    visual,
    """        own_clip_raw = element.get(\"clip-path\")\n        if own_clip_raw is not None:\n            own_clip = _clip_id(own_clip_raw)\n            if own_clip is None or own_clip not in clips:\n                invalid = True\n                return x, y\n            clip = own_clip\n        else:\n            clip = inherited_clip\n\n        semantic_text_node = tag in {\"text\", \"tspan\"}\n        visible = not hidden and _inside(bounds, x, y)\n        if clip is not None:\n            visible = visible and _inside(clips.get(clip), x, y)\n""",
    """        clip_chain = inherited_clips\n        own_clip_raw = element.get(\"clip-path\")\n        if own_clip_raw is not None:\n            own_clip = _clip_id(own_clip_raw)\n            if own_clip is None or own_clip not in clips:\n                invalid = True\n                return x, y\n            clip_chain = (*inherited_clips, own_clip)\n\n        semantic_text_node = tag in {\"text\", \"tspan\"}\n        visible = not hidden and _inside(bounds, x, y)\n        if visible:\n            visible = all(_inside(clips[clip_id], x, y) for clip_id in clip_chain)\n""",
)
replace_once(
    visual,
    """            child_x, child_y = walk(child, hidden, cursor_x, cursor_y, clip)""",
    """            child_x, child_y = walk(child, hidden, cursor_x, cursor_y, clip_chain)""",
)
replace_once(
    visual,
    """    walk(root, False, None, None, None)""",
    """    walk(root, False, None, None, ())""",
)

# P2 regression for nested tspan clips.
policy_test = ROOT / "tests/test_canonical_entity_dossier_policy_hardening.py"
insert = '''\n    def test_nested_tspan_clip_cannot_replace_narrower_ancestor_clip(self) -> None:\n        with tempfile.TemporaryDirectory() as tmp:\n            root = Path(tmp)\n            generated = root / "dossiers/assets/generated"\n            generated.mkdir(parents=True)\n            path = generated / "X-status.svg"\n            path.write_text(\n                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'\n                '<defs>'\n                '<clipPath id="outer"><rect x="0" y="0" width="20" height="20"/></clipPath>'\n                '<clipPath id="inner"><rect x="0" y="0" width="100" height="100"/></clipPath>'\n                '</defs>'\n                '<text x="10" y="10">'\n                '<tspan clip-path="url(#outer)">'\n                '<tspan x="50" y="50" clip-path="url(#inner)">REQUIRED</tspan>'\n                '</tspan>'\n                '</text></svg>',\n                encoding="utf-8",\n            )\n            visible = semantics.visible_svg_text(path) or ""\n            self.assertNotIn("REQUIRED", visible)\n'''
replace_once(
    policy_test,
    "\n\nif __name__ == \"__main__\":\n    unittest.main(verbosity=2)\n",
    insert + "\n\nif __name__ == \"__main__\":\n    unittest.main(verbosity=2)\n",
)

# P2: use the shared recursive canonical entity surface in the identity-integrity gate.
integrity = ROOT / "tools/check_non_state_entity_identity_integrity.py"
replace_once(
    integrity,
    """def validate() -> list[dict]:\n    failures: list[dict] = []\n    ids: dict[str, list[str]] = defaultdict(list)\n\n    for path in sorted(ENTITY_DIR.glob(\"*.json\")):\n""",
    """def validate(\n    root: Path = ROOT,\n    entity_dir: Path | None = None,\n    dossier_root: Path | None = None,\n) -> list[dict]:\n    failures: list[dict] = []\n    ids: dict[str, list[str]] = defaultdict(list)\n    entity_dir = root / \"knowledge/entities\" if entity_dir is None else entity_dir\n    dossier_root = (root / \"dossiers\").resolve() if dossier_root is None else dossier_root.resolve()\n    canonical_context = (root / \"ontology/ecl-context.jsonld\").resolve()\n\n    for path in identity.repository_entity_paths(entity_dir):\n""",
)
replace_once(
    integrity,
    """        rel = str(path.relative_to(ROOT))""",
    """        rel = str(path.relative_to(root))""",
)
replace_once(
    integrity,
    """        if data.get(\"@context\") != \"../../ontology/ecl-context.jsonld\":\n            failures.append({\"file\": rel, \"id\": entity_id, \"reason\": \"unexpected JSON-LD context\", \"value\": data.get(\"@context\")})\n""",
    """        context = data.get(\"@context\")\n        context_target = (path.parent / context).resolve() if isinstance(context, str) and context else None\n        if context_target != canonical_context:\n            failures.append({\"file\": rel, \"id\": entity_id, \"reason\": \"unexpected JSON-LD context\", \"value\": context})\n""",
)
replace_once(
    integrity,
    """            elif not inside(target, DOSSIER_ROOT):""",
    """            elif not inside(target, dossier_root):""",
)

# P2 regression for recursive .jsonld identity-prefix integrity.
identity_test = ROOT / "tests/test_canonical_entity_dossier_codex_p2_regressions.py"
replace_once(
    identity_test,
    """import check_canonical_entity_manifest_history as history  # noqa: E402\nimport entity_identity_resolution as resolver  # noqa: E402\n""",
    """import check_canonical_entity_manifest_history as history  # noqa: E402\nimport check_non_state_entity_identity_integrity as identity_integrity  # noqa: E402\nimport entity_identity_resolution as resolver  # noqa: E402\n""",
)
identity_insert = '''\n    def test_recursive_jsonld_identity_integrity_enforces_type_prefix(self) -> None:\n        with tempfile.TemporaryDirectory() as tmp:\n            root = Path(tmp)\n            entity_dir = root / "knowledge/entities/nested"\n            entity_dir.mkdir(parents=True)\n            (root / "ontology").mkdir(parents=True)\n            (root / "ontology/ecl-context.jsonld").write_text("{}", encoding="utf-8")\n            dossier = root / "dossiers/organizations/PERSON-WRONG.md"\n            dossier.parent.mkdir(parents=True)\n            dossier.write_text("# Identity\\n", encoding="utf-8")\n            record = {\n                "@context": "../../../ontology/ecl-context.jsonld",\n                "iri": "ecl:PERSON-WRONG",\n                "id": "PERSON-WRONG",\n                "type": "Organization",\n                "name": "Wrong Prefix Organization",\n                "dossier": "../../../dossiers/organizations/PERSON-WRONG.md",\n            }\n            (entity_dir / "PERSON-WRONG.jsonld").write_text(json.dumps(record), encoding="utf-8")\n            failures = identity_integrity.validate(root=root)\n        self.assertTrue(\n            any(item.get("reason") == "type/id-prefix mismatch" and item.get("id") == "PERSON-WRONG" for item in failures),\n            failures,\n        )\n'''
replace_once(
    identity_test,
    "\n\nif __name__ == \"__main__\":\n    unittest.main(verbosity=2)\n",
    identity_insert + "\n\nif __name__ == \"__main__\":\n    unittest.main(verbosity=2)\n",
)

# Remove temporary scaffolding before the product commit.
(ROOT / "tools/_codex_p2_fix.py").unlink()
workflow = ROOT / ".github/workflows/_codex-p2-fix.yml"
if workflow.exists():
    workflow.unlink()
