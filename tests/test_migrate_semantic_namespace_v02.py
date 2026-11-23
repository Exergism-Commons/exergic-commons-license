import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "migrate_semantic_namespace_v02", ROOT / "tools" / "migrate_semantic_namespace_v02.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

ECL = "https://id.exergism.org/ecl#"
EC = "https://id.exergism.org/commons#"


def migrate(name: str, text: str) -> str:
    return MODULE.migrate_text(Path(name), text)


class VocabularyOnlyMigrationTests(unittest.TestCase):
    def assert_idempotent(self, name: str, text: str) -> str:
        once = migrate(name, text)
        self.assertEqual(migrate(name, once), once)
        return once

    def test_jsonld_record_moves_terms_and_spells_out_instances(self):
        record = {
            "@context": "../../ontology/ecl-context.jsonld",
            "iri": "ecl:CLAIM-USA-TRACKS-X",
            "subject": "ecl:STATE-USA",
            "predicate": "ecl:status",
            "object": "ecl:PROJECT-X",
            "evidenceFor": ["ecl:EVIDENCE-X-2026-08-14"],
            "affectedVariables": ["ecl:P", "ecl:V_ep"],
            "affectedCriteria": ["ecl:ECL5_1"],
        }
        migrated = json.loads(self.assert_idempotent("claim.json", json.dumps(record)))
        self.assertEqual(migrated["iri"], "urn:ecl:CLAIM-USA-TRACKS-X")
        self.assertEqual(migrated["subject"], "urn:ecl:STATE-USA")
        self.assertEqual(migrated["object"], "urn:ecl:PROJECT-X")
        self.assertEqual(migrated["evidenceFor"], ["urn:ecl:EVIDENCE-X-2026-08-14"])
        self.assertEqual(migrated["predicate"], "ec:status")
        self.assertEqual(migrated["affectedVariables"], ["ex:P", "ex:V_ep"])
        self.assertEqual(migrated["affectedCriteria"], ["ecl:ECL5_1"])

    def test_iri_key_is_an_instance_even_when_it_looks_like_a_variable(self):
        text = '{"iri": "ecl:A", "id": "A"} {"iri": "ecl:DUPLICATE"}'
        self.assertEqual(
            self.assert_idempotent("record.json", text),
            '{"iri": "urn:ecl:A", "id": "A"} {"iri": "urn:ecl:DUPLICATE"}',
        )

    def test_full_iris_move_only_vocabulary(self):
        text = (
            '<urn:ecl:CLAIM-X> <urn:ecl:status> "accepted" <urn:ecl:graph:claims> .\n'
            '"$id": "urn:ecl:schema:entity"\n'
            'FILTER (STRSTARTS(STR(?x), "urn:ecl:")) CONCAT("urn:ecl:STATE-", ?iso)\n'
            '"urn:ecl:subject": [{"@id": "urn:ecl:tracks"}, {"@id": "urn:ecl:STATE-USA"}]\n'
            "<urn:ecl:GovernanceDecision> <urn:ecl:P> <urn:ecl:ontology>\n"
        )
        self.assertEqual(
            self.assert_idempotent("fixture.py", text),
            f'<urn:ecl:CLAIM-X> <{EC}status> "accepted" <urn:ecl:graph:claims> .\n'
            '"$id": "urn:ecl:schema:entity"\n'
            'FILTER (STRSTARTS(STR(?x), "urn:ecl:")) CONCAT("urn:ecl:STATE-", ?iso)\n'
            f'"{ECL}subject": [{{"@id": "{ECL}tracks"}}, {{"@id": "urn:ecl:STATE-USA"}}]\n'
            f"<{ECL}ECLGovernanceDecision> <https://id.exergism.org/exergism#P> "
            "<https://id.exergism.org/ontology/ecl>\n",
        )

    def test_instances_never_stay_in_the_vocabulary_namespace(self):
        text = f'CONCAT("{ECL}STATE-", ?iso) <{ECL}PROJECT-X> <{ECL}ECL5_1>'
        self.assertEqual(
            self.assert_idempotent("shape.ttl", text),
            f'CONCAT("urn:ecl:STATE-", ?iso) <urn:ecl:PROJECT-X> <{ECL}ECL5_1>',
        )

    def test_turtle_and_embedded_sparql_get_the_prefixes_they_use(self):
        text = (
            "@prefix ecl: <urn:ecl:> .\n"
            "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
            "ecl:STATE-USA a ecl:State ; ecl:stableId \"STATE-USA\" ; ecl:partOf ecl:AGENCY-X .\n"
            "ecl:GovernanceDecisionShape sh:targetClass ecl:GovernanceDecision ;\n"
            '    sh:select """\n'
            "        PREFIX ecl: <urn:ecl:>\n"
            "        SELECT $this WHERE { $this ecl:reviewDue ?due ; ecl:affectedVariable ecl:S . }\n"
            '    """ .\n'
        )
        self.assertEqual(
            self.assert_idempotent("shapes.ttl", text),
            f"@prefix ec: <{EC}> .\n"
            f"@prefix ecl: <{ECL}> .\n"
            "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
            "<urn:ecl:STATE-USA> a ecl:State ; ec:stableId \"STATE-USA\" ; ecl:partOf <urn:ecl:AGENCY-X> .\n"
            "ecl:ECLGovernanceDecisionShape sh:targetClass ecl:ECLGovernanceDecision ;\n"
            '    sh:select """\n'
            f"        PREFIX ec: <{EC}>\n"
            "        PREFIX ex: <https://id.exergism.org/exergism#>\n"
            f"        PREFIX ecl: <{ECL}>\n"
            "        SELECT $this WHERE { $this ec:reviewDue ?due ; ecl:affectedVariable ex:S . }\n"
            '    """ .\n',
        )

    def test_python_namespaces_subscripts_and_interpolation(self):
        text = (
            "from rdflib import Graph, Namespace\n"
            'ECL = Namespace("urn:ecl:")\n'
            'state = ECL["STATE-USA"]\n'
            'claim = ECL[f"CLAIM-TEST-{index}"]\n'
            'predicate = ECL["governance__status"]\n'
            "graph.add((state, ECL.stableId, ECL.Agency))\n"
            'expected = {"iri": f"ecl:{item_id}", "projection": f"ecl:STATE-{iso3}"}\n'
            'BUILD_SPEC.loader.exec_module(BUILD)\n'
        )
        self.assertEqual(
            self.assert_idempotent("test_sample.py", text),
            "from rdflib import Graph, Namespace, URIRef\n"
            f'ECL = Namespace("{ECL}")\n'
            f'EC = Namespace("{EC}")\n'
            'state = URIRef("urn:ecl:STATE-USA")\n'
            'claim = URIRef(f"urn:ecl:CLAIM-TEST-{index}")\n'
            'predicate = ECL["governance__status"]\n'
            "graph.add((state, EC.stableId, ECL.Agency))\n"
            'expected = {"iri": f"urn:ecl:{item_id}", "projection": f"urn:ecl:STATE-{iso3}"}\n'
            'BUILD_SPEC.loader.exec_module(BUILD)\n',
        )

    def test_prefix_strings_and_dynamic_code_are_left_for_review(self):
        text = 'if value.startswith("ecl:"):\n    claim = ECL[stable_id]\n'
        self.assertEqual(migrate("tool.py", text), text)
        self.assertTrue(MODULE.REVIEW_PATTERNS[0][0].search(text))


if __name__ == "__main__":
    unittest.main()
