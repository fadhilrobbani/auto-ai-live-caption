#!/usr/bin/env python3
"""
Test runner script for Auto AI Live Caption.
Discovers and runs all unit & integration tests, then exits cleanly
without PySide6 / Qt6 C++ headless static destructor conflicts.
"""

import os
import sys
import unittest

# Ensure offscreen Qt platform for headless environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"


def main():
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Clean exit without PySide6 atexit static destructor collisions on Linux
    os._exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
