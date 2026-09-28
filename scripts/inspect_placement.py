"""Summarize real ORT node events; provider presence alone proves nothing.
python scripts/inspect_placement.py reports/qnn-profile/ort_....json
Pair this report with worker environment.json + detailed QNN HTP CSV evidence.
"""
import argparse
import collections
import json
from pathlib import Path


def inspect(path):
    events=json.loads(Path(path).read_text())
    providers=collections.Counter();durations=collections.defaultdict(float)
    for e in events:
        provider=e.get('args',{}).get('provider')
        if provider and e.get('cat')=='Node' and e.get('name','').endswith('_kernel_time'):
            providers[provider]+=1;durations[provider]+=e.get('dur',0)/1000
    qnn=providers.get('QNNExecutionProvider',0)
    cpu=providers.get('CPUExecutionProvider',0)
    return {'profile':str(path),'executed_node_event_counts':dict(providers),'node_total_ms':dict(durations),
            'qnn_node_execution_observed':qnn>0,'cpu_fallback_events':cpu,
            'all_recorded_node_events_qnn':bool(qnn and not cpu and len(providers)==1),
            'npu_claim_requires':'Actual Snapdragon device metadata, strict QNN HTP backend configuration, and detailed QNN profiling evidence; this script alone is insufficient.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('profile');p.add_argument('--output');a=p.parse_args();report=inspect(a.profile)
    if a.output:Path(a.output).write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
