#!/usr/bin/env python3
"""Unified test runner for reverse-flow and pojia skills."""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    start_time = time.time()
    print("=" * 70)
    print("Running Reverse Flow & Pojia Skills Test Suite")
    print(f"Python interpreter: {sys.executable}")
    print(f"Root directory: {ROOT}")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover tests in tests/
    tests_dir = ROOT / "tests"
    if tests_dir.exists():
        discovered = loader.discover(start_dir=str(tests_dir), pattern="test_*.py")
        suite.addTests(discovered)

    # Add legacy validation tests if present
    evidence_test = ROOT / "validation" / "pojia" / "test_evidence.py"
    if evidence_test.exists():
        spec = loader.discover(start_dir=str(evidence_test.parent), pattern="test_evidence.py")
        suite.addTests(spec)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"Tests run: {result.testsRun} | Failures: {len(result.failures)} | Errors: {len(result.errors)} | Skipped: {len(result.skipped)}")
    print(f"Elapsed time: {elapsed:.3f}s")
    if result.wasSuccessful():
        print("ALL TESTS PASSED [100% OK]")
        return 0
    else:
        print("TEST SUITE FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
