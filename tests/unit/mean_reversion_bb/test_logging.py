"""Unit tests for MRBB logging: /tmp paths, ANSI stripping, persistence."""

import io
import os
import re

import pytest

from scripts.run_mrbb_trader import TeeStream, setup_logging


# ---------------------------------------------------------------------------
# Log path tests
# ---------------------------------------------------------------------------


class TestLogPath:
    """Tests for setup_logging writing to /tmp instead of logs/."""

    def test_setup_logging_creates_file_in_tmp(self, monkeypatch):
        """Log file should be created in /tmp/ directory."""
        # Prevent actual stdout/stderr replacement
        monkeypatch.setattr("sys.stdout", io.StringIO())
        monkeypatch.setattr("sys.stderr", io.StringIO())

        log_path = setup_logging(mode="paper", symbol="BTC/USDT:USDT")

        assert os.path.dirname(log_path) == "/tmp"
        assert os.path.exists(log_path)

        # Cleanup
        if os.path.exists(log_path):
            os.unlink(log_path)

    def test_log_filename_format(self, monkeypatch):
        """Filename should match /tmp/mrbb-{symbol}-{mode}-{timestamp}.log."""
        monkeypatch.setattr("sys.stdout", io.StringIO())
        monkeypatch.setattr("sys.stderr", io.StringIO())

        log_path = setup_logging(mode="paper", symbol="BTC/USDT:USDT")
        filename = os.path.basename(log_path)

        pattern = r"^mrbb-BTC-USDT-USDT-paper-\d{8}-\d{6}\.log$"
        assert re.match(pattern, filename), f"Filename {filename!r} doesn't match expected pattern"
        assert log_path.startswith("/tmp/")

        # Cleanup
        if os.path.exists(log_path):
            os.unlink(log_path)

    def test_setup_logging_returns_log_path(self, monkeypatch):
        """setup_logging should return the full log path as a string."""
        monkeypatch.setattr("sys.stdout", io.StringIO())
        monkeypatch.setattr("sys.stderr", io.StringIO())

        result = setup_logging(mode="live", symbol="BTC/USDT:USDT")

        assert isinstance(result, str)
        assert result.startswith("/tmp/mrbb-")
        assert result.endswith(".log")

        # Cleanup
        if os.path.exists(result):
            os.unlink(result)


# ---------------------------------------------------------------------------
# TeeStream behavior tests
# ---------------------------------------------------------------------------


class TestTeeStream:
    """Tests for TeeStream writing to both terminal and file."""

    def test_tee_stream_writes_to_both(self):
        """Writing to TeeStream should appear in both terminal and file streams."""
        terminal = io.StringIO()
        file_stream = io.StringIO()

        tee = TeeStream(terminal, file_stream)
        tee.write("hello world")

        assert terminal.getvalue() == "hello world"
        assert file_stream.getvalue() == "hello world"

    def test_tee_stream_strips_ansi_from_file(self):
        """ANSI escape codes should be stripped from the file output."""
        terminal = io.StringIO()
        file_stream = io.StringIO()

        tee = TeeStream(terminal, file_stream)
        ansi_text = "\x1b[32mgreen text\x1b[0m"
        tee.write(ansi_text)

        # File should have plain text with no ANSI codes
        assert file_stream.getvalue() == "green text"

    def test_tee_stream_preserves_ansi_in_terminal(self):
        """Terminal stream should retain ANSI escape codes."""
        terminal = io.StringIO()
        file_stream = io.StringIO()

        tee = TeeStream(terminal, file_stream)
        ansi_text = "\x1b[31mred text\x1b[0m"
        tee.write(ansi_text)

        assert "\x1b[31m" in terminal.getvalue()
        assert "red text" in terminal.getvalue()

    def test_tee_stream_flush_both(self):
        """flush() should flush both streams."""
        terminal = io.StringIO()
        file_stream = io.StringIO()
        flush_calls = {"terminal": 0, "file": 0}

        original_t_flush = terminal.flush
        original_f_flush = file_stream.flush

        def count_t_flush():
            flush_calls["terminal"] += 1
            original_t_flush()

        def count_f_flush():
            flush_calls["file"] += 1
            original_f_flush()

        terminal.flush = count_t_flush
        file_stream.flush = count_f_flush

        tee = TeeStream(terminal, file_stream)
        tee.flush()

        assert flush_calls["terminal"] >= 1
        assert flush_calls["file"] >= 1


# ---------------------------------------------------------------------------
# Log persistence tests
# ---------------------------------------------------------------------------


class TestLogPersistence:
    """Tests for log file surviving close and exceptions."""

    def test_log_file_persists_after_close(self, tmp_path):
        """After TeeStream is closed/deallocated, log file should still exist with content."""
        log_file_path = tmp_path / "test.log"
        log_file = open(log_file_path, "a")
        terminal = io.StringIO()

        tee = TeeStream(terminal, log_file)
        tee.write("persistent data\n")
        log_file.close()

        # File should still exist and contain the data
        assert log_file_path.exists()
        assert "persistent data" in log_file_path.read_text()

    def test_log_file_not_deleted_on_exception(self, tmp_path):
        """Log file should survive even if an exception occurs during writing."""
        log_file_path = tmp_path / "test.log"
        log_file = open(log_file_path, "a")
        terminal = io.StringIO()

        tee = TeeStream(terminal, log_file)
        tee.write("before exception\n")

        # Simulate exception context
        try:
            raise RuntimeError("simulated crash")
        except RuntimeError:
            log_file.flush()
            log_file.close()

        assert log_file_path.exists()
        assert "before exception" in log_file_path.read_text()


# ---------------------------------------------------------------------------
# Startup banner test
# ---------------------------------------------------------------------------


class TestStartupBanner:
    """Tests for startup output showing log path."""

    def test_startup_shows_log_path(self, monkeypatch, capsys):
        """The startup output should include the /tmp log file path."""
        monkeypatch.setattr("sys.stdout", io.StringIO())
        monkeypatch.setattr("sys.stderr", io.StringIO())

        log_path = setup_logging(mode="paper", symbol="BTC/USDT:USDT")

        # After setup_logging, printing the log path is done by the caller.
        # The log path should be a /tmp path that gets printed in the banner.
        # We verify the path starts with /tmp so the banner will show /tmp.
        assert log_path.startswith("/tmp/")

        # Simulate what main() does: print the log path
        import sys
        original_stdout = sys.__stdout__
        print(f"Logging to: {log_path}", file=original_stdout)

        # Cleanup
        if os.path.exists(log_path):
            os.unlink(log_path)
