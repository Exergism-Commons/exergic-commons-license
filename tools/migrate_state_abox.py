#!/usr/bin/env python3
"""Migrate canonical State dossiers into deterministic JSON-LD identity records.

The dossier remains the governance synthesis. This tool validates but never
materializes provisional_outcome/scope/tier/restriction status. Generated fields
are protected by a hash manifest; all other fields are preserved as curated ABox.
"""
from __future__ import annotations
import argparse, dataclasses, datetime as dt, hashlib, json, re, sys
from pathlib import Path
from typing import Any

STATE_RE=re.compile(r"^[A-Z]{3}\.md$"); ISO_RE=re.compile(r"^[A-Z]{3}$")
OUTCOMES={"R","S","U","N"}; VERSION=2; GENERATOR="tools/migrate_state_abox.py:v2"
LEGACY_VERSION=1; LEGACY_GENERATOR="tools/migrate_state_abox.py:v1"
OWNED=("@context","iri","id","type","name","iso3","dossier","publicReviewIssue","lastSubstantiveReview")
FORBIDDEN=re.compile(r"current[-_]?governance|governance[-_]?(status|outcome)|restriction[-_]?status|restricted[-_]?status|tier|provisional[-_]?outcome|(^|[-_])outcome($|[-_])|inherit.*restrict|restrict.*inherit",re.I)

@dataclasses.dataclass(frozen=True)
class Dossier:
    path:Path; iso3:str; dossier_id:str; entity:str; issue:int; outcome:str; last_reviewed:str
@dataclasses.dataclass
class Summary:
    dossiers_seen:int=0; selected:int=0
    created:list[str]=dataclasses.field(default_factory=list); updated:list[str]=dataclasses.field(default_factory=list)
    unchanged:list[str]=dataclasses.field(default_factory=list); conflicts:list[str]=dataclasses.field(default_factory=list)
    state_actor_count:int=0; unique_iso3:int=0; unique_ids:int=0; unique_dossiers:int=0; generated_manifest_entries:int=0

def unquote(v:str)->str:
    v=v.strip(); return v[1:-1] if len(v)>=2 and v[0]==v[-1] and v[0] in "\"'" else v

def frontmatter(text:str)->dict[str,str]:
    lines=text.splitlines()
    if not lines or lines[0].strip()!="---": raise ValueError("missing YAML frontmatter opener")
    try: end=next(i for i,x in enumerate(lines[1:],1) if x.strip()=="---")
    except StopIteration as e: raise ValueError("missing YAML frontmatter closer") from e
    out={}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"): continue
        if ":" not in line: raise ValueError(f"unsupported frontmatter line: {line!r}")
        k,v=line.split(":",1); out[k.strip()]=unquote(v)
    return out

def date(v:str,label:str)->dt.date:
    try: return dt.date.fromisoformat(v)
    except (TypeError,ValueError) as e: raise ValueError(f"{label}: invalid ISO date {v!r}") from e

def load_dossiers(root:Path, require_195:bool=True)->list[Dossier]:
    paths=[p for p in sorted(root.glob("*.md")) if STATE_RE.fullmatch(p.name)]
    if require_195 and len(paths)!=195: raise ValueError(f"expected 195 State dossiers, found {len(paths)}")
    out=[]; isos=set(); ids=set(); issues=set()
    for p in paths:
        m=frontmatter(p.read_text(encoding="utf-8")); req=("id","entity","iso3","issue","provisional_outcome","last_reviewed")
        missing=[k for k in req if not m.get(k)]
        if missing: raise ValueError(f"{p}: missing {missing}")
        iso=m["iso3"].upper(); did=m["id"]; outcome=m["provisional_outcome"]
        if not ISO_RE.fullmatch(iso) or iso!=p.stem: raise ValueError(f"{p}: ISO3 mismatch")
        if did!=f"ECL-STATE-{iso}": raise ValueError(f"{p}: expected id ECL-STATE-{iso}")
        try: issue=int(m["issue"])
        except ValueError as e: raise ValueError(f"{p}: issue must be integer") from e
        if issue<=0 or issue in issues or iso in isos or did in ids: raise ValueError(f"{p}: duplicate/invalid identity mapping")
        if outcome not in OUTCOMES: raise ValueError(f"{p}: invalid provisional_outcome {outcome!r}")
        date(m["last_reviewed"],str(p)); entity=m["entity"].strip()
        if not entity: raise ValueError(f"{p}: empty entity")
        isos.add(iso); ids.add(did); issues.add(issue); out.append(Dossier(p,iso,did,entity,issue,outcome,m["last_reviewed"]))
    return out

def projection(d:Dossier)->dict[str,Any]:
    return {"@context":"../../ontology/ecl-context.jsonld","iri":f"ecl:STATE-{d.iso3}","id":f"STATE-{d.iso3}","type":"State","name":d.entity,"iso3":d.iso3,"dossier":f"../../dossiers/states/{d.iso3}.md","publicReviewIssue":f"https://github.com/Papishushi/exergic-commons-license/issues/{d.issue}","lastSubstantiveReview":d.last_reviewed}

def phash(r:dict[str,Any])->str:
    raw=json.dumps({k:r.get(k) for k in OWNED},sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return hashlib.sha256(raw.encode()).hexdigest()

def guard(r:dict[str,Any],label:str)->None:
    for k in r:
        if FORBIDDEN.search(k): raise ValueError(f"{label}: forbidden governance/inheritance field on State: {k}")
    if r.get("type")=="State" and "status" in r: raise ValueError(f"{label}: generic status forbidden on State")

def read_obj(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(f"{p}: expected JSON object")
    return x

def load_manifest(p:Path)->tuple[dict[str,str],bool]:
    if not p.exists(): return {},False
    x=read_obj(p); hashes=x.get("generatedProjectionSha256")
    if not isinstance(hashes,dict): raise ValueError(f"{p}: unsupported manifest")
    if x.get("version")==VERSION and x.get("generator")==GENERATOR: return dict(hashes),False
    if x.get("version")==LEGACY_VERSION and x.get("generator")==LEGACY_GENERATOR: return dict(hashes),True
    raise ValueError(f"{p}: unsupported manifest")

def manifest_text(h:dict[str,str], legacy:bool=False)->str:
    version=LEGACY_VERSION if legacy else VERSION
    generator=LEGACY_GENERATOR if legacy else GENERATOR
    return json.dumps({"version":version,"generator":generator,"note":"Derived conflict-detection hashes only; not ABox data and not a governance source.","generatedProjectionSha256":dict(sorted(h.items()))},indent=2,ensure_ascii=False)+"\n"

def ordered(r:dict[str,Any])->dict[str,Any]:
    order=("@context","iri","id","type","name","iso3","aliases","dossier","publicReviewIssue","lastSubstantiveReview","reviewDue","reviewClass","reviewReason","trackedObjects","monitorIds","controls","participatesIn","operates","deploys","materiallyBenefits","targetsOrAffects","remediates","reviews")
    return {k:r[k] for k in (*order,*sorted(set(r)-set(order))) if k in r}

def record_text(r:dict[str,Any])->str: return json.dumps(ordered(r),indent=2,ensure_ascii=False)+"\n"

def synthetic_v1_due(d:Dossier)->str:
    return (date(d.last_reviewed,"last")+dt.timedelta(days=90)).isoformat()

def merge(d:Dossier, old:dict[str,Any]|None, old_hash:str|None, cleanup_v1:bool=False)->dict[str,Any]:
    want=projection(d)
    if old is None:
        return {**want,"aliases":[d.iso3],"reviewClass":"manual"}
    guard(old,d.iso3); legacy_name=None
    if old_hash is not None and phash(old)!=old_hash: raise ValueError(f"{d.iso3}: generator-owned fields changed since manifest")
    if old_hash is None:
        for k,v in want.items():
            if k not in old or old[k]==v: continue
            if k=="name": legacy_name=str(old[k]); continue
            raise ValueError(f"{d.iso3}: legacy {k} conflicts with dossier-derived value")
    out=dict(old)
    # v1 invented a +90-day date for every newly generated manual State. Remove
    # only that exact synthetic pattern while upgrading the v1 manifest. Future
    # v2 runs preserve any manually curated reviewDue, including on manual class.
    if cleanup_v1 and out.get("reviewClass")=="manual" and not out.get("reviewReason") and out.get("reviewDue")==synthetic_v1_due(d):
        out.pop("reviewDue",None)
    out.update(want); out.setdefault("aliases",[d.iso3]); out.setdefault("reviewClass","manual")
    if legacy_name and legacy_name!=d.entity and legacy_name not in out["aliases"]: out["aliases"].append(legacy_name)
    if d.iso3 not in out["aliases"]: out["aliases"].insert(0,d.iso3)
    if not isinstance(out["aliases"],list) or not out["aliases"]: raise ValueError(f"{d.iso3}: aliases must be non-empty list")
    if out["reviewClass"] not in {"hot","active","stable","manual"}: raise ValueError(f"{d.iso3}: invalid reviewClass")
    due=out.get("reviewDue")
    if due is None and out["reviewClass"]!="manual": raise ValueError(f"{d.iso3}: non-manual reviewClass requires reviewDue")
    if due is not None and date(str(due),f"{d.iso3}.reviewDue")<date(d.last_reviewed,f"{d.iso3}.last_reviewed"): raise ValueError(f"{d.iso3}: reviewDue predates last review")
    guard(out,d.iso3); return out

def scan(root:Path)->tuple[int,int,int,int]:
    rs=[]
    for p in sorted(root.glob("STATE-*.json")):
        x=read_obj(p)
        if x.get("type")=="State": guard(x,str(p)); rs.append(x)
    return len(rs),len({x.get("iso3") for x in rs}),len({x.get("id") for x in rs}),len({x.get("dossier") for x in rs})

def migrate(dossier_root:Path,entity_root:Path,manifest:Path,iso3:str|None=None,check:bool=False,dry_run:bool=False,require_195:bool=True)->tuple[Summary,int]:
    ds=load_dossiers(dossier_root,require_195=require_195); selected=ds
    if iso3:
        iso3=iso3.upper(); selected=[d for d in ds if d.iso3==iso3]
        if not ISO_RE.fullmatch(iso3) or not selected: raise ValueError(f"unknown ISO3 {iso3!r}")
    hashes,cleanup_v1=load_manifest(manifest); next_hashes=dict(hashes); s=Summary(len(ds),len(selected)); writes=[]
    for d in selected:
        p=entity_root/f"STATE-{d.iso3}.json"; old=read_obj(p) if p.exists() else None
        try: new=merge(d,old,hashes.get(d.iso3),cleanup_v1); guard(new,d.iso3)
        except ValueError as e: s.conflicts.append(str(e)); continue
        next_hashes[d.iso3]=phash(new); text=record_text(new); cur=p.read_text(encoding="utf-8") if p.exists() else None
        if cur==text: s.unchanged.append(d.iso3)
        elif p.exists(): s.updated.append(d.iso3); writes.append((p,text))
        else: s.created.append(d.iso3); writes.append((p,text))
    # A v1 manifest certifies that v1's synthetic review dates may still exist.
    # A partial --iso3 pass cannot prove the rest of the corpus is clean, so it
    # must remain v1. Only a full-corpus pass is allowed to promote to v2.
    keep_legacy_manifest=cleanup_v1 and iso3 is not None
    mt=manifest_text(next_hashes,legacy=keep_legacy_manifest); mc=manifest.read_text(encoding="utf-8") if manifest.exists() else None
    if not s.conflicts and mt!=mc: writes.append((manifest,mt))
    if not (check or dry_run) and not s.conflicts:
        for p,text in writes: p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8")
    c,ui,ud,udp=scan(entity_root); s.state_actor_count=c; s.unique_iso3=ui; s.unique_ids=ud; s.unique_dossiers=udp; s.generated_manifest_entries=len(next_hashes)
    return s, 2 if s.conflicts else (1 if check and writes else 0)

def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--dossier-root",type=Path,default=Path("dossiers/states")); ap.add_argument("--entity-root",type=Path,default=Path("knowledge/entities")); ap.add_argument("--manifest",type=Path,default=Path("knowledge/generated/state-abox-manifest.json")); ap.add_argument("--iso3"); g=ap.add_mutually_exclusive_group(); g.add_argument("--check",action="store_true"); g.add_argument("--dry-run",action="store_true"); ap.add_argument("--summary",type=Path); a=ap.parse_args(argv)
    try: s,code=migrate(a.dossier_root,a.entity_root,a.manifest,a.iso3,a.check,a.dry_run)
    except (OSError,ValueError,json.JSONDecodeError) as e: print(f"error: {e}",file=sys.stderr); return 2
    raw=json.dumps(dataclasses.asdict(s),indent=2,sort_keys=True,ensure_ascii=False)+"\n"; print(raw,end="")
    if a.summary: a.summary.parent.mkdir(parents=True,exist_ok=True); a.summary.write_text(raw,encoding="utf-8")
    return code
if __name__=="__main__": raise SystemExit(main())
