from eval.benchmark import load_cases, run_offline
def test_benchmark_has_50_cases(): assert len(load_cases())>=50
def test_offline_benchmark_runs():
    report=run_offline(); assert report["cases"]>=50; assert "baseline_recall_at_5" in report; assert report["baseline_recall_at_5"] >= 0.90
    assert report["candidate_pool"] >= 4
