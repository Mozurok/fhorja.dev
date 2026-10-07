import sys
import copy
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usage import ledger, session_records


def call(i, inp=100, cached=30, out=10):
    return {"type": "token_usage_record", "payload": {"request_id": i, "usage": {
        "input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out}}}


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.prices = {"model": {"input": 2, "cached_input": 0.1, "output": 10}}
        self.sessions = {"r": {"model": "model", "events": [call("a"), call("a")]},
                         "c": {"parent": "r", "model": "model", "events": [call("b")]},
                         "g": {"parent": "c", "model": "model", "events": [call("c")]},
                         "other": {"model": "model", "events": [call("x", 100000)]}}

    def run_ledger(self, children=()):
        return ledger(self.sessions, "r", self.prices, "2026-09-29", children)

    def test_linked_descendants_and_dedup(self):
        out = self.run_ledger()
        self.assertTrue(out["complete"])
        self.assertEqual(out["sessions"], ["c", "g", "r"])
        self.assertEqual(out["observed_tokens"]["input_tokens"], 300)
        self.assertAlmostEqual(out["cost_usd"], 3 * (70*2 + 30*0.1 + 10*10)/1e6)

    def test_missing_child_and_usage(self):
        self.assertIsNone(self.run_ledger(["absent"])["cost_usd"])
        self.sessions["c"]["events"] = []
        self.assertIsNone(self.run_ledger()["cost_usd"])

    def test_unknown_price_model_and_date(self):
        self.sessions["c"]["model"] = "unknown"
        out = self.run_ledger(); self.assertFalse(out["complete"])
        self.assertIsNone(out["cost_usd"])
        out = ledger(self.sessions, "r", self.prices)
        self.assertIn("pricing date unavailable", out["issues"])

    def test_conflicting_duplicate_and_invalid_cache(self):
        self.sessions["r"]["events"].append(call("a", 200))
        self.assertFalse(self.run_ledger()["complete"])
        self.sessions["r"]["events"] = [call("a", cached=101)]
        self.assertFalse(self.run_ledger()["complete"])

    def test_cumulative_snapshots_and_compaction(self):
        def snap(n):
            return {"payload": {"type": "token_count", "info": {"total_token_usage": {
                "input_tokens": n, "cached_input_tokens": n//2, "output_tokens": n//10}}}}
        rows, issues = session_records([snap(100), snap(100), {"type": "compacted"}, snap(200)], "r", "model")
        self.assertFalse(issues)
        self.assertEqual(sum(r["usage"]["input_tokens"] for r in rows), 200)
        _, issues = session_records([snap(200), snap(100)], "r", "model")
        self.assertTrue(issues)

    def test_call_view_preferred_over_duplicate_cumulative(self):
        c = {"payload": {"type": "token_count", "info": {"total_token_usage": call("a")["payload"]["usage"]}}}
        rows, issues = session_records([call("a"), c], "r", "model")
        self.assertEqual(len(rows), 1); self.assertFalse(issues)

    def test_model_change_and_equal_usage_distinct_calls(self):
        events = [call("a"), {"type": "turn_context", "payload": {"model": "other"}}, call("b")]
        rows, issues = session_records(events, "r", "model")
        self.assertEqual(len(rows), 2); self.assertFalse(issues)
        self.assertEqual(rows[1]["model"], "other")


    def test_mixed_views_must_reconcile(self):
        snapshot = {"payload": {"type": "token_count", "info": {"total_token_usage": call("z", 500, 150, 50)["payload"]["usage"]}}}
        self.sessions["r"]["events"] = [call("a"), snapshot]
        out = self.run_ledger()
        self.assertFalse(out["complete"]); self.assertIsNone(out["cost_usd"])
        self.assertEqual(out["observed_tokens"]["input_tokens"], 300)

    def test_cumulative_optional_fields_and_malformed_payload(self):
        usage = {**call("a")["payload"]["usage"], "cache_write_input_tokens": 900, "reasoning_output_tokens": 4}
        snapshot = {"payload": {"type": "token_count", "info": {"total_token_usage": usage}}}
        self.sessions = {"r": {"model": "model", "events": [snapshot, snapshot]}}
        out = self.run_ledger()
        self.assertFalse(out["complete"]); self.assertIsNone(out["cost_usd"])
        self.assertEqual(out["observed_optional_tokens"]["cache_write_input_tokens"], 900)
        self.assertEqual(out["observed_optional_tokens"]["reasoning_output_tokens"], 4)
        _, issues = session_records([{"type": "token_usage_record", "payload": "bad"}], "r")
        self.assertTrue(issues)


    def test_linked_duplicate_provider_id_charged_once(self):
        self.sessions["c"]["events"] = [call("a")]
        out = self.run_ledger()
        self.assertTrue(out["complete"])
        self.assertEqual(out["observed_tokens"]["input_tokens"], 200)
        self.sessions["c"]["events"] = [call("a", 200)]
        self.assertIsNone(self.run_ledger()["cost_usd"])

    def test_malformed_price_is_unknown(self):
        for prices in [{"model": "bad"}, ["bad"]]:
            out = ledger(self.sessions, "r", prices, "2026-09-29")
            self.assertFalse(out["complete"]); self.assertIsNone(out["cost_usd"])

    def compaction_events(self):
        normal = call("normal", 100, 30, 10)
        compact = call("compact", 200, 100, 20)
        compact["payload"]["thread_token_usage"] = {
            "input_tokens": 300, "cached_input_tokens": 130, "output_tokens": 30}
        snapshot = {"payload": {"type": "token_count", "info": {
            "total_token_usage": copy.deepcopy(normal["payload"]["usage"])}}}
        return [normal, snapshot, compact, {"type": "compacted"}, snapshot]

    def test_attested_compaction_is_charged_and_reconciled(self):
        self.sessions = {"r": {"model": "model", "events": self.compaction_events()}}
        out = self.run_ledger()
        self.assertTrue(out["complete"], out["issues"])
        self.assertEqual(out["ledger_version"], 2)
        self.assertEqual(out["observed_tokens"]["input_tokens"], 300)
        self.assertEqual(out["compaction_tokens"]["input_tokens"], 200)
        self.assertAlmostEqual(out["cost_usd"], (170*2 + 130*.1 + 30*10)/1e6)
        self.assertEqual(out["reconciliations"][0]["session_id"], "r")

    def test_compaction_without_thread_attestation_stays_unknown(self):
        events = self.compaction_events()
        del events[2]["payload"]["thread_token_usage"]
        self.sessions = {"r": {"model": "model", "events": events}}
        self.assertIsNone(self.run_ledger()["cost_usd"])

    def test_wrong_thread_or_ordinary_view_stays_unknown(self):
        for index, key in [(2, "thread_token_usage"), (1, "usage")]:
            events = self.compaction_events()
            if index == 2:
                events[index]["payload"][key]["input_tokens"] += 1
            else:
                events[index]["payload"]["info"]["total_token_usage"]["input_tokens"] += 1
            self.sessions = {"r": {"model": "model", "events": events}}
            self.assertIsNone(self.run_ledger()["cost_usd"])

    def test_nonadjacent_call_cannot_explain_compaction(self):
        events = self.compaction_events()
        events.insert(3, {"type": "unrelated"})
        self.sessions = {"r": {"model": "model", "events": events}}
        self.assertIsNone(self.run_ledger()["cost_usd"])

    def test_duplicate_compaction_charged_once(self):
        events = self.compaction_events()
        events.append(events[2])
        self.sessions = {"r": {"model": "model", "events": events}}
        out = self.run_ledger()
        self.assertTrue(out["complete"], out["issues"])
        self.assertEqual(out["observed_tokens"]["input_tokens"], 300)

    def test_optional_compaction_usage_requires_full_attestation(self):
        events = self.compaction_events()
        for e in [events[0], events[2]]:
            e["payload"]["usage"]["reasoning_output_tokens"] = 2
        events[1]["payload"]["info"]["total_token_usage"]["reasoning_output_tokens"] = 2
        events[2]["payload"]["thread_token_usage"]["reasoning_output_tokens"] = 4
        self.sessions = {"r": {"model": "model", "events": events}}
        self.assertTrue(self.run_ledger()["complete"])
        del events[2]["payload"]["thread_token_usage"]["reasoning_output_tokens"]
        self.assertIsNone(self.run_ledger()["cost_usd"])

    def test_multiple_compactions_and_later_ordinary_call(self):
        events = self.compaction_events()
        compact = call("second-compaction", 200, 100, 20)
        compact["payload"]["thread_token_usage"] = {
            "input_tokens": 500, "cached_input_tokens": 230, "output_tokens": 50}
        final = call("final", 100, 30, 10)
        final["payload"]["thread_token_usage"] = {
            "input_tokens": 600, "cached_input_tokens": 260, "output_tokens": 60}
        events += [compact, {"type": "compacted"}, final, {"payload": {
            "type": "token_count", "info": {"total_token_usage": {
                "input_tokens": 200, "cached_input_tokens": 60, "output_tokens": 20}}}}]
        self.sessions = {"r": {"model": "model", "events": events}}
        out = self.run_ledger()
        self.assertTrue(out["complete"], out["issues"])
        self.assertEqual(out["compaction_tokens"]["input_tokens"], 400)
        self.assertEqual(out["observed_tokens"]["input_tokens"], 600)

    def test_duplicate_before_compaction_keeps_marker_classification(self):
        events = self.compaction_events()
        events.insert(2, copy.deepcopy(events[2]))
        self.sessions = {"r": {"model": "model", "events": events}}
        out = self.run_ledger()
        self.assertTrue(out["complete"], out["issues"])
        self.assertEqual(out["observed_tokens"]["input_tokens"], 300)
        self.assertEqual(out["compaction_tokens"]["input_tokens"], 200)

    def test_conflicting_duplicate_attestation_stays_unknown(self):
        events = self.compaction_events()
        bad = copy.deepcopy(events[2])
        bad["payload"]["thread_token_usage"]["input_tokens"] += 1
        events.extend([bad, copy.deepcopy(events[2])])
        self.sessions = {"r": {"model": "model", "events": events}}
        out = self.run_ledger()
        self.assertIsNone(out["cost_usd"])
        self.assertTrue(any("conflicting duplicate thread usage" in i for i in out["issues"]))



if __name__ == "__main__":
    unittest.main()
