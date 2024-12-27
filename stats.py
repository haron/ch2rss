import json
import re
from collections import Counter
from pathlib import Path

import redis
from configargparse import ArgumentDefaultsRawHelpFormatter, ArgumentParser
from pygtail import Pygtail

p = ArgumentParser(auto_env_var_prefix="STATS_", formatter_class=ArgumentDefaultsRawHelpFormatter)
p.add("--log", help="log file to parse", default="/var/log/nginx/ch2rss.fflow.net-access.log")
p.add("--redis-url", help="Redis address", default="redis://localhost")
p.add("--redis-prefix", help="Redis key prefix", default="ch2rss_")
p.add("--offset-dir", help="Offset file directory", default="/var/tmp")
p.add("--out-json", help="Save all-time stats to JSON file", default="/var/www/ch2rss-prod/public/stats.json")
args = p.parse_args()

offset_file = Path(args.offset_dir) / (re.sub(r"\W", "-", args.log.strip("/")) + ".offset")
log_reader = Pygtail(args.log, offset_file=offset_file)
redis_client = redis.Redis.from_url(args.redis_url)


def read_log(reader):
    for line in reader:
        res = re.findall(r'.*"GET /(\w+)(\?\S*)? HTTP/[\.\d]+" 200 ', line)
        if res and res[0]:
            yield res[0][0]


def process_log():
    counter = Counter()
    for channel in read_log(log_reader):
        counter[channel] += 1
    counter["_total"] = sum(counter.values())
    for k, v in counter.items():
        redis_client.incr(f"{args.redis_prefix}{k}", v)
    stats = {
        "total_hits": int(redis_client.get(f"{args.redis_prefix}_total")),
        "channels": len(redis_client.keys(f"{args.redis_prefix}*")),
    }
    with open(args.out_json, "w") as out:
        out.write(json.dumps(stats))


if __name__ == "__main__":
    process_log()
