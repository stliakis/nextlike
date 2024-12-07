import re
import unicodedata

from app.core.indexers.stemmer.base import Stemmer
from app.core.indexers.stemmer.greek import GreekStemmer


class GreeklishStemmer(Stemmer):
    name = "greeklish"

    # Common Greeklish-to-Greek double-letter mappings
    GREEKLISH_TO_GREEK_DOUBLES = [
        (r'TH', 'Θ'),
        (r'KH', 'Χ'),  # Sometimes 'CH' is written as 'KH'
        (r'CH', 'Χ'),
        (r'PS', 'Ψ'),
        (r'PH', 'Φ'),
        (r'TZ', 'ΤΖ'),
        (r'TS', 'ΤΣ'),
        (r'KS', 'Ξ'),
        (r'EU', 'ΕΥ'),  # will handle environment-sensitive replacements below
        (r'EV', 'ΕΥ'),
        (r'AF', 'ΑΥ'),
        (r'AV', 'ΑΥ'),
        (r'OU', 'ΟΥ'),
        (r'AI', 'ΑΙ'),
        (r'EI', 'ΕΙ'),
        (r'OI', 'ΟΙ'),
        (r'MP', 'ΜΠ'),
        (r'NT', 'ΝΤ'),
        (r'GB', 'ΓΜΠ'),  # Not standard but can be adapted if needed
        (r'GK', 'ΓΚ')  # As in "γκ" sound
    ]

    # For single letters (Greeklish -> Greek)
    GREEKLISH_TO_GREEK_SINGLES = {
        'A': 'Α', 'B': 'Β', 'C': 'Κ', 'D': 'Δ', 'E': 'Ε', 'F': 'Φ', 'G': 'Γ',
        'H': 'Η', 'I': 'Ι', 'J': 'ΤΖ', 'K': 'Κ', 'L': 'Λ', 'M': 'Μ', 'N': 'Ν',
        'O': 'Ο', 'P': 'Π', 'Q': 'Κ', 'R': 'Ρ', 'S': 'Σ', 'T': 'Τ', 'U': 'Υ',
        'V': 'Β', 'W': 'Ω', 'X': 'Χ', 'Y': 'Υ', 'Z': 'Ζ'
    }

    # Greek-to-Greeklish doubles (reverse mapping)
    GREEK_TO_GREEKLISH_DOUBLES = [
        (r'Θ', 'TH'),
        (r'Χ', 'CH'),
        (r'Ψ', 'PS'),
        (r'Φ', 'F'),
        (r'ΤΖ', 'J'),
        (r'ΤΣ', 'TS'),
        (r'Ξ', 'KS'),
        (r'ΜΠ', 'MP'),
        (r'ΝΤ', 'NT'),
        (r'ΓΚ', 'GK'),
        (r'ΟΥ', 'OU'),
        (r'ΕΥ', 'EV'),  # Will handle environment-sensitive if needed
        (r'ΑΥ', 'AV'),
        (r'ΑΙ', 'AI'),
        (r'ΕΙ', 'EI'),
        (r'ΟΙ', 'OI')
    ]

    # For single letters (Greek -> Greeklish)
    GREEK_TO_GREEKLISH_SINGLES = {
        'Α': 'A', 'Β': 'V', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'I',
        'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M', 'Ν': 'N', 'Ο': 'O', 'Π': 'P',
        'Ρ': 'R', 'Σ': 'S', 'Τ': 'T', 'Υ': 'Y', 'Φ': 'F', 'Χ': 'X', 'Ψ': 'PS',
        'Ω': 'W'
    }

    SPECIAL_CHARACTERS = {
        "-": " ",
        "/": " "
    }

    # Accented Greek chars mapping
    # We'll remove accents through normalization and map final sigma (ς) -> σ
    def remove_greek_accents(self, text):
        # Normalize to NFD to separate accents from letters
        text = unicodedata.normalize('NFD', text)
        # Remove diacritical marks
        text = "".join(ch for ch in text if unicodedata.category(ch) != 'Mn')
        # Re-compose the string
        text = unicodedata.normalize('NFC', text)
        return text

    def remove_special_characters(self, text):
        for key, value in self.SPECIAL_CHARACTERS.items():
            text = text.replace(key, value)
        return text

    def to_lower(self, text):
        return text.lower()

    def normalize_greek(self, text):
        """Normalize Greek text: remove accents, normalize final sigma to normal sigma."""
        text = self.remove_greek_accents(text)
        text = self.greek_reduce_characters(text)
        text = self.remove_special_characters(text)
        # Convert final sigma (ς) to normal sigma (σ)
        text = re.sub('ς', 'σ', text)
        return self.to_lower(text)

    def greeklish_to_greek(self, string):
        string = string.upper()

        # Replace double-letter sequences first to avoid partial matches
        # Process environment-sensitive sequences like EU->ΕΥ (and handle EF if needed)
        # We'll handle conditional replacements using regex. For example:
        # If 'E' is followed by certain consonants (θ κ ξ π σ τ φ χ ψ), we might consider EF vs EV.
        # For simplicity, we assume 'EU' -> 'ΕΥ' and handle them uniformly:
        # More nuanced rules could be added if needed.

        # Handle the complex doubles in order of specificity
        # Start with the longest possible sequences to avoid partial conflicts
        # Just apply our known doubles naively here:
        for pattern, greek_char in self.GREEKLISH_TO_GREEK_DOUBLES:
            string = re.sub(pattern, greek_char, string)

        # Then handle single characters
        for lat, gr in self.GREEKLISH_TO_GREEK_SINGLES.items():
            string = string.replace(lat, gr)

        # Normalize (remove accents, ensure correct casing)
        string = self.normalize_greek(string)
        return string

    def greek_to_greeklish(self, string):
        string = self.normalize_greek(string)
        # Convert to uppercase for mapping
        string = string.upper()

        # Replace double-letter Greek sequences first
        for gr, lat in self.GREEK_TO_GREEKLISH_DOUBLES:
            string = string.replace(gr, lat)

        # Replace single Greek letters
        for gr, lat in self.GREEK_TO_GREEKLISH_SINGLES.items():
            string = string.replace(gr, lat)

        # Convert to lowercase
        string = string.lower()

        return string

    def greek_reduce_characters(self, string):
        string = string.replace("η", "ι")
        string = string.replace("υ", "ι")
        string = string.replace("ω", "ο")
        string = string.replace("ψ", "σ")
        string = string.replace("ξ", "σ")
        string = string.replace("θ", "σ")
        string = string.replace("χ", "κ")
        string = string.replace("φ", "π")
        string = string.replace("β", "μπ")
        string = string.replace("γ", "γκ")
        string = string.replace("δ", "ντ")
        return string

    def greek_remove_accents(self, word):
        word = word.replace("ά", "α")
        word = word.replace("έ", "ε")
        word = word.replace("ί", "ι")
        word = word.replace("ό", "ο")
        word = word.replace("ύ", "υ")
        word = word.replace("ώ", "ω")
        word = word.replace("ή", "η")
        word = word.replace("ϊ", "ι")
        word = word.replace("ϋ", "υ")
        word = word.replace("ΐ", "ι")
        word = word.replace("ΰ", "υ")
        return word

    def stem(self, phrase):
        # Convert Greeklish -> Greek
        greek = self.greeklish_to_greek(phrase)
        # Stem the Greek phrase
        stemmed_greek = GreekStemmer().stem(greek)
        # Convert back Greek -> Greeklish
        greeklish = self.greek_to_greeklish(stemmed_greek)
        # Normalize whitespace, remove single-letter words
        greeklish = " ".join(word for word in greeklish.split() if len(word) > 1)

        # print("phrase", phrase, "greek", greek, "stemmed_greek", stemmed_greek, "greeklish", greeklish)

        return greeklish
