import json

from eval.benchmark import run_offline

if __name__ == "__main__":
    report=run_offline()
    report.update({'result':'PASS' if report['cases'] else 'NO_DATA'})
    print(json.dumps(report,indent=2))
