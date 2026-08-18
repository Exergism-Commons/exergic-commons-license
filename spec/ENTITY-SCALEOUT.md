# State dossier entity/project scale-out

## Purpose

ECL's canonical State dossiers contain materially relevant institutions, companies, persons, projects, systems and deployments that are not yet uniformly represented as first-class ABox identities. This scale-out closes that representation gap without converting prose association into attribution or governance.

The target property is **representational completeness**, not accusation density.

## Non-inference rules

1. A textual mention is not identity proof.
2. An identity record is not a Claim that the entity performed, controlled, operated, supplied or participated in anything.
3. `partOf`, `tracks`, `operates`, `controls`, `participatesIn`, `deploys`, supplier/customer relations and other graph edges never propagate an ECL governance outcome.
4. A company, agency, person, project or deployment may be materialized as identity-only even when its governance status is unknown or not applicable.
5. R/S/U/N remains a governance determination supported by its own record; this work never derives it from mention frequency, graph centrality, association, sanctions, source prominence, or the discovery audit's review priority.
6. Candidate extraction is discovery only. False positives are expected and must not enter `knowledge/entities/` without a stable, disambiguated referent.
7. A Project/Deployment boundary must be objectively knowable enough to distinguish the object from a policy family, entire technology class, State apparatus, vendor product line, or speculative future deployment.
8. Proposition-specific edges require proposition-specific evidence. Identity evidence is insufficient for conduct attribution.

## Coverage classes

The audit distinguishes:

- **materialized** — a dossier mention resolves by canonical name/alias to an existing ABox identity;
- **review-candidate** — a deterministic extractor found a plausible named actor/institution/project/deployment that does not resolve to an existing identity;
- **curated-identity** — a reviewed candidate with a stable, disambiguated referent that has been promoted to an identity-only ABox record;
- **deferred** — plausible referent, but the current record does not support an exact enough identity or Project/Deployment boundary;
- **rejected** — extraction noise, generic class, legal/policy phrase, geographic label, or other non-identity.

Only the first three correspond to a represented identity. `review-candidate`, `deferred`, and `rejected` have no ontology or governance effect.

## Audit contract

`tools/audit_state_dossier_entities.py` scans all canonical `dossiers/states/*.md`, compares detected names against `knowledge/entities/*.json`, and emits:

- deterministic candidate groups;
- every dossier/line/section occurrence;
- whether a name already resolves to a canonical identity;
- a review-priority value used only to order curation work;
- State/outcome context so R/S dossiers can be reviewed first without treating the outcome as an actor/project attribution.

The audit must remain reproducible from repository contents and must not call an LLM, external NER service, search engine, or mutable external API.

## Promotion rule

A candidate may be promoted only when the repository contains enough information to establish:

- canonical name;
- stable identity type (`Agency`, `Organization`, `Institution`, `Person`, `Project`, or `Deployment` as applicable);
- an unambiguous dossier/evidence provenance path;
- aliases needed to resolve the dossier wording;
- a review clock/reason consistent with the existing knowledge model.

Promotion does **not** require a governance outcome.

For `Project`/`Deployment`, the reviewer must additionally record why the object boundary is exact enough to be tracked independently.

## Relation rule

After identity promotion, relation curation is a separate pass. A relation is created only as an auditable Claim with supporting EvidenceItem(s). The existence of two identities in the same dossier is never enough.

## Intended workflow

1. Run the deterministic full-corpus audit.
2. Review unresolved candidates in descending discovery priority.
3. Mark each candidate `curated-identity`, `deferred`, or `rejected` in a generated/reviewed manifest.
4. Materialize reviewed identity-only records in bounded tranches.
5. Add relation Claims only where proposition-specific evidence exists.
6. Re-run the audit until unexplained high-priority unresolved candidates are eliminated.
7. Re-run Formal Exergism coverage after the actor/object universe stabilizes.

This ordering prevents Formal Exergism completeness from being measured against an artificially sparse ABox.
