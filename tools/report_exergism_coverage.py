#!/usr/bin/env python3
"""Deterministic actor/scope Formal Exergism coverage audit for ECL."""
from __future__ import annotations
import argparse, datetime as dt, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import yaml

TOOLS=Path(__file__).resolve().parent
if str(TOOLS) not in sys.path: sys.path.insert(0,str(TOOLS))
try: import exergic_analysis as canonical_exergism
except ImportError: canonical_exergism=None

ACTORS={"State","Agency","Organization","Institution","Person"}
CORE=("P","A","V_ep","L","O","U","C","S","R","Ecol","D_p")
ADV=("D_a","I","Lz","G","Rj")
CORE_VARS=CORE
ADVANCED_VARS=ADV
INTENT_VARS=("D_a","I","Lz","G")
STATUSES={"complete","incomplete","not-applicable","insufficient-evidence","blocked","disputed"}
ACTIVE={"candidate","accepted","disputed"}
ATTR={"ecl:controls","ecl:participatesIn","ecl:operates","ecl:deploys","ecl:materiallyBenefits"}

class CoverageError(ValueError): pass

def jload(p:Path):
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise CoverageError(f"{p}: expected object")
    return v

def yload(p:Path):
    v=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(v,dict): raise CoverageError(f"{p}: expected mapping")
    return v

def iri(v:str): return "urn:ecl:"+v[4:] if v.startswith("ecl:") else v
def eid(v:str): return "urn:ecl:"+v
def status(s,reason,missing=(),prov=()):
    assert s in STATUSES
    return {"status":s,"reason":reason,"missing":sorted(set(filter(None,map(str,missing)))),"provenance":sorted(set(filter(None,map(str,prov))))}

def fm(p:Path):
    if not p.exists(): return {}
    t=p.read_text(encoding="utf-8")
    if not t.startswith("---\n"): return {}
    n=t.find("\n---\n",4)
    if n<0:return {}
    v=yaml.safe_load(t[4:n]) or {}
    return v if isinstance(v,dict) else {}

def resolve(src:Path,raw:str): return (src.parent/Path(raw)).resolve()
def norm(v:str): return re.sub(r"[^a-z0-9]+","",v.casefold())

def interval(v):
    if not isinstance(v,dict): return False
    try: xs=[float(v[k]) for k in ("low","central","high")]
    except (KeyError,TypeError,ValueError): return False
    return 0<=xs[0]<=xs[1]<=xs[2]<=1 and bool(str(v.get("rationale","")).strip()) and bool(v.get("evidence_refs"))

def ref_ok(root:Path, raw):
    if not isinstance(raw,str) or not raw.strip(): return False
    ref=raw.strip()
    if ref.startswith("ecl:EVIDENCE-"):
        return (root/"knowledge/evidence"/(ref[4:]+".json")).exists()
    if ref.startswith("urn:ecl:EVIDENCE-"):
        return (root/"knowledge/evidence"/(ref[8:]+".json")).exists()
    base=ref.split("#",1)[0]
    if base.startswith(("http://","https://")): return True
    return (root/base).exists()

def interval_refs_ok(root:Path, v):
    return isinstance(v,dict) and all(ref_ok(root,r) for r in (v.get("evidence_refs") or []))

def disposition(a):
    if a.get("scoring_status")=="insufficient_evidence": return "insufficient-evidence"
    if a.get("scoring_status")=="not_applicable": return "not-applicable"
    d=a.get("coverage_disposition")
    if d is None:return None
    if not isinstance(d,dict): raise CoverageError("coverage_disposition must be object")
    s=d.get("status")
    if s=="complete": raise CoverageError("coverage_disposition may never assert complete; completeness is derived")
    if s not in {"blocked","disputed","insufficient-evidence","not-applicable"}: raise CoverageError(f"invalid coverage disposition {s}")
    if not str(d.get("reason","")).strip() or not d.get("provenance"): raise CoverageError("coverage_disposition requires reason and provenance")
    return s

def core(a,root):
    d=disposition(a)
    if d:return status(d,str(a.get("reason") or a.get("coverage_disposition",{}).get("reason") or d),prov=[a.get("assessment_id")])
    if a.get("scoring_status")!="scorable":return status("incomplete","assessment is not scorable",["scoring_status=scorable"])
    miss=[]
    for k in ("actor_id","object"):
        if not str(a.get(k,"")).strip():miss.append(k)
    n=a.get("normalization")
    if not isinstance(n,dict):miss.append("normalization")
    else:
        for k in ("method","rubric"):
            if not str(n.get(k,"")).strip():miss.append(f"normalization.{k}")
        prov=n.get("provenance") or []
        if not prov:miss.append("normalization.provenance")
        else:miss += [f"normalization.provenance:{r}" for r in prov if not ref_ok(root,r)]
        an=n.get("anchors")
        if not isinstance(an,dict):miss.append("normalization.anchors")
        else:
            for v in CORE:
                x=an.get(v)
                if not isinstance(x,dict) or "min" not in x or "max" not in x or not str(x.get("rationale","")).strip():miss.append(f"normalization.anchors.{v}")
    ps=a.get("profiles")
    if not isinstance(ps,list) or not ps:miss.append("profiles")
    else:
        for p in ps:
            if not isinstance(p,str) or not (root/p).exists():miss.append(f"profile:{p}")
    sr=a.get("sensitivity_review")
    if not isinstance(sr,dict) or sr.get("performed") is not True or not str(sr.get("notes","")).strip():miss.append("sensitivity_review")
    vs=a.get("variables") if isinstance(a.get("variables"),dict) else {}
    for v in CORE:
        x=vs.get(v)
        if not interval(x):miss.append(f"variables.{v}")
        elif not interval_refs_ok(root,x):miss.append(f"variables.{v}.evidence_refs")
    if not miss:
        if canonical_exergism is None:miss.append("tools/exergic_analysis.py")
        else:
            for p in ps:
                try:
                    r=canonical_exergism.calculate(a,jload(root/p));keys=set((r.get("scores") or {}).keys())
                    miss += [f"derived:{k}" for k in sorted({"Ex_b","Pen","Ex_r","E_i","X_h","B_0"}-keys)]
                except Exception as e:miss.append(f"calculation:{p}:{e}")
    return status("incomplete","formal-core invariants not demonstrated",miss) if miss else status("complete","core inputs and canonical metrics mechanically demonstrated",prov=[a.get("assessment_id")])

def canonical(a,c,root):
    if c["status"] in {"blocked","disputed","insufficient-evidence","not-applicable"}:return dict(c)
    if c["status"]!="complete":return status("incomplete","canonical requires complete core",["formal-core-complete"])
    vs=a.get("variables",{});miss=[]
    for v in ADV:
        x=vs.get(v)
        if not interval(x):miss.append(f"variables.{v}")
        elif not interval_refs_ok(root,x):miss.append(f"variables.{v}.evidence_refs")
    ind=a.get("advanced_evidence_independence")
    if not isinstance(ind,dict):miss.append("advanced_evidence_independence")
    else:
        for v in INTENT_VARS:
            x=ind.get(v)
            if not isinstance(x,dict) or x.get("independent_from_harm_inference") is not True or not str(x.get("rationale","")).strip() or not x.get("evidence_refs"):
                miss.append(f"advanced_evidence_independence.{v}")
            elif not all(ref_ok(root,r) for r in x.get("evidence_refs",[])):
                miss.append(f"advanced_evidence_independence.{v}.evidence_refs")
    if not miss and canonical_exergism:
        for p in a.get("profiles",[]):
            try:
                r=canonical_exergism.calculate(a,jload(root/p))
                miss += [f"derived:{k}" for k in sorted({"P_atr","E_i_adj","M_f"}-set((r.get("scores") or {}).keys()))]
            except Exception as e:miss.append(f"calculation:{p}:{e}")
    return status("incomplete","advanced variables/metrics or independent imputability evidence not demonstrated",miss) if miss else status("complete","canonical static layer mechanically demonstrated",prov=[a.get("assessment_id")])

def temporal(a,c,root):
    ap=a.get("temporal_applicability")
    if isinstance(ap,dict) and ap.get("status")=="not-applicable":
        prov=ap.get("provenance") or []
        if str(ap.get("reason","")).strip() and prov and all(ref_ok(root,r) for r in prov):return status("not-applicable",ap["reason"],prov=prov)
        return status("incomplete","temporal N/A lacks resolvable reason/provenance",["temporal_applicability"])
    if c["status"] in {"blocked","disputed","insufficient-evidence","not-applicable"}:return dict(c)
    t=a.get("temporal")
    if not isinstance(t,dict):return status("incomplete","temporal applicability unresolved",["temporal or explicit N/A"])
    miss=[]
    if isinstance(t.get("lambda"),bool) or not isinstance(t.get("lambda"),(int,float)) or t["lambda"]<0:miss.append("temporal.lambda")
    snaps=t.get("snapshots")
    if not isinstance(snaps,list) or not snaps:miss.append("temporal.snapshots")
    else:
        for i,s in enumerate(snaps):
            if not isinstance(s,dict):miss.append(f"snapshots[{i}]");continue
            for k in ("t","gamma","delta","irreversibility"):
                if isinstance(s.get(k),bool) or not isinstance(s.get(k),(int,float)):miss.append(f"snapshots[{i}].{k}")
            vs=s.get("variables") if isinstance(s.get("variables"),dict) else {}
            for v in CORE+("Rj",):
                x=vs.get(v)
                if not interval(x):miss.append(f"snapshots[{i}].variables.{v}")
                elif not interval_refs_ok(root,x):miss.append(f"snapshots[{i}].variables.{v}.evidence_refs")
    if not miss and canonical_exergism:
        try:
            r=canonical_exergism.calculate(a,jload(root/a["profiles"][0]))
            miss += [f"derived:{k}" for k in sorted({"B_acc","D_acc","N_t"}-set((r.get("temporal") or {}).keys()))]
        except Exception as e:miss.append(f"temporal-calculation:{e}")
    return status("incomplete","temporal invariants not demonstrated",miss) if miss else status("complete","temporal inputs and B_acc/D_acc/N_t mechanically demonstrated")

def advreview(a):
    r=a.get("adversarial_review");miss=[]
    if not isinstance(r,dict):miss=["adversarial_review"]
    else:
        if r.get("status")!="reviewed":miss.append("adversarial_review.status")
        for k in ("determination","reviewed_at","reviewer_independence"):
            if not str(r.get(k,"")).strip():miss.append(f"adversarial_review.{k}")
        if not r.get("provenance"):miss.append("adversarial_review.provenance")
    return status("incomplete","structured adversarial review incomplete",miss) if miss else status("complete","structured adversarial review recorded",prov=r["provenance"])

def entities(root):
    out={};errs=[]
    for p in sorted((root/"knowledge/entities").glob("*.json")):
        try:a=jload(p)
        except Exception as e:errs.append(f"{p.relative_to(root)}: {e}");continue
        if a.get("type") not in ACTORS:continue
        sid=a.get("id")
        if not isinstance(sid,str) or sid in out:errs.append(f"invalid/duplicate actor id in {p.relative_to(root)}");continue
        a["_path"]=p;dp=resolve(p,a["dossier"]) if isinstance(a.get("dossier"),str) else None;a["_dossier"]=dp;a["_fm"]=fm(dp) if dp else {};out[sid]=a
    return out,errs

def ident(a):
    miss=[];sid=a.get("id")
    if iri(str(a.get("iri","")))!=eid(str(sid)):miss.append("iri/id")
    for k in ("type","name","dossier"):
        if not str(a.get(k,"")).strip():miss.append(k)
    if not isinstance(a.get("_dossier"),Path) or not a["_dossier"].exists():miss.append("dossier-resolves")
    if a.get("type")=="State":
        if sid!=f"STATE-{a.get('iso3')}":miss.append("iso3/id")
        for k in ("publicReviewIssue","lastSubstantiveReview","reviewClass"):
            if not a.get(k):miss.append(k)
    return status("incomplete","identity invariants incomplete",miss) if miss else status("complete","canonical identity resolves")

def claims(root):
    es={};cs=[];errs=[]
    for p in sorted((root/"knowledge/evidence").glob("*.json")):
        try:e=jload(p);es[iri(str(e.get("iri","")))]=e
        except Exception as x:errs.append(f"{p.relative_to(root)}: {x}")
    for p in sorted((root/"knowledge/claims").glob("*.json")):
        try:c=jload(p);c["_path"]=p;cs.append(c)
        except Exception as x:errs.append(f"{p.relative_to(root)}: {x}")
    return cs,es,errs

def evdim(sid,cs,es,material):
    ds=[c for c in cs if iri(str(c.get("subject","")))==eid(sid) and c.get("status") in ACTIVE]
    if not ds:return status("incomplete","material actor lacks active direct Claim/Evidence",["active claim/evidence"]) if material else status("not-applicable","no active direct Claim")
    miss=[]
    for c in ds:
        for k in ("id","iri","subject","predicate","status"):
            if not str(c.get(k,"")).strip():miss.append(f"{c.get('id','claim')}:{k}")
        refs=list(c.get("evidenceFor") or [])+list(c.get("evidenceAgainst") or [])
        if c.get("status") in ACTIVE and not refs:miss.append(f"{c.get('id')}:evidence")
        miss += [f"{c.get('id')}:unresolved:{r}" for r in refs if iri(str(r)) not in es]
        if not c.get("provenance"):miss.append(f"{c.get('id')}:provenance")
    return status("incomplete","Claim/Evidence normalization incomplete",miss) if miss else status("complete","all active direct Claims resolve evidence/provenance",prov=[c.get("id") for c in ds])

def assessments(root,actors):
    by=defaultdict(list);allv=[];errs=[];seen=set()
    for p in sorted((root/"exergism/assessments").glob("*.json")):
        try:a=jload(p);disposition(a)
        except Exception as e:errs.append(f"{p.relative_to(root)}: {e}");continue
        aid=a.get("assessment_id");sid=a.get("actor_id");a["_path"]=p;allv.append(a)
        if not isinstance(aid,str) or aid in seen:errs.append(f"duplicate/missing assessment_id in {p.relative_to(root)}")
        else:seen.add(aid)
        if sid not in actors:errs.append(f"{p.relative_to(root)}: actor_id does not resolve: {sid}")
        else:by[sid].append(a)
    return by,allv,errs

def name_index(actors):
    ix=defaultdict(set)
    for sid,a in actors.items():
        for v in [a.get("name"),*(a.get("aliases") or [])]:
            if isinstance(v,str):ix[norm(v)].add(sid)
    return ix

def materiality(root,actors,cs):
    rs=defaultdict(set);sc=[];unknown=[]
    for sid,a in actors.items():
        o=a["_fm"].get("provisional_outcome")
        if o in {"R","S"}:rs[sid].add(f"dossier:{o}");sc.append({"kind":"actor-dossier","target":sid,"outcome":o,"source":str(a["_dossier"].relative_to(root))})
    reg=root/"registry";ix=name_index(actors)
    p=reg/"schedule-organization-freezes.yml"
    if p.exists():
        for r in yload(p).get("organizations",[]) or []:
            sid=f"ORG-{r.get('id')}"
            if sid in actors:rs[sid].add("schedule-organization");sc.append({"kind":"schedule-organization","target":sid,"source":str(p.relative_to(root))})
            elif r.get("id"):unknown.append(f"unresolved schedule organization {r.get('id')}")
            for n in r.get("schedule_entities",[]) or []:
                z=norm(str(n));m=set()
                for k,ids in ix.items():
                    if k==z or (len(k)>=6 and k in z):m|=ids
                if len(m)==1:s=next(iter(m));rs[s].add("schedule-exact-entity");sc.append({"kind":"schedule-exact-entity","target":s,"source":str(p.relative_to(root))})
                else:unknown.append(f"schedule entity maps to {sorted(m)}: {n}")
    p=reg/"schedule-armed-organization-freezes.yml";amap={"RAPID-SUPPORT-FORCES":"ORG-RSF","SUDANESE-ARMED-FORCES":"ORG-SAF","IZZ-AL-DIN-AL-QASSAM-BRIGADES":"ORG-IZZ-AL-DIN-AL-QASSAM"}
    if p.exists():
        for r in yload(p).get("organizations",[]) or []:
            raw=str(r.get("id"));sid=amap.get(raw,f"ORG-{raw}")
            if sid in actors:rs[sid].add("schedule-armed-organization");sc.append({"kind":"schedule-armed-organization","target":sid,"source":str(p.relative_to(root))})
            else:unknown.append(f"unresolved armed organization {raw}")
    p=reg/"schedule-project-freezes.yml";pmap={"MITIGA-DETENTION-APPARATUS":"PROJECT-MITIGA-DETENTION"}
    if p.exists():
        for r in yload(p).get("projects",[]) or []:
            raw=str(r.get("id"));sid=pmap.get(raw,raw if raw.startswith("PROJECT-") else f"PROJECT-{raw}")
            if (root/"knowledge/entities"/f"{sid}.json").exists():sc.append({"kind":"schedule-project","target":sid,"source":str(p.relative_to(root))})
            else:unknown.append(f"unresolved schedule project {raw}")
    targets={x["target"] for x in sc}
    for c in cs:
        if c.get("status") not in {"accepted","disputed"} or c.get("predicate") not in ATTR:continue
        ob=iri(str(c.get("object",""))).removeprefix("urn:ecl:");su=iri(str(c.get("subject",""))).removeprefix("urn:ecl:")
        if ob in targets and su in actors and su not in rs:rs[su].add("attribution-review-dependency")
    return rs,sorted(sc,key=lambda x:(x["kind"],x["target"])),sorted(set(unknown))

def priority(sid,a,rs,cs,by):
    x=rs.get(sid,set())
    if any(v!="attribution-review-dependency" for v in x):return "P0"
    if "attribution-review-dependency" in x:return "P2"
    direct=any(iri(str(c.get("subject","")))==eid(sid) and c.get("status") in {"accepted","disputed"} and (c.get("affectedCriterion") or c.get("affectedCriteria") or c.get("affectedVariable") or c.get("affectedVariables")) for c in cs)
    return "P1" if by.get(sid) or direct or a["_fm"].get("provisional_outcome")=="U" else "P3"

def aggregate(av,root,required):
    if not av:
        s="blocked" if required else "not-applicable";r="actor requiring formal review has no assessment" if required else "formal analysis not yet required";d=status(s,r,["formal assessment"] if required else [])
        return d,dict(d),dict(d),dict(d),[]
    rows=[]
    for a in av:
        c=core(a,root);k=canonical(a,c,root);t=temporal(a,c,root);v=advreview(a);rows.append({"assessment_id":a.get("assessment_id"),"object":a.get("object"),"scoring_status":a.get("scoring_status"),"core":c,"canonical":k,"temporal":t,"adversarial":v})
    def agg(k):
        ss=[r[k]["status"] for r in rows]
        if all(x=="complete" for x in ss):return status("complete",f"all {len(rows)} assessments complete",prov=[r["assessment_id"] for r in rows])
        for x in ("disputed","blocked","insufficient-evidence"):
            if x in ss:return status(x,f"at least one assessment is {x}",[r["assessment_id"] for r in rows if r[k]["status"]==x])
        if all(x=="not-applicable" for x in ss):return status("not-applicable","all assessments explicitly N/A")
        return status("incomplete",f"not all assessments satisfy {k}",[r["assessment_id"] for r in rows if r[k]["status"]!="complete"])
    return agg("core"),agg("canonical"),agg("temporal"),agg("adversarial"),rows

def govready(a,required,i,e,c,v,av,today):
    if not required:return status("not-applicable","actor is not a direct material dependency")
    miss=[]
    for n,x in (("identity",i),("evidence",e),("formal-core",c),("adversarial",v)):
        if x["status"]!="complete":miss.append(f"{n}:{x['status']}")
    f=a["_fm"];expected=str(f.get("provisional_scope","")).strip();root=Path(a["_path"]).parents[2]
    for z in av:
        for k in ("criterion_relevance","attribution","counter_institutions","exclusions","disagreement_notes"):
            if not z.get(k):miss.append(f"{z.get('assessment_id')}:{k}")
        b=z.get("governance_scope_binding")
        if not isinstance(b,dict) or str(b.get("scope","")).strip()!=expected or not b.get("provenance"):
            miss.append(f"{z.get('assessment_id')}:governance_scope_binding")
        elif not all(ref_ok(root,r) for r in b.get("provenance",[])):
            miss.append(f"{z.get('assessment_id')}:governance_scope_binding.provenance")
    for k in ("provisional_scope","evidence_cutoff","last_reviewed"):
        if not f.get(k):miss.append(f"dossier.{k}")
    rd=a.get("reviewDue")
    if isinstance(rd,str):
        try:
            if dt.date.fromisoformat(rd)<today:miss.append("review-clock:stale")
        except ValueError:miss.append("review-clock:invalid")
    return status("blocked","material dependency not governance-ready",miss) if miss else status("complete","material dependency passes formal/evidence/review/scope-binding gates")

def report(root:Path,today=None):
    root=root.resolve();today=today or dt.date.today();actors,errs=entities(root);cs,es,x=claims(root);errs+=x;by,alls,x=assessments(root,actors);errs+=x;rs,sc,unknown=materiality(root,actors,cs);rows=[]
    for sid in sorted(actors):
        a=actors[sid];pri=priority(sid,a,rs,cs,by);req=any(v!="attribution-review-dependency" for v in rs.get(sid,set()));formal_req=pri!="P3";i=ident(a);e=evdim(sid,cs,es,req);c,k,t,v,ar=aggregate(by.get(sid,[]),root,formal_req);g=govready(a,req,i,e,c,v,by.get(sid,[]),today)
        rows.append({"actor_id":sid,"name":a.get("name"),"type":a.get("type"),"priority":pri,"dossier":str(a["_dossier"].relative_to(root)) if a["_dossier"] and a["_dossier"].exists() else a.get("dossier"),"provisional_outcome":a["_fm"].get("provisional_outcome"),"material_reasons":sorted(rs.get(sid,set())),"coverage":{"identity":i,"evidence_normalized":e,"formal_core":c,"formal_canonical":k,"temporal":t,"adversarial_reviewed":v,"governance_ready":g},"assessments":ar})
    for a in alls:
        bad={"tier","tier_mapping","derived_outcome","score_outcome","score_to_tier"}&set(a)
        if bad:errs.append(f"{a['_path'].relative_to(root)}: forbidden score/governance fields {sorted(bad)}")
    mr=[r for r in rows if any(v!="attribution-review-dependency" for v in r["material_reasons"])]
    deps=[]
    for r in mr:
        s=r["coverage"]["formal_core"]["status"];ds=s if s in {"insufficient-evidence","disputed"} else ("ready" if r["coverage"]["governance_ready"]["status"]=="complete" else "blocked");deps.append({"kind":"actor","target":r["actor_id"],"status":ds})
    for target in sorted({x["target"] for x in sc if x["kind"]=="schedule-project"}):
        ma=[a for a in alls if target in (a.get("target_ids") or [])];ss=[core(a,root)["status"] for a in ma]
        ds="disputed" if "disputed" in ss else "insufficient-evidence" if "insufficient-evidence" in ss else "blocked";deps.append({"kind":"scope","target":target,"status":ds,"reason":"exact project binding required"})
    cc={k:Counter(r["coverage"][k]["status"] for r in rows) for k in ("identity","evidence_normalized","formal_core","formal_canonical","temporal","adversarial_reviewed","governance_ready")};dc=Counter(d["status"] for d in deps)
    return {"schema_version":1,"as_of":today.isoformat(),"actors_total":len(rows),"actor_classes":dict(sorted(Counter(r["type"] for r in rows).items())),"tracked_projects_total":len(list((root/"knowledge/entities").glob("PROJECT-*.json"))),"assessments_total":len(alls),"claims_total":len(cs),"evidence_items_total":len(es),"priorities":{k:sum(r["priority"]==k for r in rows) for k in ("P0","P1","P2","P3")},"coverage_counts":{k:dict(sorted(v.items())) for k,v in cc.items()},"material_governance_dependencies":{"actor_count":len(mr),"scope_count":len(sc),"dependency_count":len(deps),"ready":dc.get("ready",0),"insufficient_evidence":dc.get("insufficient-evidence",0),"blocked":dc.get("blocked",0),"disputed":dc.get("disputed",0),"unknown":len(unknown),"unknown_details":unknown,"dependencies":sorted(deps,key=lambda x:(x["kind"],x["target"]))},"integrity_errors":sorted(set(errs)),"material_scopes":sc,"actors":rows}

def text(d):
    c=d["coverage_counts"];n=lambda k,s="complete":c.get(k,{}).get(s,0);m=d["material_governance_dependencies"]
    lines=[f"Actors total:                     {d['actors_total']}","Actor classes:                    "+", ".join(f"{k}={v}" for k,v in d["actor_classes"].items()),f"Tracked projects (non-Actor):     {d['tracked_projects_total']}",f"Assessments:                      {d['assessments_total']}",f"Claims / Evidence items:          {d['claims_total']} / {d['evidence_items_total']}",f"Identity complete:                {n('identity')}",f"Evidence normalized:              {n('evidence_normalized')}",f"Formal core complete:             {n('formal_core')}",f"Formal canonical complete:        {n('formal_canonical')}",f"Temporal complete:                {n('temporal')}",f"Temporal N/A:                     {n('temporal','not-applicable')}",f"Adversarial reviewed:             {n('adversarial_reviewed')}",f"Governance ready:                 {n('governance_ready')}","Priorities:                       "+", ".join(f"{k}={d['priorities'][k]}" for k in ("P0","P1","P2","P3")),"","Material governance dependencies:",f"  Actors:                         {m['actor_count']}",f"  Scopes observed:                {m['scope_count']}",f"  Unique dependencies:            {m['dependency_count']}",f"  Ready:                          {m['ready']}",f"  Insufficient evidence:          {m['insufficient_evidence']}",f"  Blocked:                        {m['blocked']}",f"  Disputed:                       {m['disputed']}",f"  UNKNOWN:                        {m['unknown']}",f"Integrity errors:                 {len(d['integrity_errors'])}"]
    if m["unknown_details"]:lines += ["","UNKNOWN material dependencies:"]+[f"  - {x}" for x in m["unknown_details"]]
    if d["integrity_errors"]:lines += ["","Integrity errors:"]+[f"  - {x}" for x in d["integrity_errors"]]
    return "\n".join(lines)+"\n"

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument("--json",dest="jp",type=Path);p.add_argument("--matrix",type=Path);p.add_argument("--fail-on-unknown-material",action="store_true");p.add_argument("--release-1-0-gate",action="store_true");p.add_argument("--as-of");a=p.parse_args(argv);d=report(a.root,dt.date.fromisoformat(a.as_of) if a.as_of else None);sys.stdout.write(text(d))
    for path,obj in ((a.jp,d),(a.matrix,d["actors"])):
        if path:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    bad=bool(d["integrity_errors"]) or (a.fail_on_unknown_material and d["material_governance_dependencies"]["unknown"])
    if a.release_1_0_gate:
        m=d["material_governance_dependencies"];bad=bad or any(m[k] for k in ("unknown","blocked","insufficient_evidence","disputed"))
    return 1 if bad else 0
if __name__=="__main__":raise SystemExit(main())
