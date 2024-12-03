from app.core.indexers.stemmer.english import EnglishStemmer
from app.core.indexers.stemmer.greek import GreekStemmer
from app.core.indexers.stemmer.greeklish import GreeklishStemmer


def stem(stemmer_names, phrase):
    for cls in [
        EnglishStemmer,
        GreekStemmer,
        GreeklishStemmer
    ]:
        if cls.name in stemmer_names:
            phrase = cls().stem(phrase)

    return phrase
