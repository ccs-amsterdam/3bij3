from urllib.request import urlopen
import csv
import elasticsearch

url = "https://raw.githubusercontent.com/vanatteveldt/wikinews/main/data/wikinews_2020.csv"

articles = csv.DictReader(urlopen(url).read().decode('utf-8').splitlines())


es = elasticsearch.Elasticsearch()
if es.indices.exists("inca"):
    print("Index 'inca' already exists, quitting")
    sys.exit(1)
    
es.indices.create("inca")

for i, article in enumerate(articles):
    es.create(id=i, index="inca", body=article)

    
