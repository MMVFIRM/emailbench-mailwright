#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'runner'; SEALED=ROOT/'sealed'; CFG=json.loads((ROOT/'evaluator/gate21_config.json').read_text())
key=json.loads((SEALED/'condition_key.json').read_text()); expected={x['run_id']:x for x in key}
files=list((RUN/'submissions').glob('*.json')); seen={}; errors=[]; violations=[]
req=['run_id','benchmark_task_id','model','final_status','final_answer','citations','evidence_actions','usage']
for p in files:
    try:o=json.loads(p.read_text())
    except Exception as e: errors.append(f'{p.name}: invalid JSON: {e}'); continue
    miss=[k for k in req if k not in o]
    if miss: errors.append(f'{p.name}: missing {miss}'); continue
    rid=o['run_id'];
    if rid not in expected: errors.append(f'{p.name}: unexpected run_id {rid}'); continue
    if rid in seen: errors.append(f'{p.name}: duplicate run_id {rid}')
    seen[rid]=p.name
    if o['benchmark_task_id']!=expected[rid]['task_id']: errors.append(f'{p.name}: task id mismatch')
    words=len(str(o.get('final_answer','')).split()); actions=len(o.get('evidence_actions',[]))
    if words>CFG['answer_word_cap']: violations.append({'run_id':rid,'type':'word_cap','value':words,'limit':CFG['answer_word_cap']})
    if actions>CFG['evidence_action_budget']: violations.append({'run_id':rid,'type':'action_budget','value':actions,'limit':CFG['evidence_action_budget']})
missing=sorted(set(expected)-set(seen))
out={'expected':len(expected),'found_valid_structure':len(seen),'missing':missing,'errors':errors,'constraint_violations':violations,'STRUCTURALLY_VALID':not missing and not errors}
print(json.dumps(out,indent=2))
(ROOT/'results').mkdir(exist_ok=True); (ROOT/'results'/'validation_report.json').write_text(json.dumps(out,indent=2))
raise SystemExit(0 if out['STRUCTURALLY_VALID'] else 2)
