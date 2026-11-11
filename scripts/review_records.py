"""Deterministic record checks; no scientific reading or completion inference."""
from __future__ import annotations
import argparse
import collections
import csv
import json
from pathlib import Path
import sys

ALIASES={'code':('reference_code','编码'),'id':('paper_id','记录ID'),'path':('pdf_path','PDF相对路径')}
READ_STATUSES={'full_text_read','mother_full_read','partial_read','not_yet_read','source_missing','abstract_only'}

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

def audit(index: list[dict[str,str]],readings: list[dict[str,str]]) -> dict:
    ids={value(r,'id') for r in index};codes=[value(r,'code') for r in index]
    errors=[]
    if '' in ids or '' in codes:errors.append('Empty identifier in source index')
    dup=[k for k,n in collections.Counter(codes).items() if n>1]
    if dup:errors.append({'duplicate_reference_codes':dup})
    full=set();mothers=set();states=collections.Counter()
    for r in readings:
        ident=r.get('paper_id','').strip();status=r.get('reading_status','').strip()
        states[status]+=1
        if not ident:errors.append('Reading row lacks paper_id')
        if status not in READ_STATUSES:errors.append({'unrecognised_reading_status':status,'paper_id':ident})
        if status in {'full_text_read','mother_full_read'}:
            if not r.get('read_scope','').strip():errors.append({'claimed_read_without_scope':ident})
            elif status=='mother_full_read':mothers.add(ident)
            elif ident in ids:full.add(ident)
            else:errors.append({'reading_id_not_in_index':ident})
    return {'relation_count':len(index),'unique_record_count':len(ids),
            'recorded_full_text_read_count':len(full),'recorded_mother_read_count':len(mothers),
            'records_without_full_read_record':len(ids-full),
            'relations_with_nonempty_pdf_path':sum(bool(value(r,'path')) for r in index),
            'reading_row_states':dict(states),'errors':errors,
            'limitations':'Counts describe records only. No study count, relationship analysis, scientific validity, source existence, or completion is inferred.'}

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
    p=sub.add_parser('audit');p.add_argument('--index',type=Path,required=True);p.add_argument('--readings',type=Path,required=True)
    p=sub.add_parser('locate');p.add_argument('--index',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--paper-id',required=True)
    args=parser.parse_args()
    try:
        index=load(args.index)
        if args.command=='audit':
            report=audit(index,load(args.readings));print(json.dumps(report,ensure_ascii=False,indent=2));return 2 if report['errors'] else 0
        print(locate(index,args.root,args.paper_id));return 0
    except (OSError,ValueError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
