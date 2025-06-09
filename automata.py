from typing import Sequence


class Automata:
    def __init__(
        self,
        states: Sequence[str] = None,
        initial_state: str = "",
        input_alphabet: Sequence[str] = None,
        output_alphabet: Sequence[str] = None,
    ):
        if states and initial_state not in self.states:
            raise ValueError("Start state must be in given states")

        self.states = set(states) if states else None
        self.initial_state_ = initial_state

        if input_alphabet:
            self.input_alphabet = {smb: i for i, smb in enumerate(input_alphabet, 1)}
        else:
            self.input_alphabet = {}

        if output_alphabet:
            self.output_alphabet = {smb: i for i, smb in enumerate(output_alphabet, 1)}
        else:
            self.output_alphabet = {}

        self.transitions = {smb: {s: "" for s in states} for smb in self.input_alphabet}
        self.output_function = {
            smb: {s: "" for s in states} for smb in self.input_alphabet
        }

    def add_state(self, state: str):
        self.states.add(state)

    def add_input_symbol(self, symbol: str):
        self.input_alphabet[symbol] = self.input_alphabet.get(
            symbol, len(self.input_alphabet) + 1
        )

    def add_output_symbol(self, symbol: str):
        self.output_alphabet[symbol] = self.output_alphabet.get(
            symbol, len(self.output_alphabet) + 1
        )

    @property
    def initial_state(self) -> str:
        return self.initial_state_

    @initial_state.setter
    def initial_state(self, state: str) -> bool:
        if state not in self.states:
            return False
        self.initial_state_ = state
        return True
    
    def verify(self) -> bool:
        if not self.initial_state:
            return False
        
        n = len(self.input_alphabet)
        m = len(self.states)
        if len(self.transitions) != n or len(self.output_function) != n:
            return False

        transitions_valid = all(len(t) == m for t in self.transitions.values())
        output_valid = all(len(outs) == m for outs in self.output_function.values())

        return output_valid or transitions_valid

    def add_transition(
        self, input_symbol: str, input_state: str, output_state: str, output_symbol: str
    ):
        if input_symbol not in self.input_alphabet:
            raise ValueError("Input symbol must be in input alphabet")
        if input_state not in self.states:
            raise ValueError("Input state must be in states")
        if output_state not in self.states:
            raise ValueError("Output state must be in states")
        if output_symbol not in self.output_alphabet:
            raise ValueError("Output symbol must be in output alphabet")

        self.transitions[input_symbol][input_state] = output_state
        self.output_function[input_symbol][input_state] = output_symbol

    def transition(self, symbol: str, state: str) -> tuple[str, str]:
        s = self.transitions[symbol][state]
        o = self.output_function[symbol][state]
        return s, o

    def read(self, word: str) -> str:
        if len(set(word) ^ self.input_alphabet.keys()) == 0:
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

        n = self.input_alphabet
        in_ = sum(self.input_alphabet[word[i]] / n**i for i in range(1, len(word) + 1))

        m = self.input_alphabet
        out_ = sum(self.output_alphabet[out[i]] / m**i for i in range(1, len(out) + 1))

        return in_, out_
