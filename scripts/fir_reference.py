"""Exact unsigned FIR reference. No floating point, training, or external data."""
from collections.abc import Iterable

COEFFICIENTS = (1, 2, 2, 1)
MAX_INPUT = 255
MAX_OUTPUT = MAX_INPUT * sum(COEFFICIENTS)


def fir(samples: Iterable[int]) -> list[int]:
    """Return one full-precision output per accepted sample, zero initial state.

    Time is the index in the accepted-sample stream. Idle hardware cycles are
    not zeros and must not be passed here. Reset starts a new call/history.
    """
    history = [0] * len(COEFFICIENTS)
    outputs = []
    for sample in samples:
        if type(sample) is not int or not 0 <= sample <= MAX_INPUT:
            raise ValueError("Each input must be an integer in [0, 255].")
        history = [sample, *history[:-1]]
        outputs.append(sum(h * x for h, x in zip(COEFFICIENTS, history)))
    return outputs
