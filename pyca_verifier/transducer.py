"""Executable two-way deterministic finite transducers (paper Definition 1.7).

The interpreter has an input head and an append-only output, but no work tape.
Only ``state`` and the symbol beneath the head are passed to the transition
function.  Interpreter bookkeeping is diagnostic, never machine-accessible.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Generic, Hashable, Iterable, Literal, TypeVar


LEFT_END = "⊢"
RIGHT_END = "⊣"
Move = Literal["L", "S", "R"]
State = TypeVar("State", bound=Hashable)
_MOVE_OFFSET = {"L": -1, "S": 0, "R": 1}


class TransducerDefinitionError(ValueError):
    """An executed transition violates the declared machine definition."""


@dataclass(frozen=True, slots=True)
class FixedControlSpec(Generic[State]):
    """A fixed finite state domain, independent of the input length.

    An explicit state set is the strongest executable specification.  For a
    large product of finite domains, ``validator`` may recognize legal states
    without materializing the product.  In that case ``state_bound`` and the
    finiteness of the predicate's domain remain obligations of the compiler;
    an arbitrary Python predicate is not a proof of finiteness.
    """

    state_bound: int
    validator: Callable[[State], bool]
    description: str = "Declared fixed finite state domain"

    def __post_init__(self) -> None:
        if isinstance(self.state_bound, bool) or not isinstance(self.state_bound, int):
            raise ValueError("state_bound must be a positive integer")
        if self.state_bound <= 0:
            raise ValueError("state_bound must be a positive integer")
        if not callable(self.validator):
            raise TypeError("validator must be callable")

    @classmethod
    def enumerated(cls, states: Iterable[State]) -> FixedControlSpec[State]:
        domain = frozenset(states)
        return cls(len(domain), domain.__contains__, "Explicit finite state set")


@dataclass(frozen=True, slots=True)
class Transition(Generic[State]):
    state: State
    move: Move
    output: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TraceStep(Generic[State]):
    index: int
    head: int
    symbol: str
    state: State
    next_state: State
    move: Move
    output: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RunResult(Generic[State]):
    status: Literal["halted", "loop", "step_limit"]
    output: tuple[str, ...] | None
    steps: int
    head: int
    state: State
    trace: tuple[TraceStep[State], ...] = ()

    @property
    def halted(self) -> bool:
        return self.status == "halted"


class TwoWayTransducer(Generic[State]):
    """Read-only single input head, finite control, write-only output.

    Supply a transition callback or override ``transition``.  The callback must
    be pure: hidden counters, mutable closure state, external tape queries, or
    access to the output would change the computational model.  The interpreter
    checks domains and executed endmarker transitions; it cannot establish the
    purity of an arbitrary Python callable.
    """

    def __init__(
        self,
        *,
        input_alphabet: Iterable[str],
        output_alphabet: Iterable[str],
        initial_state: State,
        halt_state: State,
        control: FixedControlSpec[State],
        transition: Callable[[State, str], Transition[State]] | None = None,
        max_output_per_transition: int = 1,
    ) -> None:
        self.input_alphabet = frozenset(input_alphabet)
        self.output_alphabet = frozenset(output_alphabet)
        if any(not isinstance(s, str) for s in self.input_alphabet | self.output_alphabet):
            raise TypeError("Alphabet symbols must be strings")
        if LEFT_END in self.input_alphabet or RIGHT_END in self.input_alphabet:
            raise ValueError("Input alphabet must exclude the two endmarkers")
        if (
            isinstance(max_output_per_transition, bool)
            or not isinstance(max_output_per_transition, int)
            or max_output_per_transition < 0
        ):
            raise ValueError("max_output_per_transition must be a nonnegative integer")
        self.initial_state = initial_state
        self.halt_state = halt_state
        self.control = control
        self.max_output_per_transition = max_output_per_transition
        self._transition = transition
        self._validate_state(initial_state)
        self._validate_state(halt_state)
        if initial_state == halt_state:
            raise ValueError("Initial and halting states must be distinct")

    @property
    def finite_state_bound(self) -> int:
        return self.control.state_bound

    def transition(self, state: State, symbol: str) -> Transition[State]:
        if self._transition is None:
            raise NotImplementedError("Supply or override the transition function")
        return self._transition(state, symbol)

    def _validate_state(self, state: State) -> None:
        try:
            hash(state)
        except TypeError as error:
            raise TransducerDefinitionError("Control states must be hashable") from error
        if not self.control.validator(state):
            raise TransducerDefinitionError(f"State outside declared finite control: {state!r}")

    def _validate_transition(self, instruction: Transition[State], symbol: str) -> None:
        if not isinstance(instruction, Transition):
            raise TransducerDefinitionError("Transition function must return Transition")
        self._validate_state(instruction.state)
        if instruction.move not in ("L", "S", "R"):
            raise TransducerDefinitionError(f"Invalid input-head movement: {instruction.move!r}")
        if symbol == LEFT_END and instruction.move == "L":
            raise TransducerDefinitionError("Input head cannot move left of the left endmarker")
        if symbol == RIGHT_END and instruction.move == "R":
            raise TransducerDefinitionError("Input head cannot move right of the right endmarker")
        if not isinstance(instruction.output, tuple):
            raise TransducerDefinitionError("Transition output must be a fixed tuple of symbols")
        if len(instruction.output) > self.max_output_per_transition:
            raise TransducerDefinitionError("Transition output exceeds its fixed declared bound")
        if any(s not in self.output_alphabet for s in instruction.output):
            raise TransducerDefinitionError("Transition emitted a symbol outside the output alphabet")

    def run(
        self,
        input_word: Iterable[str],
        *,
        max_steps: int | None = None,
        trace: bool = False,
        detect_loops: bool = True,
        loop_states: Iterable[State] = (),
        memoize_transitions: bool = False,
    ) -> RunResult[State]:
        """Interpret the machine from the left endmarker.

        A repeated ``(state, head)`` proves a nonhalting loop, even if that loop
        writes output.  Nonhalting runs have undefined output, represented by
        ``None``.  A smaller user step limit gives an inconclusive diagnostic,
        not rejection.  Disabling explicit loop tracking saves interpreter
        memory; the fixed-control configuration bound still applies. Known
        absorbing ``loop_states`` are checked against the actual instruction
        before reporting a loop without allocating a visited-state set.

        ``memoize_transitions`` reuses at most 16,384 validated instructions
        within this run. It requires a pure transition and fixed validator,
        with immutable states. Every input-head move, output, trace entry,
        and diagnostic step is still executed individually. The cache is
        interpreter bookkeeping and is never available to the machine.
        """
        if max_steps is not None and (
            isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 0
        ):
            raise ValueError("max_steps must be a nonnegative integer or None")
        if type(memoize_transitions) is not bool:
            raise TypeError("memoize_transitions must be a boolean")
        word = tuple(input_word)
        if any(symbol not in self.input_alphabet for symbol in word):
            raise ValueError("Input contains a symbol outside the input alphabet")
        tape = (LEFT_END, *word, RIGHT_END)
        known_loop_states = frozenset(loop_states)
        for known_state in known_loop_states:
            self._validate_state(known_state)
        head = 0
        state = self.initial_state
        steps = 0
        output: list[str] = []
        trace_steps: list[TraceStep[State]] = []
        visited: set[tuple[State, int]] | None = set() if detect_loops else None
        configuration_bound = self.finite_state_bound * len(tape)

        def validated_transition(state: State, symbol: str) -> Transition[State]:
            instruction = self.transition(state, symbol)
            self._validate_transition(instruction, symbol)
            return instruction

        execute_transition = (
            lru_cache(maxsize=16384)(validated_transition)
            if memoize_transitions else validated_transition
        )

        def result(status: Literal["halted", "loop", "step_limit"]) -> RunResult[State]:
            return RunResult(
                status, tuple(output) if status == "halted" else None,
                steps, head, state, tuple(trace_steps),
            )

        while state != self.halt_state:
            if visited is not None:
                configuration = (state, head)
                if configuration in visited:
                    return result("loop")
                visited.add(configuration)
            if steps >= configuration_bound:
                # The declared finite state domain supplies the pigeonhole
                # bound when explicit interpreter loop tracking is disabled.
                return result("loop")
            if max_steps is not None and steps >= max_steps:
                return result("step_limit")
            symbol = tape[head]
            instruction = execute_transition(state, symbol)
            known_loop = state in known_loop_states
            if known_loop and (instruction.state != state or instruction.move != "S"):
                raise TransducerDefinitionError(
                    "A declared loop state must execute a stationary self-loop"
                )
            if trace:
                trace_steps.append(TraceStep(
                    steps, head, symbol, state, instruction.state,
                    instruction.move, instruction.output,
                ))
            output.extend(instruction.output)
            head += _MOVE_OFFSET[instruction.move]
            state = instruction.state
            steps += 1
            if known_loop:
                return result("loop")
        return result("halted")
