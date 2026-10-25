"""Original NumPy Lloyd k-means on accord multi-hot; independent of recommender."""
from common import *
def distance2(x,c):
    """Squared Euclidean point-to-center matrix (nonnegative after roundoff)."""
    return np.maximum(np.sum(x*x,axis=1)[:,None]+np.sum(c*c,axis=1)[None,:]-2*x@c.T,0)

def kmeans(x,k,seed=12,n_init=3,max_iter=100,tol=1e-5):
    """kmeans++ weighted seeding, Lloyd means; empty centers reseed farthest point."""
    if not 1<k<=len(x) or len(np.unique(x,axis=0))<k:raise ValueError('Insufficient distinct features')
    best=None
    for run in range(n_init):
        rng=np.random.default_rng(seed+run);centers=[x[rng.integers(len(x))].copy()]
        for _ in range(1,k):
            d=distance2(x,np.asarray(centers)).min(axis=1)
            centers.append(x[rng.choice(len(x),p=d/d.sum())].copy())
        centers=np.asarray(centers);empties=0
        for iteration in range(max_iter):
            dist=distance2(x,centers);labels=dist.argmin(axis=1);new=[];reserved=set()
            for j in range(k):
                if np.any(labels==j):new.append(x[labels==j].mean(axis=0))
                else:
                    far=next(int(n) for n in np.argsort(-dist.min(axis=1),kind='stable') if n not in reserved)
                    reserved.add(far);new.append(x[far].copy());empties+=1
            new=np.asarray(new);shift=np.linalg.norm(new-centers);centers=new
            if shift<=tol:break
        dist=distance2(x,centers);labels=dist.argmin(axis=1);inertia=float(dist[np.arange(len(x)),labels].sum())
        result=(inertia,labels,centers,iteration+1,empties)
        if best is None or inertia<best[0]:best=result
    return best

def silhouette(x,labels):
    """Exact Euclidean silhouette for a fixed sample; singleton score0, undefined→None."""
    clusters=sorted(set(labels))
    if not 1<len(clusters)<len(x):return None
    distances=np.sqrt(distance2(x,x));np.fill_diagonal(distances,0);values=[]
    for n,l in enumerate(labels):
        same=labels==l;count=int(same.sum())
        if count==1:values.append(0.);continue
        a=distances[n,same].sum()/(count-1)
        b=min(float(distances[n,labels==other].mean()) for other in clusters if other!=l)
        values.append((b-a)/max(a,b) if max(a,b)>0 else 0.)
    return float(np.mean(values))

def main():
    catalog,raw=fragrantica(ROOT/'Term-project-datasets/fra_cleaned.csv')
    ids=sorted(catalog);vocab=sorted({t for r in catalog.values() for t in r['tokens'] if t.startswith('accord:')})
    index={t:n for n,t in enumerate(vocab)};x=np.zeros((len(ids),len(vocab)),dtype=np.float64)
    for n,i in enumerate(ids):
        for t in catalog[i]['tokens']:
            if t in index:x[n,index[t]]=1
    mask=x.sum(axis=1)>0;missing=int((~mask).sum());x=x[mask];ids=[i for i,ok in zip(ids,mask) if ok]
    rng=np.random.default_rng(12);sample=np.sort(rng.choice(len(x),min(800,len(x)),replace=False))
    results=[];models={}
    for k in [3,4,5,6,8]:
        inertia,labels,c,it,empty=kmeans(x,k)
        s=silhouette(x[sample],labels[sample]);models[k]=(labels,c)
        row={'clusters':k,'rows':len(x),'features':len(vocab),'silhouette_sample_n':len(sample),'sample_silhouette':s,'inertia':inertia,'iterations':it,'empty_reseeds':empty,'minimum_cluster_size':int(np.bincount(labels,minlength=k).min())}
        results.append(row);print(row,flush=True)
    chosen=max(results,key=lambda r:(r['sample_silhouette'],-r['clusters']));k=chosen['clusters'];labels,c=models[k]
    clusters=[];reps=[]
    for j in range(k):
        indices=np.flatnonzero(labels==j);order=sorted(range(len(vocab)),key=lambda n:(-c[j,n],vocab[n]))[:8]
        clusters.append({'cluster':j,'size':len(indices),'top_accords':'; '.join(f'{vocab[n]}={c[j,n]:.4f}' for n in order),'mean_squared_radius':float(np.mean(distance2(x[indices],c[j:j+1]))),'distinct_accord_patterns':len(np.unique(x[indices],axis=0))})
        rep=sorted(indices,key=lambda n:(float(distance2(x[n:n+1],c[j:j+1])[0,0]),ids[n]))[:5]
        for n in rep:reps.append({'cluster':j,'brand':catalog[ids[n]]['brand'],'name':catalog[ids[n]]['name'],'accords':'; '.join(t for t in catalog[ids[n]]['tokens'] if t.startswith('accord:')),'squared_distance_to_center':float(distance2(x[n:n+1],c[j:j+1])[0,0])})
    centered=x-x.mean(axis=0);cov=centered.T@centered;vals,vec=np.linalg.eigh(cov);order=np.argsort(vals)[::-1];axes=vec[:,order[:2]].copy()
    for j in range(2):
        if axes[np.abs(axes[:,j]).argmax(),j]<0:axes[:,j]*=-1
    coords=centered[sample]@axes;colors=['#2563a6','#cd6133','#25966b','#9253a1','#bd9519','#387f83','#c95586','#687381']
    lo=coords.min(axis=0);span=np.maximum(coords.max(axis=0)-lo,1e-12);xy=(coords-lo)/span
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="650"><rect width="100%" height="100%" fill="white"/><text x="25" y="30" font-family="sans-serif" font-size="20">Accord clusters: PCA projection of fixed 800-product sample</text><text x="25" y="55" font-family="sans-serif" font-size="12">Fragrantica metadata only; Euclidean multi-hot; seed12; projection is not original-space separation</text>']
    for (a,b),lab in zip(xy,labels[sample]):svg.append(f'<circle cx="{60+a*780}" cy="{590-b*490}" r="3" opacity="0.55" fill="{colors[lab]}"/>')
    svg.extend(['<text x="420" y="635" font-family="sans-serif">PC1</text><text x="10" y="320" font-family="sans-serif">PC2</text>','</svg>'])
    (OUT/'figures/kmeans_pca.svg').write_text(''.join(svg))
    table('kmeans_grid.csv',results);table('kmeans_clusters.csv',clusters);table('kmeans_representatives.csv',reps)
    save('kmeans_summary.json',{'selected':chosen,'missing_all_accords_excluded':missing,'seed':12,'n_init':3,'max_iter':100,'tol':1e-5,'selection':'highest silhouette on fixed800 sample; unsupervised, no rating labels','size_sum':sum(r['size'] for r in clusters),'pca_explained_fraction':[float(v/vals.sum()) for v in vals[order[:2]]],'visualization_sample_n':len(coords),'visualization_sample_equals_silhouette_sample':True,'feature_space':'unscaled accord multi-hot (top5 available); no recommender TFIDF changes'})
    bar('kmeans_sizes.svg','Exploratory Fragrantica accord cluster sizes',[f"Cluster {r['cluster']}" for r in clusters],[r['size'] for r in clusters],f'All nonempty accord vectors; k={k}; seed12; not recommendation performance')
    bar('kmeans_silhouette.svg','K-means silhouette on fixed sample',[str(r['clusters']) for r in results],[r['sample_silhouette'] for r in results],'Euclidean distances; n=800; seed12; top5 accord multi-hot')
if __name__=='__main__':main_run(main,'kmeans_analysis')
