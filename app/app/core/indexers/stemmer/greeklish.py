import re

from app.core.indexers.stemmer.base import Stemmer
from app.core.indexers.stemmer.greek import GreekStemmer


class GreeklishStemmer(Stemmer):
    name = "greeklish"

    suffixes = [
        "ontas", "ontas", "iontas", "ousas", "ousa", "oume", "oune", "ountai", "ou", "esai", "ia", "ies", "ion", "os",
        "ou", "es", "wn", "ous", "as", "h", "hs", "wn", "esai", "este", "etai", "oume", "oun", "ete", "eis", "ei"
    ]

    words_to_remove = ["o", "i", "oi", "tou", "tis", "ton", "tin", "to", "ta", "twn", "tw", "twn", "twn", "tis", "ston",
                       "stwn", "stou", "se", "stin", "stis", "sthn", "sths"
                                                                     "tous"]

    tokens_to_remove = ["?", "-", ">", "<", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "=", "+", "[", "]",
                        "{", "}", ";", ":", "'", "\"", "\\", "|", ",", ".", "/", "<", ">", "`", "~"]

    def stem(self, phrase):
        greeklish_stemmed = self.greek_to_greeklish(
            phrase
        )

        phrase = greeklish_stemmed.lower()

        for token in self.tokens_to_remove:
            phrase = phrase.replace(token, " ")

        phrase = " ".join([word for word in phrase.split() if word not in self.words_to_remove])
        phrase = " ".join([self.stem_word(word) for word in phrase.split()])

        phrase = " ".join([i for i in phrase.split() if len(i) > 1])

        return phrase

    def greeklish_to_greek(self, string):
        single_latin = u'ACDEFGIIKLMNOPRSTIVOXIZ83I'
        single_greek = u'ΑΨΔΕΦΓΗΙΚΛΜΝΟΠΡΣΤΥΒΩΧΥΖΘΞΥ'
        singles = list(zip(single_latin, single_greek))

        doubles = [
            (u'TH', u'Θ'),
            (u'KS', u'Ξ'),
            (u'EF', u'ΕΥ'),
            (u'AF', u'ΑΥ'),
            (u'CH', u'Χ'),
            (u'PS', u'Ψ'),
            (u'J', u'ΤΖ'),
            (u'B', u'ΜΠ')
        ]

        string = string.upper()
        for latin, greek in doubles:
            string = string.replace(latin, greek)
        for latin, greek in singles:
            string = string.replace(latin, greek)

        return string

    def greek_to_greeklish(self, string):
        accented = u'άέόίύώήϊϋΐΰΆΌΊΈΎΏΉ'
        plain = u'αεοιυωηιυιυαοιευωη'
        replace_map = list(zip(accented, plain))

        def remove_accents_and_capitalize(word):
            word = word.lower()
            for before, after in replace_map:
                word = word.replace(before, after)
            return word.upper()

        single_latin = u'ACDEFGIIKLMNOPRSTYVOXYZ83'
        single_greek = u'ΑΨΔΕΦΓΗΙΚΛΜΝΟΠΡΣΤΥΒΩΧΥΖΘΞ'

        rev_singles = list(zip(single_greek, single_latin))
        rev_doubles = [
            (u'Θ', u'TH'),
            (u'Ξ', u'KS'),
            (u'ΑΥ', u'AF'),
            (u'Ψ', u'PS'),
            (u'ΤΖ', u'J'),
            (u'ΜΠ', u'B')
        ]
        regex_rev_doubles = [('ΕΥ(?=[ΘΚΞΠΣΤΦΧΨ])', u'EF'),
                             ('ΕΥ', u'EV'),
                             ('ΑΥ(?=[ΘΚΞΠΣΤΦΧΨ])', u'AF'),
                             ('ΑΥ', u'AV')]

        string = remove_accents_and_capitalize(string)
        for greek, latin in regex_rev_doubles:
            string = re.sub(greek, latin, string, flags=re.UNICODE)
        for greek, latin in rev_doubles:
            string = string.replace(greek, latin)
        for greek, latin in rev_singles:
            string = string.replace(greek, latin)

        return string.lower()

    def stem_word(self, word):
        for suffix in self.suffixes:
            if word.endswith(suffix):
                new_word = word[:-len(suffix)]
                if len(new_word) >= 3:
                    word = new_word

        return word
