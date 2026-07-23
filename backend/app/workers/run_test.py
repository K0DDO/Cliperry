"""Enqueue test_task and wait for the worker result."""

from __future__ import annotations

import sys
import time

from app.workers.test_tasks import test_task


def main() -> int:
    print("Sending cliperry.test_task ...")
    async_result = test_task.delay()
    print(f"task_id={async_result.id}")

    deadline = time.time() + 30
    while time.time() < deadline:
        if async_result.ready():
            if async_result.successful():
                result = async_result.get(timeout=1)
                print(f"result={result!r}")
                if result == "Cliperry worker works":
                    print("OK: backend + redis + worker are connected")
                    return 0
                print(f"FAILED: unexpected result {result!r}", file=sys.stderr)
                return 1
            print(f"FAILED: {async_result.result}", file=sys.stderr)
            return 1
        time.sleep(0.5)

    print("FAILED: timed out waiting for worker (is celery running?)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
