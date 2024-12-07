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
                "expected_output": "λαστιχ αυτοκινητ",
                "stemmers": ["english", "greek"]
            },
            {
                "input": "αμοχωστος",
                "expected_output": "amoxost",
                "stemmers": ["greeklish"]
            },
            {
                "input": "xeimerina elastika autokinitou",
                "expected_output": "xeimerin elastik aftokinit",
                "stemmers": ["greeklish"]
            },
            {
                "input": "opel corsa",
                "expected_output": "opel psors",
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
            },
            {
                "input": "kalamaria",
                "expected_output": "kalamar",
                "stemmers": ["greeklish"]
            },
            {
                "input": "καλαμαριά",
                "expected_output": "kalamar",
                "stemmers": ["greeklish"]
            },
            {
                "input": "ενοικίαση διαμέρισμα studio σπίτι Θεσσαλονίκη - περιφ/κοί δήμοι Καλαμαριά",
                "expected_output": "enoikias diamerism studio spiti thessalonik perif koi dimoi kalamar",
                "stemmers": ["greeklish"]
            },
            {
                "input": "studio ston evosmo gia enikiasi",
                "expected_output": "studio evosmo enikiasi",
                "stemmers": ["greeklish"]
            },
            {
                "input": "Kαλοκαιρινά Ελαστικά <- Λάστιχα <- Ζάντες & Λάστιχα <- Αυτοκινήτων <- Ανταλλακτικά & Αξεσουάρ",
                "expected_output": "kalokairin elastik lastix zant lastix aftokinit antallaktik aksesouar",
                "stemmers": ["greeklish"]
            }
        ]

    async def test(self, input, expected_output, stemmers):
        stemmed = stem(stemmers, input)

        self.should("be correct", expected_output, stemmed)
