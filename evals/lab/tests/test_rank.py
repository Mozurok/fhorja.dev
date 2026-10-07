import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rank import compare, ordered, metrics


class RankTests(unittest.TestCase):
    def setUp(self):
        self.cases = [{"id": "c", "language": "pt", "query": "contexto",
                       "required_ids": ["mandatory"], "relevant_ids": ["b"],
                       "candidates": [{"id": "a", "text": "noise"}, {"id": "b", "text": "contexto"}]}]

    def test_frozen_pool_required_and_ranking(self):
        a = compare(self.cases, "deterministic")
        b = compare(self.cases, "injected", scorer=lambda q, c: [1, 2])
        self.assertEqual(a["status"], "measured")
        self.assertEqual(len(a["revision"]), 64)
        self.assertEqual(a["rows"][0]["candidate_hash"], b["rows"][0]["candidate_hash"])
        self.assertEqual(b["rows"][0]["required_ids"], ["mandatory"])
        self.assertEqual(b["rows"][0]["recall_at_2"], 1)

    def test_invalid_scores_and_ties(self):
        for scores in [[], [float('nan'), 1], [float('inf'), 2]]:
            with self.assertRaises(ValueError): ordered(self.cases[0]["candidates"], scores)
        self.assertEqual(ordered(self.cases[0]["candidates"], [1, 1]), ["a", "b"])

    def test_unknown_arm_and_metrics(self):
        self.assertEqual(compare(self.cases, "not-a-model")["status"], "unavailable")
        self.assertEqual(metrics(["a", "b"], ["b"])["recall_at_2"], 1)
        self.assertLess(metrics(["a", "b"], ["b"])["ndcg_at_2"], 1)

    def test_warmup_mutation_is_rejected(self):
        def mutate(q, candidates):
            candidates[0]["text"] = "changed"
            return [1, 2]
        self.assertEqual(compare(self.cases, "injected", scorer=mutate)["status"], "unavailable")


    def test_invalid_identity_and_score_are_unavailable(self):
        import copy
        bad = copy.deepcopy(self.cases)
        bad[0]["candidates"][0]["id"] = "b"
        self.assertEqual(compare(bad, "deterministic")["status"], "unavailable")
        bad = copy.deepcopy(self.cases)
        bad[0]["required_ids"] = ["a"]
        self.assertEqual(compare(bad, "deterministic")["status"], "unavailable")
        out = compare(self.cases, "injected", scorer=lambda q, c: [None, None])
        self.assertEqual(out["status"], "unavailable")



if __name__ == "__main__": unittest.main()
