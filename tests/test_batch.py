"""The timing of what is sent to Jarvis (custom_components/jarvis/batch.py), with no Home Assistant.

Run: python3 -m unittest discover tests
"""

import importlib.util
import pathlib
import unittest

# Loaded by path: the package's __init__ needs Home Assistant, the timing does not.
_spec = importlib.util.spec_from_file_location("batch", pathlib.Path(__file__).parent.parent / "custom_components" / "jarvis" / "batch.py")
batch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(batch)
Batcher = batch.Batcher


class BatchTest(unittest.TestCase):
    def test_ordinary_changes_wait_for_the_gap(self):
        b = Batcher(gap=300)
        b.take(0)  # sent at 0
        b.add("light.study", "off", "on", urgent=False, now=10)
        self.assertFalse(b.due(100))
        self.assertTrue(b.due(300))
        self.assertEqual(b.take(300), [{"id": "light.study", "from": "off", "to": "on"}])
        self.assertFalse(b.due(301))

    def test_urgent_goes_within_seconds(self):
        b = Batcher(gap=300, urgent_delay=2)
        b.take(0)
        b.add("light.study", "off", "on", urgent=False, now=10)
        b.add("lock.front_door", "locked", "unlocked", urgent=True, now=20)
        self.assertFalse(b.due(21))
        self.assertTrue(b.due(22))
        sent = b.take(22)
        self.assertEqual({c["id"] for c in sent}, {"light.study", "lock.front_door"}, "the rest goes with it")

    def test_one_entity_once_first_from_latest_to(self):
        b = Batcher()
        b.add("cover.garage", "closed", "opening", urgent=False, now=0)
        b.add("cover.garage", "opening", "open", urgent=False, now=5)
        self.assertEqual(b.take(400), [{"id": "cover.garage", "from": "closed", "to": "open"}])

    def test_changed_back_is_not_sent(self):
        b = Batcher()
        b.add("binary_sensor.hall_motion", "off", "on", urgent=False, now=0)
        b.add("binary_sensor.hall_motion", "on", "off", urgent=False, now=60)
        self.assertEqual(b.take(400), [])

    def test_a_failure_is_put_back_and_waited_out(self):
        b = Batcher(gap=0)
        b.add("light.study", "off", "on", urgent=False, now=0)
        sent = b.take(1)
        b.add("light.study", "on", "off", urgent=False, now=2)  # newer than what failed
        b.add("light.porch", "off", "on", urgent=False, now=2)
        b.failed(sent, now=3)
        self.assertFalse(b.due(10), "waits after a failure")
        self.assertTrue(b.due(3 + batch.FIRST_BACKOFF))
        again = {c["id"]: c for c in b.take(40)}
        self.assertEqual(again["light.study"]["to"], "off", "the newer change wins over the one put back")
        b.add("light.porch", "on", "off", urgent=False, now=41)
        b.failed([{"id": "light.x", "from": "a", "to": "b"}], now=41)
        self.assertFalse(b.due(41 + batch.FIRST_BACKOFF), "the wait doubles")
        b.succeeded()
        self.assertTrue(b.due(42))

    def test_at_most_a_batch_at_a_time(self):
        b = Batcher(gap=0, max_batch=3)
        for i in range(5):
            b.add(f"light.l{i}", "off", "on", urgent=False, now=0)
        self.assertEqual(len(b.take(1)), 3)
        self.assertEqual(b.waiting(), 2)


if __name__ == "__main__":
    unittest.main()
