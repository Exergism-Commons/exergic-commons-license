#!/usr/bin/env python3
"""Fail closed on graph-native GovernanceDecision/ScheduleEntry formal-coverage links."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

TOOLS=Path(__file__).resolve().parent
if str(TOOLS) not in sys.path: sys.path.insert(0,str(TOOLS))
import report_exergism_coverage as coverage

MATERIAL_OUTCOMES={"R","S","OutcomeR","OutcomeS"}


def local_id(value):
    if isinstance(value,dict): value=value.get("@id") or value.get("id")
    if not isinstance(value,str): return None
    if value.startswith("urn:ecl:"): return value[8:]
    if value.startswith("ecl:"): return value[4:]
    return value


def refs(value):
    if value is None:return []
    return value if isinstance(value,list) else [value]


def records(root:Path):
    decisions={};schedules=[];errors=[]
    for path in sorted((root/"knowledge").rglob("*.json")):
        if "generated" in path.parts:continue
        try:data=json.loads(path.read_text(encoding="utf-8"))
        except Exception:continue
        if not isinstance(data,dict):continue
        typ=local_id(data.get("type") or data.get("@type"))
        if typ not in {"GovernanceDecision","ScheduleEntry"}:continue
        rid=local_id(data.get("id") or data.get("iri") or data.get("@id"))
        if not rid:
            errors.append(f"{path.relative_to(root)}: {typ} lacks stable id")
            continue
        data["_path"]=path
        if typ=="GovernanceDecision":
            if rid in decisions:errors.append(f"duplicate GovernanceDecision id {rid}")
            decisions[rid]=data
        else:schedules.append(data)
    return decisions,schedules,errors


def assess_index(root:Path):
    out={};errors=[]
    for path in sorted((root/"exergism/assessments").glob("*.json")):
        try:data=json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
            continue
        aid=data.get("assessment_id")
        if not isinstance(aid,str) or aid in out:errors.append(f"duplicate/missing assessment_id in {path.relative_to(root)}")
        else:out[aid]=data
    return out,errors


def actor_governance_ready(root,actor_id):
    actors,errors=coverage.entities(root)
    if errors:return False,"; ".join(errors)
    actor=actors.get(actor_id)
    if not actor:return False,f"subject actor does not resolve: {actor_id}"
    claims,evidence,claim_errors=coverage.claims(root)
    if claim_errors:return False,"; ".join(claim_errors)
    by,_,assessment_errors=coverage.assessments(root,actors)
    if assessment_errors:return False,"; ".join(assessment_errors)
    i=coverage.ident(actor)
    e=coverage.evdim(actor_id,claims,evidence,True)
    c,_,_,v,_=coverage.aggregate(by.get(actor_id,[]),root,True)
    g=coverage.govready(actor,True,i,e,c,v,by.get(actor_id,[]),coverage.dt.date.today())
    return g["status"]=="complete",", ".join(g["missing"]) or g["reason"]


def project_assessment_ready(root,assessment,target):
    if target not in (assessment.get("target_ids") or []):return False,"assessment does not bind exact target_id"
    c=coverage.core(assessment,root)
    if c["status"]!="complete":return False,f"formal-core:{c['status']}"
    v=coverage.advreview(assessment)
    if v["status"]!="complete":return False,f"adversarial:{v['status']}"
    missing=[k for k in ("criterion_relevance","attribution","counter_institutions","exclusions","disagreement_notes") if not assessment.get(k)]
    return (not missing,", ".join(missing) if missing else "exact project assessment ready")


def check(root:Path):
    root=root.resolve();decisions,schedules,errors=records(root);assessments,aerrors=assess_index(root);errors+=aerrors
    for did,d in sorted(decisions.items()):
        outcome=local_id(d.get("outcome"))
        if outcome not in MATERIAL_OUTCOMES:continue
        subject=local_id(d.get("subject"))
        if not subject:
            errors.append(f"{did}: material GovernanceDecision lacks subject")
            continue
        arefs=[local_id(x) for x in refs(d.get("basedOnAssessment"))]
        arefs=[x for x in arefs if x]
        if not arefs:
            errors.append(f"{did}: material GovernanceDecision lacks basedOnAssessment")
            continue
        linked=[]
        for aid in arefs:
            a=assessments.get(aid)
            if not a:errors.append(f"{did}: basedOnAssessment does not resolve: {aid}")
            else:linked.append(a)
        if not linked:continue
        if subject.startswith(("STATE-","AGENCY-","ORG-","PERSON-","INST-")):
            if any(a.get("actor_id")!=subject for a in linked):errors.append(f"{did}: linked assessment actor_id does not match subject {subject}")
            ok,why=actor_governance_ready(root,subject)
            if not ok:errors.append(f"{did}: subject is not governance-ready: {why}")
            for a in linked:
                if coverage.core(a,root)["status"]!="complete":errors.append(f"{did}: linked assessment {a.get('assessment_id')} is not formal-core-complete")
        elif subject.startswith(("PROJECT-","DEPLOYMENT-")):
            for a in linked:
                ok,why=project_assessment_ready(root,a,subject)
                if not ok:errors.append(f"{did}: linked assessment {a.get('assessment_id')} not ready for {subject}: {why}")
        else:errors.append(f"{did}: material subject has unsupported/unresolved id {subject}")
    for s in schedules:
        sid=local_id(s.get("id") or s.get("iri") or s.get("@id"))
        drefs=[local_id(x) for x in refs(s.get("basedOnDecision"))]
        drefs=[x for x in drefs if x]
        if not drefs:errors.append(f"{sid}: ScheduleEntry lacks basedOnDecision")
        for did in drefs:
            if did not in decisions:errors.append(f"{sid}: basedOnDecision does not resolve: {did}")
    return sorted(set(errors))


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]);args=p.parse_args(argv)
    errors=check(args.root)
    if errors:
        print("Graph-native formal coverage violations:")
        for error in errors:print(f"  - {error}")
        return 1
    print("Graph-native GovernanceDecision/ScheduleEntry formal coverage: PASS")
    return 0

if __name__=="__main__":raise SystemExit(main())
