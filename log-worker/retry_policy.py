from dataclasses import dataclass
from enum import Enum, auto
import random
from typing import Any

from processor import Outcome, ProcessResult


class Action(Enum):
    """Actions decided by the worker retry policy for handling message outcomes."""
    ACK = auto()
    RETRY = auto()
    DEAD_LETTER = auto()


@dataclass
class Decision:
    """Action decision coupled with an optional failure type for DLQ routing."""
    action: Action
    failure_type: str | None = None  # "invalid_message", "retries_exhausted", or None


def compute_delay(retry_number: int, base: float = 2.0, cap: float = 60.0, rng: Any = None) -> float:
    """
    Computes exponential backoff delay with +/- 20% jitter.
    
    retry_number is 1-based (retry_number=1 for 1st retry attempt).
    Formula: min(cap, base * 2^(retry_number - 1)) * jitter_factor [0.8 .. 1.2]
    """
    if retry_number < 1:
        retry_number = 1

    raw_delay = min(cap, base * (2.0 ** (retry_number - 1)))

    if rng is None:
        rng = random.Random()

    jitter_factor = rng.uniform(0.8, 1.2)
    return max(0.0, raw_delay * jitter_factor)


def decide_action(result: ProcessResult, retry_count: int, max_retries: int) -> Decision:
    """
    Decides whether to ACK, RETRY, or DEAD_LETTER a message based on ProcessResult and retry attempt count.
    
    retry_count is the number of retries already performed (0 on initial delivery).
    """
    if result.outcome in (Outcome.COMPLETED, Outcome.SKIPPED_DUPLICATE, Outcome.FAILED_PERMANENT):
        return Decision(Action.ACK, failure_type=None)

    if result.outcome == Outcome.INVALID_MESSAGE:
        return Decision(Action.DEAD_LETTER, failure_type="invalid_message")

    if result.outcome == Outcome.RETRY_LATER:
        if retry_count < max_retries:
            return Decision(Action.RETRY, failure_type=None)
        else:
            return Decision(Action.DEAD_LETTER, failure_type="retries_exhausted")

    # Default fallback
    return Decision(Action.ACK, failure_type=None)
