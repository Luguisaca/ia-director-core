import sys
import time
import unittest

from ia_director.processes import run_bounded_process


class BoundedProcessTests(unittest.TestCase):
    def test_executes_argv_without_shell(self):
        result = run_bounded_process(
            [sys.executable, "-c", "print('fixture-ok')"], timeout_seconds=2
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "fixture-ok")
        self.assertFalse(result.timed_out)

    def test_timeout_is_observable_and_bounded(self):
        started = time.monotonic()
        result = run_bounded_process(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            timeout_seconds=0.1,
        )
        elapsed = time.monotonic() - started
        self.assertTrue(result.timed_out)
        self.assertIsNone(result.returncode)
        self.assertLess(elapsed, 1.5)

    def test_output_is_capped(self):
        result = run_bounded_process(
            [sys.executable, "-c", "print('x' * 10000)"],
            timeout_seconds=2,
            max_output_bytes=128,
        )
        self.assertTrue(result.output_truncated)
        self.assertLessEqual(len(result.stdout.encode()) + len(result.stderr.encode()), 128)

    def test_invalid_execution_bounds_fail_closed(self):
        with self.assertRaises(ValueError):
            run_bounded_process([])
        with self.assertRaises(ValueError):
            run_bounded_process([sys.executable], timeout_seconds=0)


if __name__ == "__main__":
    unittest.main()
