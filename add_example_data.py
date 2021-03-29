"""
Add example data for 3bij3 app
"""
import argparse
import logging
import sys
from urllib.request import urlopen
import csv
import elasticsearch

parser = argparse.ArgumentParser(description=__doc__.strip())
parser.add_argument('index', nargs="?", default="inca", help="Destination elasticsearch index name (default: inca)")
parser.add_argument('--force', action='store_true', help="Add articles to index if exists (default: stops)")
parser.add_argument('--replace',  action='store_true', help="Replace index if it exists (default: stops)")
args = parser.parse_args()

#logging.basicConfig(level=logging.INFO, format='[%(asctime)s %(name)-12s %(levelname)-5s] %(message)s')
es = elasticsearch.Elasticsearch()
if es.indices.exists(args.index):
    if args.replace:
        print(f"Deleting and re-creating index {args.index!r}")
        es.indices.delete(args.index)
        es.indices.create(args.index)
    elif not args.force:
        print(f"Index {args.index!r} already exists, quitting")
        sys.exit(1)
else:
    print(f"Creating index {args.index!r}")
    es.indices.create(args.index)
url = "https://raw.githubusercontent.com/vanatteveldt/wikinews/main/data/wikinews_2020.csv"

articles = list(csv.DictReader(urlopen(url).read().decode('utf-8').splitlines()))

print(f"Adding {len(articles)} articles to index {args.index!r}")
for i, article in enumerate(articles):
    es.create(id=i, index="inca", body=article)

    
