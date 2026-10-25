"""STEP 2 functional checks only. No fitting, tuning, held-out evaluation or metric imports.

Existing-user check reads development TRAIN privately and emits aggregate assertions only.
Public demo checks use separate synthetic ratings. Fault injection uses temporary mirrors.
Run separately from the historical unittest suite (which contains fit-based tests).
"""
import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from perfume.data import fragrantica
from perfume.frozen import load_frozen,score_frozen
from perfume.models import Content,MatrixFactorization,Baseline,hybrid,knowledge
from perfume.improvements import BiasedMatrixFactorization


def read(path):
    """Local JSON helper; only TRAIN, saved models, public metadata and synthetic fixtures."""
    return json.loads(Path(path).read_text())


def main():
    output=ROOT/'outputs/functional'
    output.mkdir(exist_ok=True)
    cases=[];index=0
    def record(phase,name,status,actual,execution=True,processing='정상 처리',seconds=None):
        nonlocal index
        index+=1
        cases.append({'case':f'F{index:02d}','phase':phase,'name':name,'status':status,
                      'executed':execution,'processing':processing,'actual':actual,'seconds':seconds})
    environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
    with ExitStack() as stack:
        # An unexpected training call fails the functional run instead of changing model state.
        for cls in [Content,MatrixFactorization,BiasedMatrixFactorization,Baseline]:
            stack.enter_context(patch.object(cls,'fit',side_effect=AssertionError('Fitting prohibited during functional checks')))
        freeze,mf,content,baseline=load_frozen(ROOT/'outputs/final')
        candidates=read(ROOT/freeze['candidates_path'])
        catalog,_=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv')
        qa={name:hashlib.sha256(getattr(mf,name).tobytes()).hexdigest() for name in ['P','Q']}
        frozen_memory={'counts':dict(baseline.counts),'idf':dict(content.idf)}
        train=read(ROOT/freeze['train_path'])
        user=sorted({u for u,_,_ in train})[0]
        private_support=[(i,r) for u,i,r in train if u==user]
        pool=[i for i in candidates if i not in {j for j,_ in private_support}]
        component_scores={'content':content.score(private_support,pool),'mf':mf.score(user,pool)}
        component_scores['hybrid']=hybrid(component_scores['content'],component_scores['mf'],freeze['selected']['alpha'],baseline.score(pool))
        for k in [5,10]:
            predictions=score_frozen(private_support,candidates,mf,content,baseline,freeze['selected']['alpha'],k,user=user)
            for method in ['content','mf','hybrid']:
                ranked=predictions[method]
                scored={i:s for i,s in zip(pool,component_scores[method])}
                ok=(len(ranked)==k and len(set(ranked))==k and not set(ranked)&{i for i,_ in private_support}
                    and all(np.isfinite(scored[i]) for i in ranked)
                    and all(scored[a]>=scored[b] for a,b in zip(ranked,ranked[1:])))
                record('library','existing_user_'+method+f'_top{k}','PASS' if ok else 'FAIL',
                       {'alias':'기존 사용자 시나리오 A','train_history_loaded':True,'count':len(ranked),
                        'duplicate_seen_nonfinite_or_sort_violations':not ok})
        # Unknown existing users are explicitly unscorable in pure MF, not a valid existing-user lookup.
        unknown=mf.score('SYNTHETIC_NONEXISTENT_PRESENTATION_USER',candidates)
        record('library','unknown_user_mf','PASS' if np.isnan(unknown).all() else 'FAIL',
               'Pure MF returns NaN for unknown ID; CLI does not expose ID lookup.',processing='내부 함수의 명시적 비점수 처리')
        support_a=read(ROOT/'demos/stage2/synthetic_woody.json')
        support_b=read(ROOT/'demos/stage2/synthetic_floral.json')
        vec_a=mf.fold_in(support_a);vec_b=mf.fold_in(support_b)
        record('library','synthetic_new_user_fold_in','PASS' if vec_a is not None and np.isfinite(vec_a).all() else 'FAIL',
               {'synthetic':True,'estimated_user_coordinates':len(vec_a),'known_support_factors':sum(i in mf.items for i,_ in support_a),
                'item_factor_array_writeable':bool(mf.Q.flags.writeable)})
        ranks_a=score_frozen(support_a,candidates,mf,content,baseline,freeze['selected']['alpha'],5)
        ranks_b=score_frozen(support_b,candidates,mf,content,baseline,freeze['selected']['alpha'],5)
        changed=(ranks_a['hybrid']!=ranks_b['hybrid'])
        record('library','synthetic_input_changes_recommendations','PASS' if changed and not np.allclose(vec_a,vec_b) else 'FAIL',
               {'top5_changed':changed,'new_user_vector_changed':not np.allclose(vec_a,vec_b),'synthetic':True})
        p=[i for i in candidates if i not in {j for j,_ in support_a}]
        c=content.score(support_a,p);m=mf.score_vector(vec_a,p);s=hybrid(c,m,freeze['selected']['alpha'],baseline.score(p))
        for token in ['accord:woody','accord:floral','note:rose']:
            rows=knowledge(catalog,p,s,required=[token])[:5]
            ok=bool(rows) and all(token in catalog[i]['tokens'] for i,_,_ in rows) and all(a[1]>=b[1] for a,b in zip(rows,rows[1:]))
            record('library','knowledge_'+token,'PASS' if ok else 'FAIL',
                   {'returned':len(rows),'all_satisfy_required_token':ok,'sorted_descending':all(a[1]>=b[1] for a,b in zip(rows,rows[1:]))})
        record('library','frozen_arrays_after_function_calls','PASS' if all(hashlib.sha256(getattr(mf,n).tobytes()).hexdigest()==h for n,h in qa.items()) and dict(baseline.counts)==frozen_memory['counts'] and content.idf==frozen_memory['idf'] else 'FAIL',
               'P/Q bytes, train popularity and IDF unchanged; fit calls patched to fail in library checks.')
    with tempfile.TemporaryDirectory(prefix='team12-functional-fixtures-',dir='/private/tmp') as td:
        temp=Path(td)
        def fixture(name,value):
            p=temp/name;p.write_text(json.dumps(value));return p
        def execute(script,support=None,flags=(),cwd=ROOT):
            command=[sys.executable,'-B',str(ROOT/'scripts'/script)]
            if support is not None:command+=['--support',str(support)]
            command+=list(flags);started=time.monotonic()
            cp=subprocess.run(command,cwd=cwd,env=environment,capture_output=True,text=True,timeout=60)
            return cp,round(time.monotonic()-started,3)
        def cli_case(name,support,flags=(),expected='normal',script='demo_frozen.py',cwd=ROOT,phase='original_cli'):
            cp,elapsed=execute(script,support,flags,cwd)
            traceback='Traceback (most recent call last)' in cp.stderr
            parsed=None
            if expected in ['normal','few','empty']:
                try:parsed=json.loads(cp.stdout)
                except json.JSONDecodeError:pass
                rows=parsed.get('results',[]) if isinstance(parsed,dict) else []
                ok=cp.returncode==0 and parsed is not None
                if expected=='normal':ok=ok and len(rows)==int(flags[flags.index('--k')+1]) if '--k' in flags else ok and len(rows)==10
                if expected=='few':ok=ok and 0<len(rows)<5
                if expected=='empty':ok=ok and not rows
            elif expected=='reject':ok=cp.returncode!=0 and not traceback and bool(cp.stderr.strip())
            elif expected=='unsupported':ok=cp.returncode==2 and 'unrecognized arguments' in cp.stderr
            elif expected=='text_empty':ok=cp.returncode==0 and '추천 가능한 향수가 없습니다' in cp.stdout
            elif expected=='text_few':ok=cp.returncode==0 and '개만 추천할 수 있습니다' in cp.stdout
            elif expected=='text_normal':ok=cp.returncode==0 and '1.' in cp.stdout
            elif expected=='empty_fallback':
                try:parsed=json.loads(cp.stdout)
                except json.JSONDecodeError:pass
                ok=cp.returncode==0 and len(parsed.get('results',[]))==5
            status='NOT SUPPORTED' if expected=='unsupported' and ok else 'PASS' if ok else 'FAIL'
            processing='현재 CLI에서 지원하지 않는 입력 방식' if status=='NOT SUPPORTED' else '비정상 종료/traceback' if traceback else '명확한 오류 메시지 출력' if cp.returncode else '정상 처리'
            actual={'exit_code':cp.returncode,'traceback':traceback,'stdout_type':'JSON' if parsed else 'text',
                    'stderr_tail':cp.stderr.strip().splitlines()[-1] if cp.stderr.strip() else '',
                    'returned':len(parsed['results']) if isinstance(parsed,dict) and 'results' in parsed else None}
            record(phase,name,status,actual,processing=processing,seconds=elapsed)
            # Outputs here contain synthetic examples only, never the private existing user history.
            (output/(cases[-1]['case']+'_'+name.replace(':','_')+'.stdout.txt')).write_text(cp.stdout)
            (output/(cases[-1]['case']+'_'+name.replace(':','_')+'.stderr.txt')).write_text(cp.stderr)
            return parsed,cp
        a=ROOT/'demos/stage2/synthetic_woody.json';b=ROOT/'demos/stage2/synthetic_floral.json'
        for k in [5,10]:cli_case('synthetic_hybrid_top'+str(k),a,['--k',str(k)])
        for token in ['accord:woody','accord:floral','note:rose']:
            payload,_=cli_case('required_'+token,a,['--k','5','--required',token])
            assert payload and all(token in catalog[r['item']]['tokens'] for r in payload['results'])
        nohistory=fixture('empty.json',[]);one=fixture('one.json',[support_a[0]])
        cli_case('empty_history_fallback',nohistory,['--k','5'],expected='empty_fallback')
        cli_case('one_support_fold_in',one,['--k','5'])
        counts=Counter(t for i in p for t in catalog[i]['tokens'])
        rare=sorted(t for t,n in counts.items() if n==1)[0]
        cli_case('valid_rule_fewer_than_five',a,['--k','5','--required',rare],expected='few')
        cli_case('valid_rules_no_candidates',a,['--k','5','--required','accord:woody','--forbidden','accord:woody'],expected='empty')
        bads={
          'unknown_perfume_name':[['SYNTHETIC_UNKNOWN_PERFUME',.8]],
          'out_of_range_high':[[support_a[0][0],1.5]],'out_of_range_low':[[support_a[0][0],-.1]],
          'nonnumeric_rating':[[support_a[0][0],'high']],
          'duplicate_perfume':[support_a[0],support_a[0]],
          'boolean_rating':[[support_a[0][0],True]],'malformed_input_row':[[support_a[0][0]]],
          'nonfinite_rating':[[support_a[0][0],float('nan')]]}
        bad_paths={name:fixture(name+'.json',value) for name,value in bads.items()}
        for name,path in bad_paths.items():cli_case(name,path,expected='reject')
        cli_case('unknown_required_token',a,['--required','accord:SYNTHETIC_UNKNOWN'],expected='reject')
        for k in ['0','-2']:cli_case('invalid_k_'+k,a,['--k',k],expected='reject')
        malformed=temp/'invalid_json.json';malformed.write_text('{invalid JSON')
        cli_case('malformed_json',malformed,expected='reject')
        cli_case('missing_support_file',temp/'not_here.json',expected='reject')
        cli_case('unknown_user_id_flag',a,['--user-id','SYNTHETIC_UNKNOWN_USER'],expected='unsupported')
        cli_case('model_selection_flag',a,['--method','content'],expected='unsupported')
        # Only the help branch of legacy demo.py is safe: its body fits Content/Baseline.
        cp,elapsed=execute('demo.py',flags=['--help'])
        record('original_cli','legacy_help','PASS' if cp.returncode==0 else 'FAIL','Help read only; model body not run.',seconds=elapsed)
        record('original_cli','legacy_demo_body','NOT SUPPORTED','Not executed: legacy demo.py calls Content.fit/Baseline.fit and uses historical wider catalog. Prohibited for this frozen-demo check.',execution=False,processing='이번 단계 제한상 미실행')
        # Missing/corrupt model and missing catalog: fault mirrors never touch the originals.
        mirrors={}
        for name,omit,corrupt in [('missing_catalog','Term-project-datasets/fra_cleaned.csv',False),
                                  ('missing_model','outputs/final/model.npz',False),
                                  ('corrupt_model','outputs/final/model.npz',True)]:
            mirror=temp/name;mirror.mkdir()
            for relative in ['outputs/final/freeze.json',*freeze['protected_sha256']]:
                if relative==omit:continue
                dst=mirror/relative;dst.parent.mkdir(parents=True,exist_ok=True);dst.symlink_to(ROOT/relative)
            if corrupt:
                dst=mirror/omit;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b'SYNTHETIC CORRUPT MODEL FOR FUNCTIONAL CHECK ONLY')
            mirrors[name]=mirror
            cli_case(name,a,['--k','5'],expected='reject',cwd=mirror)
        # Presentation wrapper: same frozen CLI, friendlier failures/output, no scoring changes.
        wrapper='presentation_demo.py'
        for name,path in bad_paths.items():cli_case(name,path,expected='reject',script=wrapper,phase='presentation_wrapper')
        for name,flags in [('unknown_required_token',['--required','accord:SYNTHETIC_UNKNOWN']),('zero_k',['--k','0']),('negative_k',['--k','-2'])]:
            cli_case(name,a,flags,expected='reject',script=wrapper,phase='presentation_wrapper')
        for name,path in [('malformed_json',malformed),('missing_support_file',temp/'not_here.json')]:
            cli_case(name,path,expected='reject',script=wrapper,phase='presentation_wrapper')
        for name,mirror in mirrors.items():
            cli_case(name,a,['--project-root',str(mirror)],expected='reject',script=wrapper,phase='presentation_wrapper')
        cp,elapsed=execute(wrapper,a,['--k','5'],cwd=temp)
        record('presentation_wrapper','run_from_different_directory','PASS' if cp.returncode==0 and '1.' in cp.stdout else 'FAIL',
               {'exit_code':cp.returncode,'uses_project_relative_script_root':True},seconds=elapsed)
        (output/'presentation_top5.txt').write_text(cp.stdout)
        for token in ['accord:woody','accord:floral','note:rose']:
            _,cp=cli_case('required_'+token,a,['--required',token,'--k','5'],expected='text_normal',script=wrapper,phase='presentation_wrapper')
        cli_case('few_results_message',a,['--required',rare,'--k','5'],expected='text_few',script=wrapper,phase='presentation_wrapper')
        cli_case('empty_results_message',a,['--required','accord:woody','--forbidden','accord:woody'],expected='text_empty',script=wrapper,phase='presentation_wrapper')
        cp,_=execute(wrapper,nohistory,['--k','5'])
        record('presentation_wrapper','empty_history_disclosed_fallback','PASS' if cp.returncode==0 and '개인화 추천이 아닙니다' in cp.stdout else 'FAIL',
               {'exit_code':cp.returncode,'explicit_popularity_fallback_notice':'개인화 추천이 아닙니다' in cp.stdout})
        original,_=execute('demo_frozen.py',a,['--k','5'])
        wrapped,_=execute(wrapper,a,['--k','5','--json'])
        record('presentation_wrapper','same_json_as_original_frozen_cli','PASS' if original.returncode==wrapped.returncode==0 and json.loads(original.stdout)==json.loads(wrapped.stdout) else 'FAIL',
               'Parsed JSON identical; no scoring or candidate change introduced by wrapper.')
        # Explanations: lexical overlap and constraint flags only, no invented latent-factor causality.
        payload=json.loads(original.stdout)
        ok=all(all(t in catalog[row['item']]['tokens'] and any(t in catalog[i]['tokens'] for i,_ in support_a) for t in row['explanation']['shared_tokens']) for row in payload['results'])
        record('presentation_wrapper','displayed_shared_tokens_are_real_metadata_overlap','PASS' if ok else 'FAIL',
               'Overlap is descriptive metadata, not an MF factor explanation or preference accuracy metric.')
    # Validate saved synthetic output contracts without another inference run.
    checked=0;contracts_ok=True
    for case in list(cases):
        if case['phase']!='original_cli' or case['status']!='PASS':continue
        files=list(output.glob(case['case']+'_*.stdout.txt'))
        if not files:continue
        try:document=json.loads(files[0].read_text())
        except json.JSONDecodeError:continue
        if 'results' not in document:continue
        entries=document['results'];items=[r['item'] for r in entries]
        seen=set() if case['name']=='empty_history_fallback' else {support_a[0][0]} if case['name']=='one_support_fold_in' else {i for i,_ in support_a}
        contracts_ok=contracts_ok and len(items)==len(set(items)) and not set(items)&seen
        contracts_ok=contracts_ok and all(isinstance(r['score'],(int,float)) and math.isfinite(r['score']) and r['name'] and r['brand'] and isinstance(r['explanation'],dict) for r in entries)
        contracts_ok=contracts_ok and all(a['score']>=b['score'] for a,b in zip(entries,entries[1:]))
        checked+=1
    record('output_contract','saved_synthetic_output_contract','PASS' if contracts_ok else 'FAIL',
           {'payloads_checked':checked,'unique_unseen_finite_sorted':contracts_ok,'name_brand_score_explanation_present':contracts_ok},
           processing='저장된 합성 시연 출력 검사')
    floral_cp,floral_seconds=execute('presentation_demo.py',ROOT/'demos/stage2/synthetic_floral.json',['--k','5'])
    floral_ok=floral_cp.returncode==0 and '1.' in floral_cp.stdout and 'MF factor가 있는 입력 3개' in floral_cp.stdout
    record('presentation_wrapper','synthetic_floral_example_top5','PASS' if floral_ok else 'FAIL',
           {'synthetic':True,'top5_displayed':floral_ok,'known_support_factors':3},seconds=floral_seconds)
    (output/'presentation_floral_top5.txt').write_text(floral_cp.stdout)
    (output/'presentation_floral_top5.stderr.txt').write_text(floral_cp.stderr)
    phase_counts={phase:dict(Counter(r['status'] for r in cases if r['phase']==phase)) for phase in sorted({r['phase'] for r in cases})}
    payload={'purpose':'Functional inference checks only; synthetic public demo inputs; no held-out evaluation or fitting',
             'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),
             'cases':cases,'total':len(cases),'executed':sum(r['executed'] for r in cases),'counts':dict(Counter(r['status'] for r in cases)),
             'by_phase':phase_counts,'rare_constraint_for_few_results':rare,
             'prohibited_train_eval_calls_invoked':False}
    (output/'results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:payload[key] for key in ['purpose','total','executed','counts','by_phase']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
