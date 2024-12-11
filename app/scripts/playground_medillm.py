import asyncio
import copy
import itertools
import json
import sys
from pprint import pprint
from sqlalchemy.orm import Session
from app.db.session import Database
from app.llm.embeddings import OpenAiEmbeddingsCalculator
from app.llm.llm import GroqLLM, OpenAILLM
from app.models import Collection
from app.core.aggregator.aggregator import Aggregator
from app.core.searcher.searcher import Searcher
from app.core.types import (
    SearchConfig,
    SimilaritySearchConfig,
    SimilarityClauseEmbeddings, AggregationConfig,
)
from app.utils.base import listify
from app.utils.timeit import Timeit
import base64
from PIL import Image
from io import BytesIO


async def main():
    def encode_image_to_base64(file_path):
        with Image.open(file_path) as img:
            resized_img = img.resize((512, 512))
            buffer = BytesIO()
            img.save(buffer, format=img.format)
            buffer.seek(0)
            encoded_string = base64.b64encode(buffer.read()).decode('utf-8')
            return encoded_string

    def pdf_to_base64(file_path):
        import base64

        with open(file_path, "rb") as pdf_file:
            encoded_string = base64.b64encode(pdf_file.read())
            return encoded_string

    with Database() as db:
        collection = Collection.objects(db).get(627829530234)

        with Timeit("aggregator.aggregate()"):
            query = AggregationConfig(
                prompt="Extract the indicators from the images, parse all the indicators in all the files, they are in greek, must read all the files!",
                files=[
                    # {
                    #     "type": "image",
                    #     "base64": encode_image_to_base64('1.png')
                    # },
                    {
                        "type": "pdf",
                        "base64": pdf_to_base64("3.pdf")
                    }
                ],
                aggregations=[
                    {
                        "name": "results",
                        "description": "the blood test results",
                        "fields": {
                            "indicators": {
                                "description": "the list of indicators as seen in the uploaded images",
                                "type": "list",
                                "of": {
                                    "objects": {
                                        "category": {
                                            "type": "text",
                                            "enum": ["Blood Sugar and Lipid Profile", "Liver Function",
                                                     "Kidney Function", "Blood Count", "Inflammation", "Iron",
                                                     "Vitamins", "Hormones", "Tumor Markers", "Other"],
                                            "required": True
                                        },
                                        "value_metric": "the value metric",
                                        "indicator": {
                                            "object": {
                                                "text_english": {
                                                    "required": True,
                                                    "description": "the indicator name in english"
                                                },
                                                "text_greek": {
                                                    "required": True,
                                                    "description": "the indicator name in greek"
                                                }
                                            }
                                        },
                                        "base_value_min": "the minimum base value",
                                        "base_value_max": "the maximum base value",
                                        "value": {
                                            "type": "text",
                                            "description": "the value of the indicator"
                                        }
                                    }
                                }
                            },
                            "date": {
                                "type": "text",
                                "description": "the date of the test",
                                "required": True
                            },
                            "doctor": {
                                "type": "text",
                                "description": "the doctor name",
                                "required": True
                            }
                        }
                    }
                ],
                light_model="openai:gpt-4o-mini",
                heavy_model="openai:gpt-4o-mini",
                caching=False
            )

            engine = Aggregator(db, collection, query)

            aggregations = await Aggregator(db, collection, query).aggregate()

            pprint([aggregation.dict() for aggregation in aggregations])


if __name__ == "__main__":
    text_queries = [
        (
            "καταχωρηση αγγελιας opel corsa ασπρο 2000 κιβυκα , 3000ευρω θεσσαλονικη, 100000 χιλιομετρα",
            [{'engine_size': 1000, 'registration_year': 2000, 'location': 2, 'make': 13334, 'color': '9',
              'mileage': 100000, 'model': 14744},
             {'engine_size': 1000, 'registration_year': 2000, 'location': 2, 'make': 13334, 'color': '9',
              'mileage': 100000, 'model': 14752},
             {'engine_size': 1000, 'registration_year': 2000, 'location': 41, 'make': 13334, 'color': '9',
              'mileage': 100000, 'model': 14744},
             {'engine_size': 1000, 'registration_year': 2000, 'location': 41, 'make': 13334, 'color': '9',
              'mileage': 100000, 'model': 14752}]
        ),
        (
            "μιζα κινητηρα ford puma",
            [{'make': 13272, 'text_search': 'μιζα κινητηρα', 'model': 14305},
             {'make': 13272, 'text_search': 'μιζα κινητηρα', 'model': 14268}]
        ),
        (
            "ψαχνω διαμερισμα η studio για αγορα στην θεσσαλονικη εως 7000 ευρω να επιστρεπονται τα κατοικιδια",
            [{'location': 2, 'price_to': 7000, 'category': [20031, 20036]},
             {'location': 22, 'price_to': 7000, 'category': [20031, 20036]}]
        )

    ]

    asyncio.run(main())
