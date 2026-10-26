"""Read-only actual-fit/cache/mapping/boundary verification; zero MF fits."""
import json,re
import numpy as np
from v3_data import ROOT,OUT,load_train,digest,save,guard,sha
from v3_config import SETTINGS
from split import outer_specs,inner_specs,known_split
from data import inner_stop

def main():
    guard();path=OUT/'diagnostics/fit_ledger.json';before=sha(path);ledger=json.loads(path.read_text());train,pool,cat,raw=load_train();outer={o:(fit,held) for o,fit,held in outer_specs(train)};records=ledger['records'];bykey={r['key']:r for r in records}
    assert len(records)==ledger['total']==sum(ledger['counts'].values())<=61
    assert all(ledger['counts'][k]<=SETTINGS['caps'][k] for k in ['primary','seed','final'])
    assert all(r['status']=='completed' and r['observed_calls']==1 for r in records)
    verified=0
    for r in records:
        tag=r['tag'];seed=r['seed'];base=None;held=set()
        if tag.startswith('fulltrain/'):base=train
        elif tag.startswith('known'):
            o=int(re.match(r'known(\d+)',tag).group(1));base,_=known_split(outer[o][0],o);held=outer[o][1]
        else:
            match=re.search(r'outer(\d+)',tag);assert match,tag;o=int(match.group(1));base=outer[o][0];held=set(outer[o][1])
            im=re.search(r'/inner(\d+)/',tag)
            if im:
                ii=int(im.group(1));_,base,ih=next(s for s in inner_specs(base,o) if s[0]==ii);held|=ih
        stop=()
        if tag.endswith('/nested_stop'):base,stop=inner_stop(base,seed)
        assert not held&{u for u,_,_ in base},tag
        assert digest(base)==r['training_digest'] and digest(stop)==r['stop_digest'],tag
        directory=OUT/'models/cache'/r['key'];meta=json.loads((directory/'metadata.json').read_text())
        assert set(meta['users'])=={u for u,_,_ in base} and set(meta['items'])=={i for _,i,_ in base}
        assert set(meta['users'].values())==set(range(len(meta['users']))) and set(meta['items'].values())==set(range(len(meta['items'])))
        with np.load(directory/'weights.npz',allow_pickle=False) as weights:
            assert weights['P'].shape[0]==len(meta['users']) and weights['Q'].shape[0]==len(meta['items'])
            assert all(np.isfinite(weights[k]).all() for k in weights.files)
        verified+=1
    for reuse in ledger['cache_reuses']:
        original=bykey[reuse['key']];assert reuse['training_digest']==original['training_digest'] and reuse['stop_digest']==original['stop_digest']
    assert before==sha(path)
    save('diagnostics/post_checks.json',{'actual_mf_entries':len(records),'phase_counts':ledger['counts'],'cache_hits_verified':len(ledger['cache_reuses']),'cached_model_mappings_checked':verified,'train_user_boundaries_and_row_digests_match':True,'seed_and_configuration_in_cache_key':True,'all_weights_finite':True,'fit_ledger_unchanged':True,'new_mf_fits':0})
    print('POST CHECK PASS:',verified,'real fit models; cache',len(ledger['cache_reuses']),'exact digests; no MF fit.')
if __name__=='__main__':main()
