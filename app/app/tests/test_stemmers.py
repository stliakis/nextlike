from app.core.indexers.stemmer.generic import stem
from app.easytests import EasyTest
from app.tests.config import nextlike_easytest_config


class TestStemmers(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self) -> list[dict]:
        return [
            {
                "input": "this is a great day",
                "expected_output": "thi great day",
                "stemmers": ["english", "greek"]
            },
            {
                "input": "λάστιχα αυτοκινήτων",
                "expected_output": "λάστιχ αυτοκινήτ",
                "stemmers": ["english", "greek"]
            },
            {
                "input": "αμοχωστος",
                "expected_output": "amoxost",
                "stemmers": ["greeklish"]
            },
            {
                "input": "xeimerina elastika autokinitou",
                "expected_output": "xeimerin elastik autokinit",
                "stemmers": ["greeklish"]
            },
            {
                "input": "opel corsa",
                "expected_output": "opel cors",
                "stemmers": ["greeklish"]
            },
            {
                "input": "ford mondeo",
                "expected_output": "ford mondeo",
                "stemmers": ["greeklish"]
            },
            {
                "input": "διαμέρισμα",
                "expected_output": "diamerism",
                "stemmers": ["greeklish"]
            }
        ]

    async def test(self, input, expected_output, stemmers):
        stemmed = stem(stemmers, input)

        self.should("be correct", expected_output, stemmed)
