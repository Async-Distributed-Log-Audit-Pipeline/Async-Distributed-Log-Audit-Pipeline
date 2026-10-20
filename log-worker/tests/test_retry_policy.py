import pytest

from processor import Outcome, ProcessResult
from retry_policy import Action, compute_delay, decide_action


class FakeRng:
    def __init__(self, factor: float):
        self.factor = factor

    def uniform(self, a: float, b: float) -> float:
        return self.factor


def test_compute_delay_growth_and_cap():
    # Test exponential delay growth without jitter (factor = 1.0)
    rng_exact = FakeRng(1.0)
    assert compute_delay(1, base=2.0, cap=60.0, rng=rng_exact) == 2.0
    assert compute_delay(2, base=2.0, cap=60.0, rng=rng_exact) == 4.0
    assert compute_delay(3, base=2.0, cap=60.0, rng=rng_exact) == 8.0
    assert compute_delay(4, base=2.0, cap=60.0, rng=rng_exact) == 16.0

    # Test cap enforcement
    assert compute_delay(10, base=2.0, cap=60.0, rng=rng_exact) == 60.0


def test_compute_delay_jitter_bounds():
    # Jitter lower bound factor 0.8
    rng_min = FakeRng(0.8)
    delay_min = compute_delay(1, base=10.0, cap=100.0, rng=rng_min)
    assert delay_min == 8.0  # 10 * 0.8

    # Jitter upper bound factor 1.2
    rng_max = FakeRng(1.2)
    delay_max = compute_delay(1, base=10.0, cap=100.0, rng=rng_max)
    assert delay_max == 12.0  # 10 * 1.2


def test_decide_action_outcomes():
    # 1. ACK outcomes
    res_completed = ProcessResult(Outcome.COMPLETED, "id-1")
    res_duplicate = ProcessResult(Outcome.SKIPPED_DUPLICATE, "id-1")
    res_permanent = ProcessResult(Outcome.FAILED_PERMANENT, "id-1", reason="bad file")

    assert decide_action(res_completed, 0, 3).action == Action.ACK
    assert decide_action(res_duplicate, 0, 3).action == Action.ACK
    assert decide_action(res_permanent, 0, 3).action == Action.ACK

    # 2. INVALID_MESSAGE -> DEAD_LETTER with failure_type "invalid_message"
    res_invalid = ProcessResult(Outcome.INVALID_MESSAGE, reason="bad json")
    dec_invalid = decide_action(res_invalid, 0, 3)
    assert dec_invalid.action == Action.DEAD_LETTER
    assert dec_invalid.failure_type == "invalid_message"

    # 3. RETRY_LATER within retry limit -> Action.RETRY
    res_retry = ProcessResult(Outcome.RETRY_LATER, "id-1", reason="db timeout")
    dec_retry_0 = decide_action(res_retry, 0, max_retries=3)
    assert dec_retry_0.action == Action.RETRY
    assert dec_retry_0.failure_type is None

    dec_retry_2 = decide_action(res_retry, 2, max_retries=3)
    assert dec_retry_2.action == Action.RETRY

    # 4. RETRY_LATER at or exceeding retry limit -> Action.DEAD_LETTER with failure_type "retries_exhausted"
    dec_retry_3 = decide_action(res_retry, 3, max_retries=3)
    assert dec_retry_3.action == Action.DEAD_LETTER
    assert dec_retry_3.failure_type == "retries_exhausted"

    dec_retry_4 = decide_action(res_retry, 4, max_retries=3)
    assert dec_retry_4.action == Action.DEAD_LETTER
    assert dec_retry_4.failure_type == "retries_exhausted"
