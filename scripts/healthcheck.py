import sys
import urllib.request

url = sys.argv[1]
with urllib.request.urlopen(url, timeout=4) as response:
    if response.status >= 400:
        raise SystemExit(1)
print("ok")
