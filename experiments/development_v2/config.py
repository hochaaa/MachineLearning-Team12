"""Predeclared bounded V2 search. All selection is training-internal only."""
SEED=12
FOLDS=3
RELEVANCE=.7
TOP_K=10
CONTENT_GRID=[
 {'name':'v1_content','kind':'v1','mode':'rating'},
 *[{'name':f'split_a{a}','kind':'split','mode':'rating','accord_weight':a} for a in [.25,.5,.75]],
 {'name':'position_equal','kind':'position','mode':'rating','accord_weight':.5,'position_weights':[1,1,1]},
 {'name':'position_base','kind':'position','mode':'rating','accord_weight':.5,'position_weights':[2,3,5]},
 {'name':'neutral','kind':'split','mode':'neutral','accord_weight':.5},
 {'name':'centered','kind':'split','mode':'centered','accord_weight':.5},
 {'name':'position_neutral','kind':'position','mode':'neutral','accord_weight':.5,'position_weights':[2,3,5]},
]
MF_GRID=[{'name':'v1_mf','biased':False,'factors':4,'regularization':.01,'learning_rate':.01,'epochs':160,'early':False},
 *[{'name':f'bias_f{f}_r{r}','biased':True,'factors':f,'regularization':r,'learning_rate':.01,'epochs':120,'early':True} for f in [2,4,8,16] for r in [.01,.1]]]
HYBRID_GRID=[
 *[{'name':f'{method}_a{a}','method':method,'alpha':a} for method in ['linear','minmax','rrf'] for a in [.25,.5,.75]],
 {'name':'history','method':'history','alpha':.5},
]
FOLDIN_REG=[.01,.1,1.]
STABILITY_SEEDS=[29,47]
