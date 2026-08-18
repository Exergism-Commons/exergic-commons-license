#!/usr/bin/env python3
# Render deterministic SVG visual evidence for canonical entity dossiers.

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_DIR = ROOT / "knowledge/generated"
DEFAULT_PALETTE = ROOT / "knowledge/generated/dossier-visual-palette-v1.json"
DEFAULT_OUT = ROOT / "dossiers/assets/generated"


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_entities(manifest_dir: Path) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    manifests = sorted(
        manifest_dir.glob("canonical-entity-dossier-migration-v*.json"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
    if not manifests:
        raise SystemExit("no canonical entity dossier migration manifests found")
    for path in manifests:
        manifest = load_json(path)
        for row in manifest["entities"]:
            entity_id = row["id"]
            if entity_id in seen:
                raise SystemExit(f"duplicate migrated entity across manifests: {entity_id}")
            seen.add(entity_id)
            rows.append(row)
    return rows


def status_svg(entity: dict, palette: dict) -> str:
    state = entity["stateContext"]
    swatch = palette["states"][state]
    name = entity["name"]
    state_code = entity["state"]
    label = swatch["label"]
    color = swatch["hex"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="260" viewBox="0 0 960 260" role="img" aria-labelledby="title desc">
  <title id="title">{esc(name)} — State dossier context {esc(state)}</title>
  <desc id="desc">Derived status card. The {esc(state_code)} State dossier is {esc(state)} — {esc(label)}. This status is context only and is not inherited by {esc(name)}.</desc>
  <rect width="960" height="260" rx="18" fill="#FFFFFF" stroke="#D0D5DD"/>
  <rect width="18" height="260" rx="9" fill="{esc(color)}"/>
  <text x="54" y="58" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="700" fill="#101828">STATE DOSSIER CONTEXT</text>
  <text x="54" y="104" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" fill="#101828">{esc(name)}</text>
  <rect x="54" y="130" width="250" height="58" rx="12" fill="{esc(color)}"/>
  <text x="76" y="168" font-family="Arial, Helvetica, sans-serif" font-size="28" font-weight="700" fill="#FFFFFF">{esc(state)} · {esc(label)}</text>
  <text x="330" y="153" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" fill="#344054">{esc(state_code)} State dossier</text>
  <text x="330" y="181" font-family="Arial, Helvetica, sans-serif" font-size="17" fill="#475467">Context only — no entity-level governance inheritance</text>
  <line x1="54" y1="212" x2="906" y2="212" stroke="#EAECF0"/>
  <text x="54" y="239" font-family="Arial, Helvetica, sans-serif" font-size="15" fill="#667085">Color is never the sole signal: the state letter and label are always rendered.</text>
</svg>
'''


def evidence_svg(entity: dict) -> str:
    name = entity["name"]
    source = entity["visualModel"]["source"]
    proposition = entity["visualModel"]["proposition"]
    boundary = entity["visualModel"]["boundary"]
    granularity = entity["sourceGranularity"]
    granularity_label = "direct locator" if granularity == "direct" else "partial locator / explicit gap"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="360" viewBox="0 0 1100 360" role="img" aria-labelledby="title desc">
  <title id="title">{esc(name)} — derived evidence diagram</title>
  <desc id="desc">Derived evidence diagram linking the curated source surface to the dossier proposition and then to the entity identity, while preserving a no-governance-inheritance boundary.</desc>
  <rect width="1100" height="360" rx="18" fill="#FFFFFF" stroke="#D0D5DD"/>
  <text x="40" y="48" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="700" fill="#101828">DERIVED EVIDENCE DIAGRAM</text>
  <text x="40" y="76" font-family="Arial, Helvetica, sans-serif" font-size="15" fill="#667085">Not a source facsimile · textual equivalent is preserved in the dossier</text>

  <rect x="40" y="118" width="285" height="130" rx="14" fill="#F9FAFB" stroke="#98A2B3"/>
  <text x="62" y="149" font-family="Arial, Helvetica, sans-serif" font-size="15" font-weight="700" fill="#344054">SOURCE SURFACE</text>
  <text x="62" y="184" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" fill="#101828">{esc(source)}</text>
  <text x="62" y="219" font-family="Arial, Helvetica, sans-serif" font-size="14" fill="#667085">{esc(granularity_label)}</text>

  <line x1="325" y1="183" x2="395" y2="183" stroke="#667085" stroke-width="2"/>
  <polygon points="395,183 383,176 383,190" fill="#667085"/>

  <rect x="405" y="118" width="285" height="130" rx="14" fill="#F9FAFB" stroke="#98A2B3"/>
  <text x="427" y="149" font-family="Arial, Helvetica, sans-serif" font-size="15" font-weight="700" fill="#344054">CURATED PROPOSITION</text>
  <text x="427" y="184" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" fill="#101828">{esc(proposition)}</text>
  <text x="427" y="219" font-family="Arial, Helvetica, sans-serif" font-size="14" fill="#667085">Prose evidence; no Claim/EvidenceItem invented</text>

  <line x1="690" y1="183" x2="760" y2="183" stroke="#667085" stroke-width="2"/>
  <polygon points="760,183 748,176 748,190" fill="#667085"/>

  <rect x="770" y="118" width="290" height="130" rx="14" fill="#F9FAFB" stroke="#98A2B3"/>
  <text x="792" y="149" font-family="Arial, Helvetica, sans-serif" font-size="15" font-weight="700" fill="#344054">IDENTITY BOUNDARY</text>
  <text x="792" y="184" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" fill="#101828">{esc(name)}</text>
  <text x="792" y="219" font-family="Arial, Helvetica, sans-serif" font-size="14" fill="#667085">Identity ≠ participation / culpability</text>

  <rect x="40" y="284" width="1020" height="46" rx="10" fill="#F2F4F7"/>
  <text x="60" y="313" font-family="Arial, Helvetica, sans-serif" font-size="16" font-weight="700" fill="#344054">BOUNDARY:</text>
  <text x="160" y="313" font-family="Arial, Helvetica, sans-serif" font-size="16" fill="#475467">{esc(boundary)} · no partOf/control/operation/participation/supplier inference</text>
</svg>
'''


def legend_svg(palette: dict) -> str:
    order = ["R", "S", "U", "N", "UNKNOWN"]
    x = 40
    blocks = []
    for key in order:
        item = palette["states"][key]
        blocks.append(
            f'  <rect x="{x}" y="92" width="168" height="78" rx="12" fill="{esc(item["hex"])}"/>\n'
            f'  <text x="{x+18}" y="122" font-family="Arial, Helvetica, sans-serif" font-size="23" font-weight="700" fill="#FFFFFF">{esc(key)}</text>\n'
            f'  <text x="{x+18}" y="150" font-family="Arial, Helvetica, sans-serif" font-size="14" fill="#FFFFFF">{esc(item["label"])}</text>'
        )
        x += 184
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="230" viewBox="0 0 1000 230" role="img" aria-labelledby="title desc">
  <title id="title">ECL dossier state-context palette</title>
  <desc id="desc">Canonical R, S, U, N and unknown colors. Letters and labels accompany every swatch; colors are never entity culpability scores.</desc>
  <rect width="1000" height="230" rx="18" fill="#FFFFFF" stroke="#D0D5DD"/>
  <text x="40" y="47" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700" fill="#101828">ECL STATE-CONTEXT PALETTE</text>
  <text x="40" y="73" font-family="Arial, Helvetica, sans-serif" font-size="15" fill="#667085">Rendering vocabulary only · not a severity scale · no governance inheritance</text>
{chr(10).join(blocks)}
  <text x="40" y="208" font-family="Arial, Helvetica, sans-serif" font-size="14" fill="#667085">Always render letter + text label together with color.</text>
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--palette", type=Path, default=DEFAULT_PALETTE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows = load_entities(args.manifest_dir)
    palette = load_json(args.palette)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "state-outcome-legend.svg").write_text(legend_svg(palette), encoding="utf-8")
    for entity in rows:
        (args.out / f'{entity["id"]}-status.svg').write_text(status_svg(entity, palette), encoding="utf-8")
        (args.out / f'{entity["id"]}-evidence.svg').write_text(evidence_svg(entity), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
