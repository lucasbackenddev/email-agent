"""Testes do decorator @retry."""
import pytest

from app.core.retry import RetryExhaustedError, retry


def test_retry_succeeds_after_transient_failures():
    calls = []

    @retry(times=3, backoff=2.0, initial_delay=0.01)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("transient")
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 3


def test_retry_raises_retry_exhausted_error():
    calls = []

    @retry(times=2, backoff=2.0, initial_delay=0.01)
    def always_fails():
        calls.append(1)
        raise ConnectionError("permanent")

    with pytest.raises(RetryExhaustedError):
        always_fails()
    assert len(calls) == 2


def test_retry_does_not_catch_unlisted_exceptions():
    calls = []

    @retry(times=3, backoff=2.0, initial_delay=0.01, exceptions=(ConnectionError,))
    def wrong_error():
        calls.append(1)
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        wrong_error()
    assert len(calls) == 1  # sem retry para exceção fora da lista


def test_retry_no_failure_needed():
    @retry(times=3, initial_delay=0.01)
    def fine():
        return 42

    assert fine() == 42
