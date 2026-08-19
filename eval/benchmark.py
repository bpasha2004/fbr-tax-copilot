"""Reproducible benchmark with an offline lexical baseline and optional live retriever."""
import json
import re
import statistics
import time
from pathlib import Path

from eval.metrics.retrieval import recall_at_k, reciprocal_rank

ROOT=Path(__file__).resolve().parent

def load_cases():
    rows=[]
    for p in sorted((ROOT/'datasets').glob('*.jsonl')):
        rows += [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
    return rows

def _terms(text): return {x.lower() for x in re.findall(r"[a-z0-9]{3,}", text)}

def lexical_baseline(cases):
    """Offline sanity benchmark: each case is evaluated against its declared evidence set.

    This is deliberately a correctness smoke test, not a claim of production RAG quality.
    Live Chroma benchmarking must be used for retrieval quality measurements.
    """
    results=[]; recalls=[]; mrr=[]; pool_sizes=[]
    for c in cases:
        candidates=[{"id":c['expected_rule'],"text":c['gold_context']}]+[{"id":f"DISTRACTOR_{c['id']}_{i}","text":x} for i,x in enumerate(c.get('distractors',[]))]
        q=_terms(c['question']); scored=sorted(candidates,key=lambda x:len(q&_terms(x['text'])),reverse=True)
        recalls.append(recall_at_k(scored,[c['expected_rule']],5)); mrr.append(reciprocal_rank(scored,[c['expected_rule']])); pool_sizes.append(len(candidates))
        results.append({'id':c['id'],'top':scored[0]['id']})
    return recalls,mrr,results,int(statistics.mean(pool_sizes))


def run_offline(retriever=None):
    cases=load_cases(); recalls,mrr,_,pool_size=lexical_baseline(cases)
    report={'cases':len(cases),'candidate_pool':pool_size,'baseline_recall_at_5':round(statistics.mean(recalls),4),'baseline_mrr':round(statistics.mean(mrr),4),'latency_ms_p50':0.0}
    if retriever:
        lat=[]; live_rec=[]; live_mrr=[]
        for c in cases:
            start=time.perf_counter(); got=retriever.retrieve(c['question'],top_k=5,taxpayer_type=c.get('taxpayer_type'),tax_year=c.get('tax_year')); lat.append((time.perf_counter()-start)*1000)
            ids=[{'id':x.citation} for x in got.get('chunks',[])]
            expected=[c.get('expected_citation','')] if c.get('expected_citation') else []
            if expected:
                live_rec.append(recall_at_k(ids,expected,5)); live_mrr.append(reciprocal_rank(ids,expected))
        report['live_recall_at_5']=round(statistics.mean(live_rec),4) if live_rec else None
        report['live_mrr']=round(statistics.mean(live_mrr),4) if live_mrr else None
        report['live_latency_ms_p50']=round(statistics.median(lat),2) if lat else None
    return report
