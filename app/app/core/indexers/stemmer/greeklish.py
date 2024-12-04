import re

from app.core.indexers.stemmer.base import Stemmer
from app.core.indexers.stemmer.greek import GreekStemmer


class GreeklishStemmer(Stemmer):
    name = "greeklish"

    suffixes = [
        'ωντας', 'οντας', 'ιωντας', 'ουσας', 'ουσα', 'ουμε', 'ουνε', 'ουνται',
        'εσαι', 'εστε', 'εται', 'ουμε', 'ουν', 'ετε', 'εις', 'ει', 'ειτε',
        'ια', 'ιες', 'ιων', 'ος', 'ου', 'α', 'ες', 'ων', 'ους', 'ας', 'η', 'ης', 'ων'
    ]

    def stem(self, phrase):
        greek = self.greeklish_to_greek(phrase)
        stemmed_greek = GreekStemmer().stem(greek)
        greeklish_stemmed = self.greek_to_greeklish(
            stemmed_greek
        )
        return greeklish_stemmed

    def greeklish_to_greek(self, string):
        single_latin = u'ACDEFGIIKLMNOPRSTYVWXYZ83U'
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
            # (u'ΕΥ', u'EF'),
            (u'ΑΥ', u'AF'),
            # (u'Χ', u'CH'),
            (u'Ψ', u'PS'),
            (u'ΤΖ', u'J'),
            (u'ΜΠ', u'B')
        ]
        regex_rev_doubles = [('ΕΥ(?=[ΘΚΞΠΣΤΦΧΨ])', u'EF'),  # ΕΥ followed by specific consonants
                             ('ΕΥ', u'EV'),  # ΕΥ in other cases
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
                return word[:-len(suffix)]
        return word
