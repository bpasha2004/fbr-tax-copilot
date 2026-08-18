"""Small dependency-free Prometheus-style metrics registry."""
from collections import Counter, defaultdict
from threading import Lock

_lock = Lock()
_counters = Counter()
_histograms: dict[str, list[float]] = defaultdict(list)


def inc(name: str, value: int = 1, **labels):
    key = _label_key(name, labels)
    with _lock:
        _counters[key] += value


def observe(name: str, value: float, **labels):
    key = _label_key(name, labels)
    with _lock:
        values = _histograms[key]
        values.append(float(value))
        if len(values) > 1000:
            del values[:-1000]


def _label_key(name, labels):
    if not labels:
        return name
    suffix = ",".join(f'{k}="{str(v).replace(chr(34), chr(39))}"' for k, v in sorted(labels.items()))
    return f"{name}{{{suffix}}}"


def prometheus_text() -> str:
    lines=[]
    with _lock:
        for key, value in sorted(_counters.items()):
            lines.append(f"{key} {value}")
        for key, values in sorted(_histograms.items()):
            if values:
                ordered=sorted(values)
                p50=ordered[len(ordered)//2]
                lines.append(f"{key}_count {len(values)}")
                lines.append(f"{key}_p50 {p50:.3f}")
    return "\\n".join(lines) + "\\n"
