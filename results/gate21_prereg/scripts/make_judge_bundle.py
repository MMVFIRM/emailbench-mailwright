#!/usr/bin/env python3
import json, random, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RUN=ROOT/'runner'; SEALED=ROOT/'sealed'; EV=ROOT/'evaluator'
CFG=json.loads((EV/'gate21_config.json').read_text()); key=json.loads((SEALED/'condition_key.json').read_text()); tasks={x['task_id']:x for x in json.loads((SEALED/'task_index.json').read_text())}
subs={json.loads(p.read_text())['run_id']:json.loads(p.read_text()) for p in (RUN/'submissions').glob('*.json')}
by={}
for x in key: by.setdefault(x['task_id'],{})[x['condition']]=x
rng=random.Random(CFG['judge_blind_seed']); groups=[]; judge_key=[]
for task_id in sorted(by):
    m=by[task_id]; labels=['A','B']; rng.shuffle(labels); mapping={labels[0]:'control',labels[1]:'lrpe_v07'}
    judge_id='J'+task_id[1:]+'-'+str(rng.randrange(100000,999999))
    full=json.loads((SEALED/'tasks'/task_id/'task.json').read_text())
    cand={}
    keyrow={'judge_id':judge_id,'task_id':task_id,'stratum':tasks[task_id]['stratum']}
    for lab,cond in mapping.items():
        entry=m[cond]; s=subs[entry['run_id']]
        # Strip all condition-fingerprinting trace. Judge sees only final work product and explicit citations.
        cand[lab]={'final_status':s.get('final_status'),'final_answer':s.get('final_answer',''),'citations':s.get('citations',[])}
        keyrow[lab]={'condition':cond,'run_id':entry['run_id']}
    groups.append({'judge_id':judge_id,'task_id':task_id,'stratum':tasks[task_id]['stratum'],'title':full.get('title',''),'instructions':full.get('instructions',''),'criteria':full.get('criteria',[]),'candidates':cand})
    judge_key.append(keyrow)
# Make judge bundle directory cleanly.
bundle=EV/'judge_bundle'
if bundle.exists(): shutil.rmtree(bundle)
bundle.mkdir()
(bundle/'groups.json').write_text(json.dumps({'benchmark':'Harvey LAB external subset','groups':groups},indent=2))
shutil.copy2(EV/'JUDGE_AGENT_INSTRUCTIONS.md',bundle/'JUDGE_AGENT_INSTRUCTIONS.md')
(SEALED/'judge_key.json').write_text(json.dumps(judge_key,indent=2))
print(f'Built condition-blind bundle with {len(groups)} paired tasks at {bundle}')
