from math import log2

def recall_at_k(results, expected, k=5):
    got={r.get("id") if isinstance(r,dict) else getattr(r,"id",None) for r in results[:k]}
    exp=set(expected); return len(got&exp)/len(exp) if exp else 0.0

def reciprocal_rank(results, expected):
    exp=set(expected)
    for i,r in enumerate(results,1):
        rid=r.get("id") if isinstance(r,dict) else getattr(r,"id",None)
        if rid in exp: return 1.0/i
    return 0.0

def ndcg_at_k(relevances, k=5):
    rel=relevances[:k]
    dcg=sum((2**x-1)/log2(i+2) for i,x in enumerate(rel))
    ideal=sorted(rel,reverse=True); idcg=sum((2**x-1)/log2(i+2) for i,x in enumerate(ideal))
    return dcg/idcg if idcg else 0.0
