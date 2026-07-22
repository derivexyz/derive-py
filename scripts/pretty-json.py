import json
import sys

data = json.load(sys.stdin)
json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
sys.stdout.write("\n")
