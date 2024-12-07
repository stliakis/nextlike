from app.core.indexers.stemmer.generic import stem
from app.easytests import EasyTest
from app.tests.config import nextlike_easytest_config


class TestStemmers(EasyTest):
    config = nextlike_easytest_config

    async def get_cases(self) -> list[dict]:
        return [
            {
                "input": "Διαμέρισμα <- Κατοικία <- Ενοικίαση <- Ακίνητα",
                "expected_output": "ntiamerism katoiki enoikias akinit",
                "stemmers": ["greeklish"]
            },
            {
                "input": "οικόπεδο",
                "expected_output": "oikopento",
                "stemmers": ["greeklish"]
            },
            {
                "input": "oikopedo",
                "expected_output": "oikopento",
                "stemmers": ["greeklish"]
            },
            {
                "input": "iphone 14",
                "expected_output": "ipone 14",
                "stemmers": ["greeklish"]
            },
            {
                "input": "ιπηονε 14",
                "expected_output": "ipione 14",
                "stemmers": ["greeklish"]
            },
            {
                "input": "enoikiasi",
                "expected_output": "enoikias",
                "stemmers": ["greeklish"]
            },
            {
                "input": "ενοικιαση",
                "expected_output": "enoikias",
                "stemmers": ["greeklish"]
            },
            {
                "input": "this is a great day",
                "expected_output": "thi great day",
                "stemmers": ["english", "greek"]
            },
            {
                "input": "lastixa autokiniton",
                "expected_output": "lastik aitokinit",
                "stemmers": ["greeklish"]
            },
            {
                "input": "λάστιχα αυτοκινήτων",
                "expected_output": "lastik aitokinit",
                "stemmers": ["greeklish"]
            },
            {
                "input": "αμοχωστος",
                "expected_output": "amokost",
                "stemmers": ["greeklish"]
            },
            {
                "input": "xeimerina elastika autokinitou",
                "expected_output": "keimerin elastik aitokinit",
                "stemmers": ["greeklish"]
            },
            {
                "input": "opel corsa",
                "expected_output": "opel kors",
                "stemmers": ["greeklish"]
            },
            {
                "input": "ford mondeo",
                "expected_output": "pornt monnteo",
                "stemmers": ["greeklish"]
            },
            {
                "input": "διαμέρισμα",
                "expected_output": "ntiamerism",
                "stemmers": ["greeklish"]
            },
            {
                "input": "kalamaria",
                "expected_output": "kalamari",
                "stemmers": ["greeklish"]
            },
            {
                "input": "καλαμαριά",
                "expected_output": "kalamari",
                "stemmers": ["greeklish"]
            },
            {
                "input": "ενοικίαση διαμέρισμα studio σπίτι Θεσσαλονίκη - περιφ/κοί δήμοι Καλαμαριά",
                "expected_output": "enoikias ntiamerism stintio spit sessalonik perip ko ntimo kalamari",
                "stemmers": ["greeklish"]
            },
            {
                "input": "studio ston evosmo gia enikiasi",
                "expected_output": "stintio eiosmo enikias",
                "stemmers": ["greeklish"]
            },
            {
                "input": "Kαλοκαιρινά Ελαστικά <- Λάστιχα <- Ζάντες & Λάστιχα <- Αυτοκινήτων <- Ανταλλακτικά & Αξεσουάρ",
                "expected_output": "kalokairin elastik lastik zant lastik aitokinit antallaktik asesoiar",
                "stemmers": ["greeklish"]
            }
        ]

    async def test(self, input, expected_output, stemmers):
        stemmed = stem(stemmers, input)

        self.should("be correct", expected_output, stemmed)
