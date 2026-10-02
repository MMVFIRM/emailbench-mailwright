#!/usr/bin/env python3
import argparse, json, math, random, statistics
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RUN=ROOT/'runner'; SEALED=ROOT/'sealed'; EV=ROOT/'evaluator'; RES=ROOT/'results'; RES.mkdir(exist_ok=True)
CFG=json.loads((EV/'gate22_config.json').read_text()); TH=CFG['pass_thresholds']

def mean(xs): return statistics.mean(xs) if xs else None

def candidate_metrics(c, full_task):
    exp={x['id'] for x in full_task.get('criteria',[])}; rows={x['criterion_id']:x for x in c.get('criteria',[])}
    vals=[1.0 if rows.get(cid,{}).get('pass') else 0.0 for cid in exp]
    omission_fail=sum(1 for cid in exp if (not rows.get(cid,{}).get('pass')) and rows.get(cid,{}).get('failure_type')=='omission')
    ver=[x for x in c.get('citations',[]) if x.get('verifiability')=='verified']
    cp=None
    if ver:
        cp=statistics.mean(1.0 if all(bool(x.get(k)) for k in ['source_exists','supports_claim','correct_jurisdiction_scope','temporally_valid']) else 0.0 for x in ver)
    return {
      'all_pass':1.0 if vals and all(v==1 for v in vals) else 0.0,
      'criterion_pass':statistics.mean(vals) if vals else 0.0,
      'criteria_passed':int(sum(vals)),'criteria_total':len(vals),
      'central_correctness':float(bool(c.get('central_conclusion_correct'))),
      'material_omission':float(bool(c.get('material_omission'))),
      'unsafe_hallucination':float(bool(c.get('unsafe_hallucination'))),
      'omission_criterion_count':omission_fail,
      'task_has_omission_failure':float(omission_fail>0 or bool(c.get('material_omission'))),
      'citation_precision':cp,'verified_citation_count':len(ver),
      'failure_stage':c.get('primary_failure_stage','other')
    }

def paired_boot(rows, metric, new='lrpe_v08', old='control', it=20000, seed=22022, stratum=None):
    rr=[r for r in rows if stratum is None or r['stratum']==stratum]
    diffs=[r[new][metric]-r[old][metric] for r in rr]
    if not diffs:return {'n':0,'delta':None,'ci95':[None,None]}
    rng=random.Random(seed); vals=[]
    for _ in range(it): vals.append(statistics.mean(rng.choice(diffs) for __ in diffs))
    vals.sort(); n=len(vals)
    return {'n':len(diffs),'delta':statistics.mean(diffs),'ci95':[vals[int(.025*n)],vals[min(n-1,int(.975*n))]]}

def mcnemar_exact(rows,new='lrpe_v08',old='control'):
    b=sum(1 for r in rows if r[new]['all_pass']==1 and r[old]['all_pass']==0)
    c=sum(1 for r in rows if r[new]['all_pass']==0 and r[old]['all_pass']==1)
    n=b+c
    if n==0:return {'lrpe_only_passes':b,'control_only_passes':c,'p_two_sided':1.0}
    k=min(b,c)
    # exact two-sided binomial under p=.5
    tail=sum(math.comb(n,i) for i in range(0,k+1))/(2**n)
    return {'lrpe_only_passes':b,'control_only_passes':c,'p_two_sided':min(1.0,2*tail)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('judge_results'); a=ap.parse_args(); jr=json.loads(Path(a.judge_results).read_text())
    key={x['judge_id']:x for x in json.loads((SEALED/'judge_key.json').read_text())}
    submissions={json.loads(p.read_text())['run_id']:json.loads(p.read_text()) for p in (RUN/'submissions').glob('*.json')}
    rows=[]
    for g in jr.get('groups',[]):
        kk=key[g['judge_id']]; task_id=kk['task_id']; full=json.loads((SEALED/'tasks'/task_id/'task.json').read_text())
        row={'judge_id':g['judge_id'],'task_id':task_id,'stratum':kk['stratum']}
        for lab in ['A','B']:
            cond=kk[lab]['condition']; m=candidate_metrics(g['candidates'][lab],full); s=submissions[kk[lab]['run_id']]
            m['word_count']=len(str(s.get('final_answer','')).split()); m['evidence_actions']=len(s.get('evidence_actions',[])); m['word_cap_ok']=float(m['word_count']<=CFG['answer_word_cap']); m['budget_ok']=float(m['evidence_actions']<=CFG['evidence_action_budget'])
            row[cond]=m
        rows.append(row)
    conds=['control','lrpe_v08']
    agg={}
    for c in conds:
        agg[c]={
          'all_pass':mean([r[c]['all_pass'] for r in rows]),
          'criterion_pass_macro':mean([r[c]['criterion_pass'] for r in rows]),
          'criterion_pass_micro':sum(r[c]['criteria_passed'] for r in rows)/sum(r[c]['criteria_total'] for r in rows),
          'central_correctness':mean([r[c]['central_correctness'] for r in rows]),
          'material_omission':mean([r[c]['material_omission'] for r in rows]),
          'task_omission_rate':mean([r[c]['task_has_omission_failure'] for r in rows]),
          'unsafe_hallucination':mean([r[c]['unsafe_hallucination'] for r in rows]),
          'mean_evidence_actions':mean([r[c]['evidence_actions'] for r in rows]),
          'budget_compliance':mean([r[c]['budget_ok'] for r in rows]),
          'word_cap_compliance':mean([r[c]['word_cap_ok'] for r in rows]),
          'verified_citations':sum(r[c]['verified_citation_count'] for r in rows)
        }
        cps=[]
        for r in rows:
            if r[c]['citation_precision'] is not None:
                # Aggregate per verified citation approximately by weighting each task's precision by checked count.
                cps.extend([r[c]['citation_precision']]*r[c]['verified_citation_count'])
        agg[c]['citation_precision']=mean(cps)
    deltas={m:paired_boot(rows,m) for m in ['all_pass','criterion_pass','central_correctness','material_omission','task_has_omission_failure','unsafe_hallucination']}
    strata={s:{'criterion_pass_delta':paired_boot(rows,'criterion_pass',stratum=s),'all_pass_delta':paired_boot(rows,'all_pass',stratum=s)} for s in sorted({r['stratum'] for r in rows})}
    new=agg['lrpe_v08']; old=agg['control']
    cp_rule=True; cp_testable=(new['verified_citations']>=10 and old['verified_citations']>=10 and new['citation_precision'] is not None and old['citation_precision'] is not None)
    if cp_testable: cp_rule=new['citation_precision']>=old['citation_precision']-TH['citation_precision_max_regression']
    extra_omissions=sum(r['lrpe_v08']['task_has_omission_failure'] for r in rows)-sum(r['control']['task_has_omission_failure'] for r in rows)
    rules={
      'task_wins_ge_losses':sum(1 for r in rows if r['lrpe_v08']['criterion_pass']-r['control']['criterion_pass']>0.001)>=sum(1 for r in rows if r['lrpe_v08']['criterion_pass']-r['control']['criterion_pass']<-0.001),
      'criterion_pass_gain':deltas['criterion_pass']['delta']>=TH['criterion_pass_delta_min'],
      'pure_research_noninferior':strata['pure_research']['criterion_pass_delta']['delta']>=TH['pure_research_criterion_delta_min'],
      'omission_cap':extra_omissions<=TH['max_extra_task_omissions'],
      'central_noninferior':new['central_correctness']>=old['central_correctness']-TH['central_correctness_max_regression'],
      'hallucination_noninferior':new['unsafe_hallucination']<=old['unsafe_hallucination']+TH['unsafe_hallucination_max_increase'],
      'citation_noninferior_if_testable':cp_rule,
      'budget_compliance':all(agg[c]['budget_compliance']>=TH['budget_compliance_rate'] for c in conds),
      'word_cap_compliance':all(agg[c]['word_cap_compliance']>=TH['word_cap_compliance_rate'] for c in conds)
    }
    strong=(deltas['criterion_pass']['ci95'][0] is not None and deltas['criterion_pass']['ci95'][0]>0)
    out={
      'gate':'22 - Held-out Fresh-Task Efficacy (v0.8)','benchmark':'Harvey LAB external subset','judge_model':jr.get('judge_model'),'n_unique_tasks':len(rows),
      'aggregate':agg,'paired_deltas_lrpe_minus_control':deltas,'strata':strata,'mcnemar_all_pass':mcnemar_exact(rows),
      'failure_stage_counts':{c:dict(Counter(r[c]['failure_stage'] for r in rows)) for c in conds},
      'extra_lrpe_tasks_with_omission_failure':extra_omissions,'citation_rule_testable':cp_testable,'pass_rules':rules,'PASS':all(rules.values()),
      'STRONG_EVIDENCE':strong,
      'interpretation':'PASS indicates held-out pilot efficacy of v0.8 on 20 unique, previously unused Harvey LAB tasks under preregistered margins. STRONG_EVIDENCE additionally requires the paired-task bootstrap 95% CI for criterion-pass delta to exclude zero. Neither is deployment certification.'
    }
    (RES/'gate22_summary.json').write_text(json.dumps(out,indent=2)); (RES/'gate22_scored_rows.json').write_text(json.dumps(rows,indent=2)); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
