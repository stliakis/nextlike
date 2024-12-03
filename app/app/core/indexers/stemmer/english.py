from app.core.indexers.stemmer.base import Stemmer


class EnglishStemmer(Stemmer):
    name = "english"

    suffixes = ['ing', 'ly', 'ious', 'ies', 'ive', 'es', 's', 'ment']
    words_to_remove = ["is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
                       "did", "shall", "will", "should", "would", "may", "might", "must", "can", "could", "to", "a"]
    tokens_to_remove = ["?", "-", ">", "<", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "=", "+", "[", "]",
                        "{", "}", ";", ":", "'", "\"", "\\", "|", ",", ".", "/", "<", ">", "`", "~"]

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
