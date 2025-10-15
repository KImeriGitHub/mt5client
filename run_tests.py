#!/usr/bin/env python3
"""
Run tests for darwinexclient without spawning a subprocess.

Usage:
    python run_tests.py                        # Run all tests
    python run_tests.py tests/test_mt_init.py  # Run a specific file
    python run_tests.py -k "pattern" -- -x     # Pass extra pytest args after '--'
"""
import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime

# 1) Import pytest for in-process execution
import pytest

def setup_logging():
    project_root = Path(__file__).parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"test_run_{timestamp}.log"

    # 2) Avoid duplicate handlers on re-runs
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,  # Python 3.8+: reset existing handlers
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Test run started - Log file: {log_file}")
    return logger, log_file

def run_tests(target: str | None, extra_pytest_args: list[str]):
    logger, log_file = setup_logging()

    project_root = Path(__file__).parent
    os.chdir(project_root)

    # 3) Resolve target
    if target is None:
        target = "tests"
    else:
        # accept both with/without "tests/" prefix
        p = Path(target)
        if not p.exists():
            p = Path("tests") / target
        target = str(p)

    # 4) Build pytest args; also mirror logs to the file via pytest’s logging plugin
    args = [
        "-v",
        "--tb=short",
        f"--log-file={log_file}",
        "--log-file-level=INFO",
        target,
        *extra_pytest_args,
    ]

    logger.info("Running pytest with: %s", " ".join(args))
    logger.info("-" * 50)

    try:
        # 5) Run in-process, get exit code directly
        rc = pytest.main(args)
        logger.info("Test run completed with exit code: %s", rc)
        return rc
    except KeyboardInterrupt:
        logger.warning("Test run interrupted by user")
        return 1
    except Exception as e:
        logger.exception("Error running tests: %s", e)
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests for darwinexclient")
    parser.add_argument("test_file", nargs="?", help="Specific test file (optional)")
    # everything after '--' is passed straight to pytest
    parser.add_argument("--", dest="pytest_args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    args = parser.parse_args()
    extra = args.pytest_args or []

    sys.exit(run_tests(args.test_file, extra))
