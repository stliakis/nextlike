import csv
import logging
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile
import argparse

import requests as requests

NEXTLIKE_HOST = "http://localhost:8045"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument(
    "-d",
    "--dataset",
    dest="dataset",
    default="small",
    help="The movielens dataset to load, either 'big' or 'small'",
)

args = parser.parse_args()

if args.dataset == "big":
    DATASET = "ml-latest"
else:
    DATASET = "ml-latest-small"

logger.log(logging.INFO, "Loading %s dataset" % DATASET)


def main():
    resp = urlopen(
        "https://files.grouplens.org/datasets/movielens/%s.zip" % DATASET
    )
    zipfile = ZipFile(BytesIO(resp.read()))
    print(zipfile.namelist())

    # requests.delete(f"{NEXTLIKE_HOST}/api/collection/items", json={"collection": "movielens"})
    # requests.delete(f"{NEXTLIKE_HOST}/api/collection/events", json={"collection": "movielens"})

    items_bucket = []
    with zipfile.open("%s/movies.csv" % DATASET) as file:
        for line in csv.reader(
                [
                    str(line)
                            .replace("\\r", "")
                            .replace("\\n", "")
                            .replace("b'", "")
                            .replace('b"', "")
                    for line in file.readlines()[1:]
                ]
        ):
            items_bucket.append(
                {
                    "id": line[0],
                    "fields": {"name": line[1], "genre": line[2].split("|")}
                }
            )

        print("finished")

    requests.post(f"{NEXTLIKE_HOST}/api/items", json={
        "collection": "movielens",
        "items": items_bucket
    })

    count = 0

    events_bucket = []

    with zipfile.open("%s/ratings.csv" % DATASET) as file:
        for line in csv.reader(
                [
                    str(line).replace("\\r", "").replace("\\n", "").replace("b'", "")
                    for line in file.readlines()[1:]
                ]
        ):

            if float(line[2]) >= 4:
                events_bucket.append(
                    {
                        "event": "like",
                        "person_id": line[0],
                        "item_id": line[1],
                    }
                )
                count += 1

            if len(events_bucket) >= 100000:
                response = requests.post(f"{NEXTLIKE_HOST}/api/events", json={
                    "collection": "movielens",
                    "events": events_bucket
                })
                print("flushing", response.text)
                events_bucket = []


if __name__ == "__main__":
    main()
