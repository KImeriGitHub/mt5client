"""Integration tests for darwinexclient.

This package contains integration tests that require actual MT5 connections
and real demo account credentials.

These tests are designed to:
- Test actual MT5 connectivity using the mt5demo_acc_usd account
- Verify that client classes work with real MT5 data
- Ensure proper error handling when MT5 is not available

Prerequisites:
- MetaTrader5 Python package installed
- Valid MT5 demo account credentials in secrets/
- MT5 terminal installed (for full integration testing)
"""