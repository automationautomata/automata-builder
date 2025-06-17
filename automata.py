from typing import Sequence

Table = dict[str, dict[str]]

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

        self.states = set(states) if states else None
        self.initial_state_ = initial_state

        self.input_alphabet_ = {}
        if input_alphabet:
            self.input_alphabet_.update({smb: i for i, smb in enumerate(input_alphabet, 1)})
            
        self.output_alphabet_ = {}
        if output_alphabet:
            self.output_alphabet_.update({smb: i for i, smb in enumerate(output_alphabet, 1)})

        self.transitions_ = {
            smb: dict.fromkeys(states, '') for smb in self.input_alphabet_
        }
        self.output_function_ = {
            smb: dict.fromkeys(states, '') for smb in self.input_alphabet_
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

    def reset_input_order(self, ordered: list[str]) -> None:
        if len(ordered) != len(self.input_alphabet_):
            raise ValueError()
        if len(set(ordered) ^ set(self.input_alphabet_)) != 0:
            raise ValueError()
        self.input_alphabet_ = {symb: i for i, symb in enumerate(ordered, 1)}

    def reset_output_order(self, ordered: list[str]) -> None:
        if len(ordered) != len(self.output_alphabet_):
            raise ValueError()
        if len(set(ordered) ^ set(self.output_alphabet_)) != 0:
            raise ValueError()
        self.output_alphabet_ = {symb: i for i, symb in enumerate(ordered, 1)}

    @property
    def transitions(self) -> Table:
        return self.transitions_

    @transitions.setter
    def transitions(self, transitions: Table) -> None:
        if len(self.states ^ transitions.keys()) != 0:
            raise ValueError()

        for _, t in transitions.items():
            diff = self.input_alphabet_.keys() ^ t.keys()
            if len(diff) != 0:
                raise ValueError()

    @property
    def output_function(self) -> Table:
        return self.output_function_

    @output_function.setter
    def output_function(self, output_function: Table) -> None:
        if len(self.states ^ output_function.keys()) != 0:
            raise ValueError()

        for _, t in output_function.items():
            diff = self.input_alphabet_.keys() ^ t.keys()
            if len(diff) != 0:
                raise ValueError()

    def add_state(self, state: str) -> None:
        self.states.add(state)

    def add_input_symbol(self, symbol: str) -> None:
        self.input_alphabet_[symbol] = self.input_alphabet_.get(
            symbol, len(self.input_alphabet_) + 1
        )

    def add_output_symbol(self, symbol: str) -> None:
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

        self.transitions_[input_symbol][input_state] = output_state
        self.output_function_[input_symbol][input_state] = output_symbol

    def transition(self, symbol: str, state: str) -> tuple[str, str]:
        s = self.transitions_[symbol][state]
        o = self.output_function_[symbol][state]
        return s, o

    def read(self, word: str) -> str:
        if len(set(word) ^ self.input_alphabet_.keys()) == 0:
            raise ValueError(
                "The input word contains symbols not from the input alphabet"
            )
        if not self.initial_state:
            raise ValueError("Initial state must be setted")

        output = ""
        s = self.initial_state
        for w in word:
            s, o = self.transition(w, s)
            output += f"{output}{o}"
        return output

    def to_number(self, word: str) -> tuple[float, float]:
        out = self.read(word)

        n = self.input_alphabet_
        in_ = sum(self.input_alphabet_[word[i]] / n**i for i in range(1, len(word) + 1))

        m = self.input_alphabet_
        out_ = sum(self.output_alphabet_[out[i]] / m**i for i in range(1, len(out) + 1))

        return in_, out_

    def detailed_verificatin(self) -> list[str]:
        errors = []
        if not self.initial_state:
            errors.append("There is no initial state")

        for state, tranistions in self.transitions_.items():
            diff = self.input_alphabet_.keys() - tranistions.keys()
            if len(diff) != 0:
                errors.append(
                    f"State {state} must have transition for {diff} input symbols"
                )

        for state, tranistions in self.transitions_.items():
            diff = self.input_alphabet_.keys() - tranistions.keys()
            if len(diff) != 0:
                errors.append(
                    f"State {state} must have output for {diff} input alphabet"
                )

        return errors
