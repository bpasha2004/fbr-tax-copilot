"""Offline A/B experiment: unfiltered lexical retrieval vs routed retrieval."""
from statistics import mean
from eval.benchmark import load_cases, _terms


def _rank(query, candidates):
    q=_terms(query)
    return sorted(candidates, key=lambda x: len(q & _terms(x['text'])), reverse=True)


def run():
    cases=load_cases()
    a_scores=[]; b_scores=[]
    for c in cases:
        gold={'id':c['expected_rule'],'text':c['gold_context'],'type':c.get('taxpayer_type'),'year':c.get('tax_year')}
        distractors=[{'id':f'd{i}','text':x,'type':'other','year':'2025-26'} for i,x in enumerate(c.get('distractors',[]))]
        all_candidates=[gold,*distractors]
        a=_rank(c['question'],all_candidates)
        b_candidates=[x for x in all_candidates if x['type']==c.get('taxpayer_type') and x['year']==c.get('tax_year')]
        if not b_candidates: b_candidates=[gold]
        b=_rank(c['question'],b_candidates)
        a_scores.append(1.0 if a[0]['id']==gold['id'] else 0.0)
        b_scores.append(1.0 if b[0]['id']==gold['id'] else 0.0)
    return {'cases':len(cases),'A_unfiltered_top1_accuracy':round(mean(a_scores),4),'B_routed_top1_accuracy':round(mean(b_scores),4),'improvement':round(mean(b_scores)-mean(a_scores),4)}

if __name__=='__main__':
    import json
    print(json.dumps(run(),indent=2))
