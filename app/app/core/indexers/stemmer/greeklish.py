import re

from app.core.indexers.stemmer.base import Stemmer
from app.core.indexers.stemmer.greek import GreekStemmer

class GreeklishStemmer(Stemmer):
    name = "greeklish"

    suffixes = [
        "iontas", "ontas", "ousas", "ountai", "oune", "oume",
        "ousa", "este", "esai", "etai", "oun", "ion", "ies",
        "eis", "ete", "os", "ou", "es", "wn", "ous", "as", "hs", "ei"
    ]

    def stem(self, phrase):
        greek = self.greeklish_to_greek(phrase)

        stemmed_greek = GreekStemmer().stem(greek)

        greeklish = self.greek_to_greeklish(stemmed_greek)

        phrase = greeklish.lower()

        phrase = " ".join(word for word in phrase.split() if len(word) > 1)

        return phrase

    def greeklish_to_greek(self, string):
        single_latin = u'ACDEFGIIKLMNOPRSTIVOXIZ83IU'
        single_greek = u'ΑΨΔΕΦΓΙΙΚΛΜΝΟΠΡΣΤΙΒΩΧΙΖΘΞΥΥ'
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

        return string.lower()

    def greek_to_greeklish(self, string):
        accented = u'άέόίύώήϊϋΐΰΆΌΊΈΎΏΉ'
        plain = u'αεοιυωηιυιυαοιευωη'
        replace_map = list(zip(accented, plain))

        def remove_accents_and_capitalize(word):
            word = word.lower()
            for before, after in replace_map:
                word = word.replace(before, after)
            return word.upper()

        single_latin = u'ACDEFGIIKLMNOPRSTUVOXUZ83'
        single_greek = u'ΑΨΔΕΦΓΗΙΚΛΜΝΟΠΡΣΤΥΒΩΧΥΖΘΞ'

        rev_singles = list(zip(single_greek, single_latin))
        rev_doubles = [
            (u'Θ', u'TH'),
            (u'Ξ', u'KS'),
            # (u'ΑΥ', u'AF'),
            (u'Ψ', u'PS'),
            (u'ΤΖ', u'J'),
            (u'ΜΠ', u'B')
        ]

        regex_rev_doubles = [
            (r'ΕΥ(?=[ΘΚΞΠΣΤΦΧΨ])', u'EF'),
            (r'ΕΥ', u'EV'),
            (r'ΑΥ(?=[ΘΚΞΠΣΤΦΧΨ])', u'AF'),
            (r'ΑΥ', u'AV')
        ]

        string = remove_accents_and_capitalize(string)

        for pattern, repl in regex_rev_doubles:
            string = re.sub(pattern, repl, string, flags=re.UNICODE)

        for greek, latin in rev_doubles:
            string = string.replace(greek, latin)
        for greek, latin in rev_singles:
            string = string.replace(greek, latin)

        return string.lower()
