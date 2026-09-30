"""Compare runs on common, error-free scenario sets."""
import glob, json, math, os, sys
from collections import defaultdict


def load(d):
    R = {}
    for l in open(os.path.join(d, "results.jsonl")):
        r = json.loads(l)
        if not r["error"]:
            R[r["id"]] = r
    return R


def wilson(k, n, z=1.959964):
    p = k / n; c = (p + z*z/(2*n)) / (1 + z*z/n); h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return 100*(c-h), 100*(c+h)


def mcnemar(a, b, ids):
    b01 = sum(1 for i in ids if not a[i]["passed"] and b[i]["passed"])
    b10 = sum(1 for i in ids if a[i]["passed"] and not b[i]["passed"])
    n = b01 + b10
    if n == 0:
        return b01, b10, 1.0
    k = min(b01, b10)
    p = sum(math.comb(n, j) for j in range(0, k + 1)) / 2 ** n * 2
    return b01, b10, min(1.0, p)


if __name__ == "__main__":
    dirs = sys.argv[1:]
    runs = {os.path.basename(d.rstrip("/")): load(d) for d in dirs}
    common = sorted(set.intersection(*[set(v) for v in runs.values()]))
    print("common scenarios:", len(common))
    for k, v in runs.items():
        p = sum(v[i]["passed"] for i in common); lo, hi = wilson(p, len(common))
        lat = sum(v[i]["latency"] for i in common) / len(common)
        tok = sum(v[i]["usage"]["input_tokens"] + v[i]["usage"]["output_tokens"] for i in common) / len(common)
        print(f"{k:34s} {p:3d}/{len(common)} {100*p/len(common):5.1f}%  CI[{lo:4.1f},{hi:4.1f}]  score {sum(v[i]['score'] for i in common)/len(common):.3f}  lat {lat:5.1f}s  tok/scn {tok/1000:5.1f}k")
