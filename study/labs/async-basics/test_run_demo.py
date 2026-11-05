import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("run_demo.py")


class AsyncTaskLifecycleTest(unittest.TestCase):
    def test_task_runs_after_create_task_and_await_waits_for_completion(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.stdout.splitlines(),
            [
                "main:before-create",
                "main:after-create",
                "child:start",
                "child:end",
                "main:after-await",
            ],
        )


if __name__ == "__main__":
    unittest.main()
