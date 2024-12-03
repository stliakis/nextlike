from app.core.indexers.stemmer.base import Stemmer


class GreekStemmer(Stemmer):
    name = "greek"

    words_to_remove = ["είμαι", "είσαι", "είναι", "είμαστε", "είστε", "είναι", "είσαι", "είστε", "είναι", "σε", "για"]

    tokens_to_remove = ["?", "-", ">", "<", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "=", "+", "[", "]",
                        "{", "}", ";", ":", "'", "\"", "\\", "|", ",", ".", "/", "<", ">", "`", "~"]

    suffixes = [
        'ωντας', 'οντας', 'ιωντας', 'ουσας', 'ουσα', 'ουμε', 'ουνε', 'ουνται',
        'εσαι', 'εστε', 'εται', 'ουμε', 'ουν', 'ετε', 'εις', 'ει', 'ειτε',
        'ια', 'ιες', 'ιων', 'ος', 'ου', 'α', 'ες', 'ων', 'ους', 'ας', 'η', 'ης', 'ων'
    ]

    def stem(self, phrase):
        phrase = phrase.lower()

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
