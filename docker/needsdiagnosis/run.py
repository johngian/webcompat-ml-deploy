import argparse
import json
import os
import pandas
import subprocess
import tempfile
import urllib.request

import boto3

from elasticsearch import ElasticSearch


MODEL_PATH = "/srv/model.bin"
PREDICTION_PATH = "/srv/predictions.csv"
JSON_OUTPUT_PATH = "/srv/predictions.json"
S3_RESULTS_ML_BUCKET = os.environ.get("S3_RESULTS_ML_BUCKET")
ES = ElasticSearch(os.environ.get("ES_URL"))
ES_INDEX = os.environ.get("ES_INDEX")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run webcompat ML task.")
    parser.add_argument("--issue-url", action="store", dest="issue_url")
    args = parser.parse_args()

    with urllib.request.urlopen(args.issue_url) as response:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            data = json.load(response)
            issue = {"body": data["body"], "title": data["title"]}
            df = pandas.DataFrame([issue])

            df.to_csv(tmp_file.name, index=False)

            command = [
                "webcompat-ml-needsdiagnosis",
                "predict",
                "--data",
                tmp_file.name,
                "--model",
                MODEL_PATH,
                "--output",
                PREDICTION_PATH,
            ]
            subprocess.run(command, check=True)

    df = pandas.read_csv(PREDICTION_PATH)
    df.to_json(JSON_OUTPUT_PATH, index=False, orient="split")

    s3 = boto3.client("s3")
    issue_number = args.issue_url.split("/")[-1]

    with open(JSON_OUTPUT_PATH, "rb") as prediction:
        output_name = "needsdiagnosis/{}.json".format(issue_number)
        s3.upload_fileobj(
            prediction,
            S3_RESULTS_ML_BUCKET,
            output_name,
            ExtraArgs={"ContentType": "application/json"},
        )

    with open("predictions.json") as prediction:
        prediction = json.load(prediction)
        doc = {"issue": int(issue_number), "prediction": prediction}
        ES.indices.create("needsdiagnosis-ml-results", ignore=400)
        ES.index(
            index="needsdiagnosis-ml-results",
            doc_type="result",
            id=int(issue_number),
            body=doc,
        )
