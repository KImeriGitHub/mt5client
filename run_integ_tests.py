#!/usr/bin/env python3
"""
Run integration tests for darwinexclient without spawning a subprocess.

Integration tests require actual MT5 connection and credentials.
These tests are designed to work with real MT5 demo accounts.

Usage:
    python run_integ_tests.py                          # Run all integration tests
    python run_integ_tests.py test_connection          # Run connection tests only
    python run_integ_tests.py test_orders_and_positions # Run orders/positions tests only
    python run_integ_tests.py tests/integ_tests/test_connection.py  # Run specific test file
    python run_integ_tests.py -k "pattern" -- -x       # Pass extra pytest args after '--'
"""
import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Import pytest for in-process execution
import pytest

def setup_logging():
    """Setup logging for integration tests with dedicated log directory."""
    project_root = Path(__file__).parent
    logs_dir = project_root / "logs" / "dev"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = logs_dir / f"integ_test_run_{timestamp}.log"

    # Avoid duplicate handlers on re-runs
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,  # Python 3.8+: reset existing handlers
    )

    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("INTEGRATION TEST RUN STARTED")
    logger.info("="*60)
    logger.info(f"Log file: {log_file}")
    logger.info(f"Test account: mt5demo_acc_usd")
    logger.info("NOTE: These tests require MT5 installation and valid credentials")
    logger.info("-"*60)
    return logger, log_file

def check_prerequisites():
    """Check if integration test prerequisites are met."""
    logger = logging.getLogger(__name__)
    
    # Check if credential files exist
    credentials_path = Path("secrets/mt5_acc_cred.yaml")
    config_path = Path("secrets/mt5_config.ini")
    
    missing_files = []
    if not credentials_path.exists():
        missing_files.append(str(credentials_path))
    if not config_path.exists():
        missing_files.append(str(config_path))
    
    if missing_files:
        logger.warning("Missing credential files: %s", ", ".join(missing_files))
        logger.warning("Integration tests may be skipped due to missing credentials")
    else:
        logger.info("✓ Credential files found")
    
    # Check if MT5 is likely available (we can't check this directly without importing)
    try:
        import MetaTrader5
        logger.info("✓ MetaTrader5 module is available")
    except ImportError:
        logger.warning("MetaTrader5 module not found - integration tests will be skipped")
    
    return True

def run_integ_tests(target: str | None, extra_pytest_args: list[str]):
    """Run integration tests with proper setup and error handling."""
    logger, log_file = setup_logging()

    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Check prerequisites
    check_prerequisites()

    # Resolve target - default to integration tests directory
    if target is None:
        target = "tests/integ_tests"
    else:
        # Accept various path formats
        p = Path(target)
        if not p.exists():
            # Try with tests/integ_tests/ prefix
            p = Path("tests/integ_tests") / target
            if not p.exists():
                # Try with .py extension
                p = Path("tests/integ_tests") / f"{target}.py"
                if not p.exists():
                    # Fallback to original
                    p = Path(target)
        target = str(p)

    # Build pytest args with integration test specific settings
    args = [
        "-v",
        "--tb=long",  # More detailed tracebacks for integration tests
        "-s",  # Don't capture output (useful for integration test debugging)
        f"--log-file={log_file}",
        "--log-file-level=INFO",
        "--log-cli-level=INFO",  # Show logs in console during test run
        target,
        *extra_pytest_args,
    ]

    logger.info("Running integration tests with pytest args: %s", " ".join(args))
    logger.info("Target: %s", target)
    logger.info("="*60)

    try:
        # Run in-process, get exit code directly
        rc = pytest.main(args)
        
        logger.info("="*60)
        if rc == 0:
            logger.info("✓ INTEGRATION TESTS PASSED")
        else:
            logger.error("✗ INTEGRATION TESTS FAILED (exit code: %s)", rc)
        logger.info("="*60)
        
        return rc
        
    except KeyboardInterrupt:
        logger.warning("Integration test run interrupted by user")
        return 1
    except Exception as e:
        logger.exception("Error running integration tests: %s", e)
        return 1
    finally:
        logger.info("Integration test run completed")
        logger.info("Log file saved to: %s", log_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run integration tests for darwinexclient",
        epilog="""
Examples:
  python run_integ_tests.py                    # Run all integration tests
  python run_integ_tests.py test_connection    # Run connection tests
  python run_integ_tests.py test_orders_and_positions  # Run orders/positions tests
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "test_target", 
        nargs="?", 
        help="Test target: test file name (without .py), or specific test file path (optional)"
    )
    # Everything after '--' is passed straight to pytest
    parser.add_argument(
        "--", 
        dest="pytest_args", 
        nargs=argparse.REMAINDER, 
        help="Additional arguments passed to pytest"
    )

    args = parser.parse_args()
    extra = args.pytest_args or []

    sys.exit(run_integ_tests(args.test_target, extra))