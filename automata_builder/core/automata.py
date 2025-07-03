import copy
from itertools import permutations
from typing import Any, Generator, Sequence

Table = dict[str, dict[str]]  # State: { Symbol: State }


class Automata:
    def __init__(
        self,
        states: Sequence[str] | None = None,
        initial_state: str = "",
        input_alphabet: Sequence[str] | None = None,
        output_alphabet: Sequence[str] | None = None,
    ) -> None:
        if initial_state and states and initial_state not in states:
            raise ValueError("Initial state must be in given states")

        self.states = set(states) if states else set()
        self.initial_state_ = initial_state

        self.input_alphabet_ = {}
        if input_alphabet:
            self.input_alphabet_.update(
                {smb: i for i, smb in enumerate(input_alphabet, 1)}
            )

        self.output_alphabet_ = {}
        if output_alphabet:
            self.output_alphabet_.update(
                {smb: i for i, smb in enumerate(output_alphabet, 1)}
            )

        self.transitions_ = {
            s: dict.fromkeys(self.input_alphabet_, "") for s in self.states
        }
        self.output_function_ = {
            s: dict.fromkeys(self.input_alphabet_, "") for s in self.states
        }

    @property
    def initial_state(self) -> str:
        return self.initial_state_

    @initial_state.setter
    def initial_state(self, state: str) -> bool:
        if state not in self.states:
            return False
        self.initial_state_ = state
        return True

    @property
    def input_alphabet(self) -> list[str]:
        return list(self.input_alphabet_.keys())

    @property
    def output_alphabet(self) -> list[str]:
        return list(self.output_alphabet_.keys())

    @property
    def transitions(self) -> Table:
        return copy.deepcopy(self.transitions_)

    @transitions.setter
    def transitions(self, transitions: Table) -> None:
        if len(self.states ^ transitions.keys()) != 0:
            raise ValueError()

        for _, state_tranistions in transitions.items():
            if len(self.input_alphabet_ ^ state_tranistions.keys()) == 0:
                raise ValueError()
            empty_tranistions = [k for k, v in state_tranistions.items() if not v]
            if len(empty_tranistions) != 0:
                raise ValueError()

        self.transitions = copy.deepcopy(transitions)

    @property
    def output_function(self) -> Table:
        return copy.deepcopy(self.output_function_)

    @output_function.setter
    def output_function(self, output_function: Table) -> None:
        if len(self.states ^ output_function.keys()) != 0:
            raise ValueError()

        for _, state_tranistions in output_function.items():
            if len(self.input_alphabet_ ^ state_tranistions.keys()) == 0:
                raise ValueError()
            empty_tranistions = [k for k, v in state_tranistions.items() if not v]
            if len(empty_tranistions) != 0:
                raise ValueError()
        self.output_function = copy.deepcopy(output_function)

    def reset_input_order(self, ordered: list[str]) -> None:
        if len(ordered) != len(self.input_alphabet_):
            raise ValueError()
        if len(set(ordered) ^ set(self.input_alphabet_)) != 0:
            raise ValueError()
        self.input_alphabet_ = {symb: i for i, symb in enumerate(ordered, 1)}

    def reset_output_order(self, ordered: list[str]) -> None:
        if len(ordered) != len(self.output_alphabet_):
            raise ValueError()
        if set(ordered) != set(self.output_alphabet_):
            raise ValueError()
        self.output_alphabet_ = {symb: i for i, symb in enumerate(ordered, 1)}

    def add_state(self, state: str) -> None:
        self.states.add(state)
        self.transitions_.update({state: dict.fromkeys(self.input_alphabet_, "")})
        self.output_function_.update({state: dict.fromkeys(self.input_alphabet_, "")})

    def add_input(self, symbol: str) -> None:
        if symbol in self.input_alphabet_:
            return
        self.input_alphabet_[symbol] = len(self.input_alphabet_) + 1
        for state in self.transitions_.keys():
            self.transitions_[state][symbol] = ""
            self.output_function_[state][symbol] = ""

    def add_output(self, symbol: str) -> None:
        self.output_alphabet_[symbol] = self.output_alphabet_.get(
            symbol, len(self.output_alphabet_) + 1
        )

    def add_transition(
        self, input_symbol: str, input_state: str, output_state: str, output_symbol: str
    ) -> None:
        if input_symbol not in self.input_alphabet_:
            raise ValueError("Input symbol must be in input alphabet")
        if input_state not in self.states:
            raise ValueError("Input state must be in states")
        if output_state not in self.states:
            raise ValueError("Output state must be in states")
        if output_symbol not in self.output_alphabet_:
            raise ValueError("Output symbol must be in output alphabet")

        self.transitions_[input_state][input_symbol] = output_state
        self.output_function_[input_state][input_symbol] = output_symbol

    def transition(self, symbol: str, state: str) -> tuple[str, str]:
        s = self.transitions_[state][symbol]
        o = self.output_function_[state][symbol]
        return s, o

    def __read__(self, word: str) -> str:
        """Unsafe read"""
        output = ""
        s = self.initial_state
        for w in word:
            s, o = self.transition(w, s)
            output += f"{output}{o}"
        return output

    def read(self, word: str) -> str:
        """Read with input word check"""
        if set(self.input_alphabet_.keys()).issubset(word):
            raise ValueError(
                "The input word contains symbols not from the input alphabet"
            )
        if not self.initial_state:
            raise ValueError("Initial state must be setted")

        return self.__read__(word)

    def to_number(self, word: str) -> tuple[float, float]:
        n = len(self.input_alphabet_)
        number = sum(
            self.input_alphabet_[word[i - 1]] / n**i for i in range(1, len(word) + 1)
        )
        return number

    def input_words(self, length: int) -> Generator[str, Any, None]:
        for seq in permutations(self.input_alphabet_, length):
            yield "".join(seq)

    def pairs_generator(self, length: int) -> Generator[tuple[str, str], Any, None]:
        for in_word in self.input_words(length):
            out_word = self.__read__(in_word)
            yield in_word, out_word

    def detailed_verificatin(self) -> list[str]:
        errors = []
        if not self.initial_state:
            errors.append("There is no initial state")

        for state, state_tranistions in self.transitions_.items():
            empty_tranistions = [k for k, v in state_tranistions.items() if not v]
            if len(empty_tranistions) != 0:
                errors.append(
                    f"State {state} must have transition for {', '.join(empty_tranistions)} input symbols"
                )

        for state, state_tranistions in self.output_function_.items():
            empty_tranistions = [k for k, v in state_tranistions.items() if not v]
            if len(empty_tranistions) != 0:
                errors.append(
                    f"State {state} must have output for {', '.join(empty_tranistions)} input alphabet"
                )

        return errors
