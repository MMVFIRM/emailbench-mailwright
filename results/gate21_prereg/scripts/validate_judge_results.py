#!/usr/bin/env python3
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SEALED=ROOT/'sealed'; EV=ROOT/'evaluator'
ap=argparse.ArgumentParser(); ap.add_argument('judge_results'); a=ap.parse_args(); jr=json.loads(Path(a.judge_results).read_text()); key={x['judge_id']:x for x in json.loads((SEALED/'judge_key.json').read_text())}
errors=[]; seen=set()
for g in jr.get('groups',[]):
    jid=g.get('judge_id');
    if jid not in key: errors.append(f'unknown judge_id {jid}'); continue
    if jid in seen: errors.append(f'duplicate judge_id {jid}')
    seen.add(jid); task_id=key[jid]['task_id']; full=json.loads((SEALED/'tasks'/task_id/'task.json').read_text()); exp={c['id'] for c in full.get('criteria',[])}
    for lab in ['A','B']:
        c=g.get('candidates',{}).get(lab)
        if not isinstance(c,dict): errors.append(f'{jid}/{lab}: missing candidate'); continue
        arr=c.get('criteria',[]); ids=[x.get('criterion_id') for x in arr]
        if set(ids)!=exp: errors.append(f'{jid}/{lab}: criterion ids mismatch; missing={sorted(exp-set(ids))} extra={sorted(set(ids)-exp)}')
        if len(ids)!=len(set(ids)): errors.append(f'{jid}/{lab}: duplicate criterion id')
missing=set(key)-seen
if missing: errors.append(f'missing groups: {sorted(missing)}')
out={'expected_groups':len(key),'seen_groups':len(seen),'errors':errors,'VALID':not errors}; print(json.dumps(out,indent=2)); (ROOT/'results').mkdir(exist_ok=True); (ROOT/'results'/'judge_validation.json').write_text(json.dumps(out,indent=2)); raise SystemExit(0 if out['VALID'] else 2)
