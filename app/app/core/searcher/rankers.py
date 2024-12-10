import random

from sympy import sympify


class Ranker(object):
    def item_score_calculator(self, item):
        raise NotImplementedError()


class RandomRanker(object):
    def __init__(self):
        pass

    def rank(self, items, limit):
        return random.shuffle(items)[:limit]


class ScoreRanker(object):

    def __init__(self, score_function: str):
        self.score_function = score_function

    def item_score_calculator(self, item):
        variables = {
            "score": item.score
        }

        normalized_score_function = self.score_function
        normalized_score_function = normalized_score_function.replace("score.", "score___")

        all_score_names = set(
            str(symbol) for symbol in sympify(normalized_score_function).free_symbols
        )

        for score_name, score in item.scores.items():
            variables[f"score___{score_name}"] = score

        for score_name in all_score_names:
            if score_name.startswith("score___") and score_name not in variables:
                variables[score_name] = 0

        return sympify(normalized_score_function).evalf(subs=variables)

    def rank(self, items, limit):
        ranked_items = []

        for item in items:
            item.score = self.item_score_calculator(item)
            ranked_items.append(item)

        ranked_items.sort(key=lambda item: item.score, reverse=True)

        return ranked_items[:limit]
