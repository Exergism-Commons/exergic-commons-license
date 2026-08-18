import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "report_exergism_coverage.py"
SPEC = importlib.util.spec_from_file_location('report_exergism_coverage', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FakeExergism:
    @staticmethod
    def calculate(assessment, profile):
        scores = {k: {'low': 0.1, 'central': 0.2, 'high': 0.3} for k in ('Ex_b','Pen','Ex_r','E_i','X_h','B_0')}
        if all(v in assessment.get('variables', {}) for v in MODULE.ADVANCED_VARS):
            scores.update({k: {'low': 0.1, 'central': 0.2, 'high': 0.3} for k in ('P_atr','E_i_adj','M_f')})
        return {'scores': scores}


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.old = MODULE.canonical_exergism
        MODULE.canonical_exergism = FakeExergism()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in ('knowledge/entities','knowledge/claims','knowledge/evidence','dossiers/states','dossiers/agencies','dossiers/projects','exergism/assessments','exergism/profiles','registry'):
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        (self.root/'exergism/profiles/test.json').write_text(json.dumps({'name':'test'}))

    def tearDown(self):
        MODULE.canonical_exergism = self.old
        self.tmp.cleanup()

    def write_json(self, rel, data):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

    def state(self, outcome='S'):
        self.write_json('knowledge/entities/STATE-AAA.json', {
            '@context':'../../ontology/ecl-context.jsonld', 'iri':'ecl:STATE-AAA', 'id':'STATE-AAA',
            'type':'State','name':'Alpha','iso3':'AAA','dossier':'../../dossiers/states/AAA.md',
            'publicReviewIssue':'https://example.test/issues/1','lastSubstantiveReview':'2026-08-17','reviewClass':'manual'
        })
        (self.root/'dossiers/states/AAA.md').write_text(
            '---\nid: ECL-STATE-AAA\nentity: Alpha\nprovisional_outcome: '+outcome+'\n'
            'provisional_scope: "Exact alpha project"\nevidence_cutoff: 2026-08-17\nlast_reviewed: 2026-08-17\n---\n# Alpha\n', encoding='utf-8')

    def claim(self):
        self.write_json('knowledge/evidence/EVIDENCE-A.json', {
            '@context':'../../ontology/ecl-context.jsonld','iri':'ecl:EVIDENCE-A','id':'EVIDENCE-A','type':'EvidenceItem',
            'sourceLocator':'https://example.test/source','provenance':['fixture']
        })
        self.write_json('knowledge/claims/CLAIM-A.json', {
            '@context':'../../ontology/ecl-context.jsonld','iri':'ecl:CLAIM-A','id':'CLAIM-A','type':'Claim',
            'subject':'ecl:STATE-AAA','predicate':'ecl:tracks','object':'ecl:PROJECT-X','status':'accepted',
            'evidenceFor':['ecl:EVIDENCE-A'],'provenance':['fixture']
        })

    def interval(self):
        return {'low':0.2,'central':0.3,'high':0.4,'rationale':'fixture bound','evidence_refs':['ecl:EVIDENCE-A']}

    def complete_assessment(self):
        anchors = {v:{'min':0,'max':1,'rationale':'fixture anchors'} for v in MODULE.CORE_VARS}
        variables = {v:self.interval() for v in MODULE.CORE_VARS + MODULE.ADVANCED_VARS}
        return {
            'assessment_id':'ECL-EX-AAA-001','actor_id':'STATE-AAA','model':'test','entity':'Alpha','object':'Exact alpha project',
            'scoring_status':'scorable','normalization':{'method':'bounded rubric','rubric':'fixture','anchors':anchors,'provenance':['ecl:EVIDENCE-A']},
            'profiles':['exergism/profiles/test.json'],'sensitivity_review':{'performed':True,'notes':'interval/profile sensitivity checked'},
            'variables':variables,
            'advanced_evidence_independence':{v:{'independent_from_harm_inference':True,'rationale':'independent fixture basis','evidence_refs':['ecl:EVIDENCE-A']} for v in ('D_a','I','Lz','G')},
            'adversarial_review':{'status':'reviewed','determination':'uphold exact scope','reviewed_at':'2026-08-17','reviewer_independence':'independent-second-pass','provenance':['fixture-review']},
            'criterion_relevance':['ECL5_1'],'attribution':['direct project evidence'],'counter_institutions':['none material to fixture'],
            'governance_scope_binding':{'scope':'Exact alpha project','provenance':['ecl:EVIDENCE-A']},
            'exclusions':['outside project'],'disagreement_notes':['none'],
            'temporal_applicability':{'status':'not-applicable','reason':'single bounded event; no temporal conclusion used','provenance':['ecl:EVIDENCE-A']}
        }

    def test_complete_is_derived_not_declared(self):
        self.state(); self.claim(); self.write_json('exergism/assessments/AAA.json', self.complete_assessment())
        data = MODULE.report(self.root, today=MODULE.dt.date(2026,8,18))
        row = data['actors'][0]
        self.assertEqual(row['coverage']['formal_core']['status'], 'complete')
        self.assertEqual(row['coverage']['formal_canonical']['status'], 'complete')
        self.assertEqual(row['coverage']['temporal']['status'], 'not-applicable')
        self.assertEqual(row['coverage']['governance_ready']['status'], 'complete')
        self.assertEqual(data['material_governance_dependencies']['unknown'], 0)
        self.assertEqual(data['material_governance_dependencies']['ready'], 1)

    def test_material_actor_without_assessment_is_explicitly_blocked_not_unknown(self):
        self.state(); self.claim()
        data = MODULE.report(self.root, today=MODULE.dt.date(2026,8,18))
        row = data['actors'][0]
        self.assertEqual(row['coverage']['formal_core']['status'], 'blocked')
        self.assertEqual(data['material_governance_dependencies']['blocked'], 1)
        self.assertEqual(data['material_governance_dependencies']['unknown'], 0)

    def test_manual_complete_disposition_is_rejected(self):
        self.state(); self.claim()
        item = self.complete_assessment(); item['coverage_disposition']={'status':'complete','reason':'launder it','provenance':['x']}
        self.write_json('exergism/assessments/AAA.json', item)
        data = MODULE.report(self.root)
        self.assertTrue(any('may never assert complete' in e for e in data['integrity_errors']))

    def test_partof_does_not_propagate_materiality(self):
        self.state(); self.claim()
        self.write_json('knowledge/entities/AGENCY-BBB.json', {
            '@context':'../../ontology/ecl-context.jsonld','iri':'ecl:AGENCY-BBB','id':'AGENCY-BBB','type':'Agency','name':'Beta Agency',
            'dossier':'../../dossiers/agencies/BBB.md','partOf':['ecl:STATE-AAA']
        })
        (self.root/'dossiers/agencies/BBB.md').write_text('---\nid: ECL-AGENCY-BBB\nentity: Beta Agency\n---\n# Beta\n')
        data = MODULE.report(self.root)
        beta = next(r for r in data['actors'] if r['actor_id']=='AGENCY-BBB')
        self.assertEqual(beta['priority'], 'P3')
        self.assertFalse(beta['material_reasons'])

    def test_direct_project_freeze_is_known_but_blocked_without_exact_assessment_binding(self):
        self.state(outcome='N')
        self.write_json('knowledge/entities/PROJECT-MITIGA-DETENTION.json', {
            '@context':'../../ontology/ecl-context.jsonld','iri':'ecl:PROJECT-MITIGA-DETENTION','id':'PROJECT-MITIGA-DETENTION',
            'type':'Project','name':'Mitiga detention','dossier':'../../dossiers/projects/MITIGA.md'
        })
        (self.root/'dossiers/projects/MITIGA.md').write_text('# Mitiga\n')
        (self.root/'registry/schedule-project-freezes.yml').write_text(
            'projects:\n  - id: MITIGA-DETENTION-APPARATUS\n    outcome: R\n', encoding='utf-8')
        data = MODULE.report(self.root)
        material = data['material_governance_dependencies']
        self.assertEqual(material['unknown'], 0)
        dep = next(d for d in material['dependencies'] if d['target']=='PROJECT-MITIGA-DETENTION')
        self.assertEqual(dep['status'], 'blocked')

    def test_scope_mismatch_blocks_governance_ready(self):
        self.state(); self.claim(); item=self.complete_assessment()
        item['governance_scope_binding']['scope']='Different scope'
        self.write_json('exergism/assessments/AAA.json', item)
        data = MODULE.report(self.root, today=MODULE.dt.date(2026,8,18))
        row=data['actors'][0]
        self.assertEqual(row['coverage']['formal_core']['status'], 'complete')
        self.assertEqual(row['coverage']['governance_ready']['status'], 'blocked')
        self.assertTrue(any('governance_scope_binding' in x for x in row['coverage']['governance_ready']['missing']))

    def test_score_to_tier_laundering_is_integrity_error(self):
        self.state(); self.claim(); item=self.complete_assessment(); item['tier']='R'
        self.write_json('exergism/assessments/AAA.json', item)
        data = MODULE.report(self.root)
        self.assertTrue(any('forbidden score/governance fields' in e for e in data['integrity_errors']))

if __name__ == '__main__':
    unittest.main()
