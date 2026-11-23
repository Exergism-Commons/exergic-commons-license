#!/usr/bin/env python3
"""End-to-end checks that compact ABox JSON and RDF expansion stay equivalent."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import sys
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import strict_json  # noqa: E402
ECL = Namespace("https://id.exergism.org/ecl#")
EC = Namespace("https://id.exergism.org/commons#")
# Entity classes reused from Commons; the other entity types are ECL vocabulary.
COMMONS_ENTITY_CLASSES = {"Organization", "Person"}


class JsonLdContextSemanticEquivalenceTests(unittest.TestCase):
    def test_every_entity_raw_identity_matches_rdf_expansion(self) -> None:
        paths = sorted(set((ROOT / "knowledge/entities").rglob("*.json")) | set((ROOT / "knowledge/entities").rglob("*.jsonld")))
        self.assertTrue(paths)
        for path in paths:
            record = strict_json.load(path)
            entity_id = record["id"]
            entity_type = record["type"]
            subject = URIRef(f"urn:ecl:{entity_id}")
            graph = Graph().parse(path, format="json-ld")
            with self.subTest(path=str(path.relative_to(ROOT))):
                entity_class = (EC if entity_type in COMMONS_ENTITY_CLASSES else ECL)[entity_type]
                self.assertIn((subject, RDF.type, entity_class), graph)
                self.assertIn((subject, EC.stableId, Literal(entity_id)), graph)

    def test_representative_relation_aliases_expand_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ontology").mkdir(parents=True)
            (root / "knowledge/entities").mkdir(parents=True)
            shutil.copy2(ROOT / "ontology/ecl-context.jsonld", root / "ontology/ecl-context.jsonld")
            fixture = root / "knowledge/entities/ORG-SOURCE.json"
            fixture.write_text(
                json.dumps(
                    {
                        "@context": "../../ontology/ecl-context.jsonld",
                        "iri": "urn:ecl:ORG-SOURCE",
                        "id": "ORG-SOURCE",
                        "type": "Organization",
                        "identityLifecycle": "superseded",
                        "supersededBy": "urn:ecl:ORG-SUCCESSOR",
                        "partOf": ["urn:ecl:ORG-PARENT"],
                        "controls": "urn:ecl:PROJECT-CONTROLLED",
                        "participatesIn": "urn:ecl:PROJECT-PARTICIPATION",
                        "operates": "urn:ecl:PROJECT-OPERATED",
                        "deploys": "urn:ecl:DEPLOYMENT-X",
                    }
                ),
                encoding="utf-8",
            )
            graph = Graph().parse(fixture, format="json-ld")
            source = URIRef("urn:ecl:ORG-SOURCE")
            self.assertIn((source, RDF.type, EC.Organization), graph)
            self.assertIn((source, EC.stableId, Literal("ORG-SOURCE")), graph)
            self.assertIn((source, EC.status, Literal("superseded")), graph)
            self.assertIn((source, ECL.partOf, URIRef("urn:ecl:ORG-PARENT")), graph)
            self.assertIn((source, ECL.controls, URIRef("urn:ecl:PROJECT-CONTROLLED")), graph)
            self.assertIn((source, ECL.participatesIn, URIRef("urn:ecl:PROJECT-PARTICIPATION")), graph)
            self.assertIn((source, ECL.operates, URIRef("urn:ecl:PROJECT-OPERATED")), graph)
            self.assertIn((source, ECL.deploys, URIRef("urn:ecl:DEPLOYMENT-X")), graph)
            self.assertIn((URIRef("urn:ecl:ORG-SUCCESSOR"), EC.supersedes, source), graph)


if __name__ == "__main__":
    unittest.main(verbosity=2)
