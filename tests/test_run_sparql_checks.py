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
                '<https://id.exergism.org/ecl#CLAIM-X> <https://id.exergism.org/ecl#status> "accepted" <https://id.exergism.org/ecl#graph:claims> .\n',
                encoding="utf-8",
            )

            graph = MODULE.load_query_graph(path)
            rows = list(
                graph.query(
                    "SELECT ?claim WHERE { ?claim <https://id.exergism.org/ecl#status> \"accepted\" . }"
                )
            )

            self.assertEqual([row.claim for row in rows], [URIRef("https://id.exergism.org/ecl#CLAIM-X")])

    def test_trig_named_graphs_are_visible_to_integrity_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.trig"
            path.write_text(
                "<https://id.exergism.org/ecl#graph:claims> { <https://id.exergism.org/ecl#CLAIM-X> <https://id.exergism.org/ecl#status> \"accepted\" . }\n",
                encoding="utf-8",
            )

            graph = MODULE.load_query_graph(path)
            rows = list(
                graph.query(
                    "SELECT ?claim WHERE { ?claim <https://id.exergism.org/ecl#status> \"accepted\" . }"
                )
            )

            self.assertEqual([row.claim for row in rows], [URIRef("https://id.exergism.org/ecl#CLAIM-X")])


if __name__ == "__main__":
    unittest.main()
