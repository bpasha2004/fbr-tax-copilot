from eval.ab import run

def test_ab_experiment_is_reproducible():
    r=run(); assert r['cases'] >= 50; assert r['B_routed_top1_accuracy'] >= r['A_unfiltered_top1_accuracy']
