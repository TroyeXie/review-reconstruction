"""Deterministic record checks; no scientific reading or completion inference."""
from __future__ import annotations
import argparse
import collections
import csv
import json
import re
from pathlib import Path
import sys

ALIASES={'code':('reference_code','编码'),'id':('paper_id','记录ID'),'path':('pdf_path','PDF相对路径')}
SIMPLE_STATUSES={'full_text_read':'main','mother_full_read':'main','partial_read':'partial',
                 'not_yet_read':'unread','source_missing':'missing','abstract_only':'abstract'}
CANONICAL_STATUSES={'MAIN_TEXT_READ':'main',
    'PROVIDED_VERSION_MAIN_TEXT_READ_VOR_UNVERIFIED':'provided',
    'PARTIAL_READ':'partial','PUBLISHED_ABSTRACT_READ':'abstract',
    'PUBLISHED_CORRECTION_READ':'correction_read',
    'NOT_YET_READ':'unread','SOURCE_UNAVAILABLE':'missing','SOURCE_GAP':'missing',
    'REGISTRY_CURRENT_RECORD_READ_HISTORY_UNVERIFIED':'registry_read',
    'REGISTRY_REVIEW_PENDING':'unread'}
READ_STATUSES=set(SIMPLE_STATUSES)|set(CANONICAL_STATUSES)
INDEX_KINDS={'literature','mother_review','mother_supplement','registry'}
KINDS=INDEX_KINDS|{'correction','analyst_associated_literature'}

def load(path: Path) -> list[dict[str,str]]:
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if not reader.fieldnames:raise ValueError(f'No CSV header: {path.name}')
        rows=list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError(f'Ragged CSV rows: {path.name}')
    return rows

def value(row: dict[str,str],field: str) -> str:
    for key in ALIASES[field]:
        if key in row:return row[key].strip()
    raise ValueError('Missing field: '+ '/'.join(ALIASES[field]))

def load_aliases(path: Path) -> dict[str,str]:
    def unique_object(pairs):
        result={}
        for key,item in pairs:
            if key in result:raise ValueError('Duplicate JSON key in alias input: '+key)
            result[key]=item
        return result
    payload=json.loads(path.read_text(encoding='utf-8-sig'),object_pairs_hook=unique_object)
    if not isinstance(payload,dict):raise ValueError('Alias input must be a JSON object')
    aliases=payload.get('reviewed_shared_evidence_aliases',payload)
    if not isinstance(aliases,dict):raise ValueError('reviewed_shared_evidence_aliases must be an object')
    if any(not isinstance(k,str) or not isinstance(v,str) or not k or not v or k!=k.strip() or v!=v.strip()
           for k,v in aliases.items()):raise ValueError('Aliases must map exact nonempty IDs to exact nonempty IDs')
    return aliases

def apply_explicit_aliases(aliases,index_rows,literature,full,provided):
    covered_full=set(full);covered_provided=set(provided);errors=[];validated=[]
    for alias,target in aliases.items():
        if not isinstance(alias,str) or not isinstance(target,str) or alias==target or alias not in literature or target not in literature:
            errors.append({'invalid_alias_endpoint':str(alias),'target':str(target)});continue
        if target in aliases:
            errors.append({'alias_chain_not_supported':alias,'target':target});continue
        if target not in full|provided:
            errors.append({'alias_target_has_no_direct_main_read':alias,'target':target});continue
        signatures=set()
        for row in index_rows[alias]+index_rows[target]:
            path=value(row,'path');digest=row.get('sha256',row.get('SHA256','')).strip().lower()
            page=row.get('pdf_start_page',row.get('PDF起始页','')).strip()
            if not path or not re.fullmatch('[0-9a-f]{64}',digest):
                errors.append({'alias_requires_same_recorded_file_and_sha256':alias});break
            if ('pdf_start_page' in row or 'PDF起始页' in row) and not page:
                errors.append({'alias_missing_recorded_start_page':alias});break
            signatures.add((path,digest,page))
        else:
            if len(signatures)!=1:errors.append({'alias_source_identity_metadata_mismatch':alias,'target':target})
            else:validated.append((alias,target))
    if not errors:
        for alias,target in validated:
            (covered_full if target in full else covered_provided).add(alias)
    covered_provided-=covered_full
    return covered_full,covered_provided,errors,len(validated) if not errors else 0

def audit(index: list[dict[str,str]],readings: list[dict[str,str]],aliases: dict[str,str]|None=None) -> dict:
    ids={value(r,'id') for r in index};codes=[value(r,'code') for r in index]
    errors=[]
    if '' in ids or '' in codes:errors.append('Empty identifier in source index')
    dup=[k for k,n in collections.Counter(codes).items() if n>1]
    if dup:errors.append({'duplicate_reference_codes':dup})
    index_rows=collections.defaultdict(list);index_kinds=collections.defaultdict(set)
    for r in index:
        ident=value(r,'id');index_rows[ident].append(r)
        explicit=r.get('record_kind','').strip();scope=r.get('范围','').strip()
        scoped={'main':'literature','supplement':'literature','registry':'registry'}.get(scope)
        if '范围' in r and scoped is None:errors.append({'unrecognised_index_scope':scope,'paper_id':ident})
        kind=explicit or scoped or 'literature'
        if kind not in INDEX_KINDS:errors.append({'unrecognised_index_record_kind':kind,'paper_id':ident})
        if explicit and scoped and explicit!=scoped:errors.append({'conflicting_index_record_kind':ident})
        index_kinds[ident].add(kind)
    for ident,kinds in index_kinds.items():
        if len(kinds)>1:errors.append({'conflicting_index_kinds':ident,'kinds':sorted(kinds)})
    literature={i for i,k in index_kinds.items() if k=={'literature'}}
    registry={i for i,k in index_kinds.items() if k=={'registry'}}
    recorded=collections.defaultdict(lambda:collections.defaultdict(set))
    states=collections.Counter();kinds_seen=collections.Counter();unindexed=set()
    for r in readings:
        ident=r.get('paper_id','').strip();raw=r.get('reading_status','').strip()
        states[raw]+=1
        if not ident:
            errors.append('Reading row lacks paper_id');continue
        if raw not in READ_STATUSES:
            errors.append({'unrecognised_reading_status':raw,'paper_id':ident});continue
        state={**SIMPLE_STATUSES,**CANONICAL_STATUSES}[raw]
        kind=r.get('record_kind','').strip()
        if not kind and raw in SIMPLE_STATUSES:kind='mother_review' if raw=='mother_full_read' else 'literature'
        if kind not in KINDS:
            errors.append({'missing_or_unrecognised_record_kind':kind,'paper_id':ident});continue
        kinds_seen[kind]+=1
        if (raw=='mother_full_read' and kind!='mother_review') or (raw in {'REGISTRY_CURRENT_RECORD_READ_HISTORY_UNVERIFIED','REGISTRY_REVIEW_PENDING'} and kind!='registry') or (kind=='registry' and state not in {'registry_read','partial','unread','missing'}) or (state=='correction_read' and kind!='correction') or (kind=='correction' and state!='correction_read'):
            errors.append({'invalid_status_for_record_kind':raw,'record_kind':kind,'paper_id':ident});continue
        if state in {'main','provided','registry_read','correction_read'} and not r.get('read_scope','').strip():
            errors.append({'claimed_read_without_scope':ident});continue
        # A correction is an indexed bibliographic item, not a main-text read.
        # Auxiliary reading is explicit and outside the original index.
        if kind=='analyst_associated_literature' and ident in ids:
            errors.append({'auxiliary_reading_id_present_in_index':ident});continue
        if kind in {'literature','registry','correction'}:
            if ident not in ids:
                errors.append({'reading_id_not_in_index':ident,'record_kind':kind});unindexed.add(ident);continue
            expected_kind='literature' if kind=='correction' else kind
            if index_kinds[ident]!={expected_kind}:
                errors.append({'reading_index_kind_mismatch':ident,'record_kind':kind});continue
        recorded[kind][state].add(ident)
    correction_ids=set(recorded['correction']['correction_read'])
    conflicts=correction_ids & set().union(*recorded['literature'].values())
    if conflicts:
        errors.append({'conflicting_correction_and_literature_reading_ids':sorted(conflicts)})
        # Do not choose between conflicting declarations or count either as read.
        for states_for_kind in (recorded['correction'],recorded['literature']):
            for members in states_for_kind.values():members.difference_update(conflicts)
    corrections=recorded['correction']['correction_read']
    auxiliary=recorded['analyst_associated_literature']
    auxiliary_counts={};seen_auxiliary=set()
    for state,label in [('main','main_text_read'),('provided','provided_version_main_text_read_vor_unverified'),
                        ('partial','partial_read_only'),('abstract','abstract_only'),
                        ('missing','source_missing_only'),('unread','not_yet_read')]:
        members=auxiliary[state]-seen_auxiliary
        auxiliary_counts[label]=len(members);seen_auxiliary.update(members)
    full=recorded['literature']['main']
    provided=recorded['literature']['provided']-full
    partial=recorded['literature']['partial']-full-provided
    abstract=recorded['literature']['abstract']-full-provided-partial
    missing=recorded['literature']['missing']-full-provided-partial-abstract
    supplied=aliases is not None;aliases=aliases or {}
    covered_full,covered_provided,alias_errors,validated=apply_explicit_aliases(aliases,index_rows,literature-correction_ids,full,provided)
    errors.extend(alias_errors)
    return {'relation_count':len(index),'unique_record_count':len(ids),
            'indexed_literature_count':len(literature),'indexed_registry_count':len(registry),
            'recorded_full_text_read_count':len(full),
            'recorded_provided_version_main_text_read_vor_unverified_count':len(provided),
            'recorded_any_provided_version_main_text_read_count':len(full|provided),
            'recorded_mother_read_count':len(recorded['mother_review']['main']),
            'recorded_mother_provided_version_read_vor_unverified_count':len(recorded['mother_review']['provided']-recorded['mother_review']['main']),
            'recorded_mother_supplement_read_count':len(recorded['mother_supplement']['main']),
            'recorded_mother_supplement_provided_version_read_vor_unverified_count':len(recorded['mother_supplement']['provided']-recorded['mother_supplement']['main']),
            'recorded_registry_read_count':len(recorded['registry']['registry_read']),
            'recorded_correction_read_count':len(corrections),
            'recorded_auxiliary_record_count':len(seen_auxiliary),
            'auxiliary_reading_counts':auxiliary_counts,
            'recorded_partial_read_only_count':len(partial),'recorded_abstract_only_count':len(abstract),
            'recorded_source_missing_only_count':len(missing),
            'records_without_full_read_record':len(literature-full-provided),
            'unread_literature_record_count':len(literature-full-provided-partial-abstract-corrections),
            'alias_mapping_supplied':supplied,'alias_mapping_count':len(aliases),
            'validated_alias_mapping_count':validated,
            'alias_added_main_coverage_count':len((covered_full|covered_provided)-(full|provided)),
            'literature_main_text_covered_with_aliases':len(covered_full),
            'literature_provided_version_unverified_covered_with_aliases':len(covered_provided),
            'literature_any_provided_version_main_text_covered_with_aliases':len(covered_full|covered_provided),
            'unread_literature_records_after_explicit_aliases':len(literature-covered_full-covered_provided-partial-abstract-corrections),
            'relations_with_nonempty_pdf_path':sum(bool(value(r,'path')) for r in index),
            'reading_row_states':dict(states),'reading_row_kinds':dict(kinds_seen),
            'unindexed_reading_ids':sorted(unindexed),'errors':errors,
            'limitations':['Counts describe records, not studies, scientific validity or completion.',
                'Direct records and explicit-alias coverage are separate; no alias is inferred from a title or ID spelling.',
                'Main text does not establish supplement reading. VOR-unverified main text and registry records are separate.',
                'Alias validation checks supplied index metadata and a direct main-read record; it does not reread PDFs, rehash source bytes or independently establish work identity.',
                'No alias mapping is applied unless explicitly supplied. Any invalid alias prevents all alias coverage application.',
                'Correction-read records remain in the original index denominator and without a main-text reading record, but are excluded from the unread residual; they cannot be alias endpoints.',
                'Explicit analyst-associated literature is counted separately, never added to original-index denominators, coverage or aliases. An indexed ID cannot be reclassified as auxiliary.',
                'Unindexed literature is reported as an error, not silently reclassified or included in source-index counts.']}

def locate(index: list[dict[str,str]],root: Path,ident: str) -> Path:
    root=root.resolve()
    matches=[r for r in index if ident in (value(r,'id'),value(r,'code'))]
    if not matches:raise ValueError('Identifier not present in index')
    paths={value(r,'path') for r in matches if value(r,'path')}
    if not paths:raise ValueError('No local file recorded for this identifier')
    resolved=set()
    for entry in paths:
        path=(root/entry).resolve()
        if not path.is_relative_to(root):raise ValueError('Recorded path escapes the selected library root')
        resolved.add(path)
    if len(resolved)!=1:raise ValueError('Multiple files/versions match; choose a reference code or resolve explicitly')
    path=resolved.pop()
    if not path.is_file():raise FileNotFoundError('Recorded source file is missing')
    return path

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('audit');p.add_argument('--index',type=Path,required=True);p.add_argument('--readings',type=Path,required=True);p.add_argument('--aliases',type=Path)
    p=sub.add_parser('locate');p.add_argument('--index',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--paper-id',required=True)
    args=parser.parse_args()
    try:
        index=load(args.index)
        if args.command=='audit':
            report=audit(index,load(args.readings),load_aliases(args.aliases) if args.aliases else None);print(json.dumps(report,ensure_ascii=False,indent=2));return 2 if report['errors'] else 0
        print(locate(index,args.root,args.paper_id));return 0
    except (OSError,ValueError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
