import importlib.util
import tempfile
import unittest
from pathlib import Path

from rdflib import URIRef

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_sparql_checks", ROOT / "tools" / "run_sparql_checks.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RunSparqlChecksTests(unittest.TestCase):
    def test_nquads_named_graphs_are_visible_to_integrity_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.nq"
            path.write_text(
                '<urn:ecl:CLAIM-X> <urn:ecl:status> "accepted" <urn:ecl:graph:claims> .\n',
                encoding="utf-8",
            )

            graph = MODULE.load_query_graph(path)
            rows = list(
                graph.query(
                    "SELECT ?claim WHERE { ?claim <urn:ecl:status> \"accepted\" . }"
                )
            )

            self.assertEqual([row.claim for row in rows], [URIRef("urn:ecl:CLAIM-X")])

    def test_trig_named_graphs_are_visible_to_integrity_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.trig"
            path.write_text(
                "<urn:ecl:graph:claims> { <urn:ecl:CLAIM-X> <urn:ecl:status> \"accepted\" . }\n",
                encoding="utf-8",
            )

            graph = MODULE.load_query_graph(path)
            rows = list(
                graph.query(
                    "SELECT ?claim WHERE { ?claim <urn:ecl:status> \"accepted\" . }"
                )
            )

            self.assertEqual([row.claim for row in rows], [URIRef("urn:ecl:CLAIM-X")])


if __name__ == "__main__":
    unittest.main()
