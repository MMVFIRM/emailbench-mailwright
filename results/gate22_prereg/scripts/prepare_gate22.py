#!/usr/bin/env python3
import argparse, hashlib, json, random, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CFG = json.loads((HERE/'gate22_config.json').read_text())
MAN = json.loads((HERE/'selection_manifest.json').read_text())


def run(cmd, cwd=None):
    print('+', ' '.join(map(str,cmd)))
    subprocess.run(cmd, cwd=cwd, check=True)


def opaque(seed, text, prefix='R'):
    h = hashlib.sha256(f'{seed}|{text}'.encode()).hexdigest().upper()
    return prefix + h[:12]


def copy_documents(task_dir: Path, dest: Path):
    src = task_dir/'documents'
    dest.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copytree(src, dest, dirs_exist_ok=True)


def instantiate(template, vals):
    out = template
    for k,v in vals.items():
        out = out.replace('{{'+k+'}}', str(v))
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out', default='gate22_prepared')
    ap.add_argument('--repo-dir', default=None, help='Use an existing Harvey LAB checkout instead of cloning')
    ap.add_argument('--keep-source', action='store_true')
    args=ap.parse_args()
    out=Path(args.out).resolve()
    if out.exists():
        raise SystemExit(f'Output directory already exists: {out}')
    out.mkdir(parents=True)

    source = Path(args.repo_dir).resolve() if args.repo_dir else out/'_harvey_source'
    all_paths=[('pure_research',p) for p in MAN['pure_research']]+[('stress_reconciliation',p) for p in MAN['stress_reconciliation']]
    selected_dirs=sorted({str(Path(p).parent) for _,p in all_paths})
    if not args.repo_dir:
        # Sparse/partial clone: selected benchmark tasks contain many binary matter documents,
        # so avoid downloading the rest of LAB's large task corpus.
        run(['git','clone','--filter=blob:none','--no-checkout',CFG['harvey_repo'],str(source)])
        run(['git','sparse-checkout','init','--cone'], cwd=source)
        run(['git','sparse-checkout','set',*selected_dirs], cwd=source)
        run(['git','fetch','--depth','1','origin',CFG['harvey_commit']], cwd=source)
        run(['git','checkout',CFG['harvey_commit']], cwd=source)
    else:
        got=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
        if got != CFG['harvey_commit']:
            print(f'WARNING: existing repo HEAD {got} != pinned {CFG["harvey_commit"]}', file=sys.stderr)

    runner=out/'runner'; sealed=out/'sealed'; evaluator=out/'evaluator'; results=out/'results'
    for p in [runner/'tasks', runner/'task_data', runner/'submissions', sealed/'tasks', evaluator, results]: p.mkdir(parents=True,exist_ok=True)

    control=(HERE/'prompts/control_prompt.txt').read_text()
    lrpe=(HERE/'prompts/lrpe_v08_prompt.txt').read_text()
    task_entries=[]; cond_entries=[]
    if len(all_paths)!=CFG['unique_tasks']:
        raise SystemExit(f'Manifest has {len(all_paths)} tasks, config expects {CFG["unique_tasks"]}')

    for i,(stratum,rel) in enumerate(all_paths,1):
        src=source/rel
        if not src.exists(): raise SystemExit(f'Missing selected task: {rel}')
        obj=json.loads(src.read_text())
        criteria=obj.get('criteria')
        if not isinstance(criteria,list) or not criteria: raise SystemExit(f'No criteria in {rel}')
        task_id=f'H{i:02d}'
        task_dir=src.parent
        data_dir=runner/'task_data'/task_id/'documents'
        copy_documents(task_dir,data_dir)
        # Full task stays sealed.
        sdir=sealed/'tasks'/task_id; sdir.mkdir(parents=True,exist_ok=True)
        (sdir/'task.json').write_text(json.dumps(obj,indent=2))
        meta={
            'task_id':task_id,'stratum':stratum,'source_path':rel,'title':obj.get('title',''),
            'instructions':obj.get('instructions',''),'work_type':obj.get('work_type'),'tags':obj.get('tags',[]),
            'criteria_count':len(criteria),'document_dir':f'runner/task_data/{task_id}/documents'
        }
        task_entries.append(meta)
        for cond,templ in [('control',control),('lrpe_v08',lrpe)]:
            rid=opaque(CFG['task_seed'], f'{task_id}|{cond}')
            vals={
                'RUN_ID':rid,'TASK_ID':task_id,'TITLE':obj.get('title',''),'INSTRUCTIONS':obj.get('instructions',''),
                'DOCUMENT_DIR':f'runner/task_data/{task_id}/documents','WORD_CAP':CFG['answer_word_cap'],
                'ACTION_BUDGET':CFG['evidence_action_budget']
            }
            prompt=instantiate(templ,vals)
            cond_entries.append({'run_id':rid,'task_id':task_id,'condition':cond,'stratum':stratum,'source_path':rel})
            # Condition label intentionally omitted from filename; prompt contents necessarily differ.
            idx=len(cond_entries)
            (runner/'tasks'/f'task_{idx:03d}_{rid}.md').write_text(prompt)

    rng=random.Random(CFG['task_seed']); rng.shuffle(cond_entries)
    # Renumber physical task files into randomized queue without changing prompt/run IDs.
    old_files={p.stem.split('_')[-1]:p for p in (runner/'tasks').glob('*.md')}
    tmp=runner/'_tmp_tasks'; tmp.mkdir()
    queue=[]
    for idx,e in enumerate(cond_entries,1):
        src=old_files[e['run_id']]
        dst=tmp/f'task_{idx:03d}_{e["run_id"]}.md'; shutil.copy2(src,dst)
        q={k:v for k,v in e.items() if k!='condition'}
        q['task_file']=dst.name; queue.append(q)
    shutil.rmtree(runner/'tasks'); tmp.rename(runner/'tasks')

    (runner/'task_queue.json').write_text(json.dumps(queue,indent=2))
    (runner/'RUNNER_AGENT_INSTRUCTIONS.md').write_text('''# Gate 22 run-agent instructions\n\nRun every file in `tasks/` in a fresh independent model context. A run agent may read only its assigned task file and the referenced directory under `task_data/`. Do not expose `sealed/`, evaluator criteria, another run, or prior outputs. Save the single returned JSON object as `submissions/<run_id>.json`. Retry only transport failures or cases where no valid JSON response was produced.\n''')
    (sealed/'task_index.json').write_text(json.dumps(task_entries,indent=2))
    (sealed/'condition_key.json').write_text(json.dumps(cond_entries,indent=2))
    shutil.copy2(HERE/'gate22_config.json',sealed/'gate22_config.json')
    shutil.copy2(HERE/'evaluator/JUDGE_AGENT_INSTRUCTIONS.md',evaluator/'JUDGE_AGENT_INSTRUCTIONS.md')
    for name in ['validate_submissions.py','make_judge_bundle.py','validate_judge_results.py','score_gate22.py']:
        shutil.copy2(HERE/'scripts'/name,evaluator/name)
    shutil.copy2(HERE/'gate22_config.json',evaluator/'gate22_config.json')
    (out/'README.md').write_text('''# Prepared Gate 22\n\n- `runner/`: run-agent materials. Safe to distribute to run agents.\n- `sealed/`: full Harvey criteria and condition mapping. DO NOT expose before blind judging is complete.\n- `evaluator/`: judge/scoring scripts. `make_judge_bundle.py` reads sealed files by relative path.\n- `results/`: final scorer output.\n''')
    if not args.keep_source and not args.repo_dir:
        shutil.rmtree(source)
    print(f'Prepared {len(task_entries)} unique tasks / {len(cond_entries)} runs in {out}')

if __name__=='__main__': main()
