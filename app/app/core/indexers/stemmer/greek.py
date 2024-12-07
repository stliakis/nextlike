from app.core.indexers.stemmer.base import Stemmer


class GreekStemmer(Stemmer):
    name = "greek"

    words_to_remove = ["ειμαι", "εισαι", "ειναι", "ειμαστε", "ειστε", "ειναι", "εισαι", "ειστε", "ειναι", "σε", "για",
                       "στην", "στον", "απο", "εως"]

    tokens_to_remove = ["?", "-", ">", "<", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "=", "+", "[", "]",
                        "{", "}", ";", ":", "'", "\"", "\\", "|", ",", ".", "/", "<", ">", "`", "~"]

    suffixes = [
        'ωντας', 'οντας', 'ιωντας', 'ουσας', 'ουσα', 'ουμε', 'ουνε', 'ουνται',
        'εσαι', 'εστε', 'εται', 'ουμε', 'ουν', 'ετε', 'εις', 'ει', 'ειτε',
        'ια', 'ιες', 'ιων', 'ος', 'ου', 'α', 'ες', 'ων', 'ους', 'ας', 'η', 'ης', 'ων', 'του'
    ]

    def remove_accents(self, word):
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
        phrase = phrase.lower()

        phrase = self.remove_accents(phrase)

        for token in self.tokens_to_remove:
            phrase = phrase.replace(token, " ")

        phrase = " ".join([word for word in phrase.split() if word not in self.words_to_remove])
        phrase = " ".join([self.stem_word(word) for word in phrase.split()])

        return phrase

    def stem_word(self, word):
        for suffix in self.suffixes:
            if word.endswith(suffix):
                return word[:-len(suffix)]
        return word
