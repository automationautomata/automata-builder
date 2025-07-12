import copy
from itertools import product
from typing import Generator, Sequence, Union

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

        self.inputs = {}
        if input_alphabet:
            self.inputs.update({smb: i for i, smb in enumerate(input_alphabet, 1)})

        self.outputs = {}
        if output_alphabet:
            self.outputs.update({smb: i for i, smb in enumerate(output_alphabet, 1)})

        self.transitions_ = {s: dict.fromkeys(self.inputs, "") for s in self.states}
        self.output_function_ = {s: dict.fromkeys(self.inputs, "") for s in self.states}

    @property
    def initial_state(self) -> str:
        return self.initial_state_

    @initial_state.setter
    def initial_state(self, state: str) -> None:
        if state not in self.states:
            raise ValueError("Initial state must be in given states")
        self.initial_state_ = state

    @property
    def input_alphabet(self) -> list[str]:
        return list(self.inputs.keys())

    @property
    def output_alphabet(self) -> list[str]:
        return list(self.outputs.keys())

    @property
    def transitions(self) -> Table:
        return copy.deepcopy(self.transitions_)

    @property
    def output_function(self) -> Table:
        return copy.deepcopy(self.output_function_)

    def reset_inputs_order(self, ordered: list[str]) -> None:
        if len(ordered) != len(self.inputs):
            raise ValueError()
        if len(set(ordered) ^ set(self.inputs)) != 0:
            raise ValueError()
        self.inputs = {symb: i for i, symb in enumerate(ordered, 1)}

    def reset_outputs_order(self, ordered: list[str]) -> None:
        if len(ordered) != len(self.outputs):
            raise ValueError()
        if set(ordered) != set(self.outputs):
            raise ValueError()
        self.outputs = {symb: i for i, symb in enumerate(ordered, 1)}

    def add_state(self, state: str) -> None:
        self.states.add(state)
        self.transitions_.update({state: dict.fromkeys(self.inputs, "")})
        self.output_function_.update({state: dict.fromkeys(self.inputs, "")})

    def add_input(self, symbol: str) -> None:
        if symbol in self.inputs:
            return
        self.inputs[symbol] = len(self.inputs) + 1
        for state in self.transitions_.keys():
            self.transitions_[state][symbol] = ""
            self.output_function_[state][symbol] = ""

    def add_output(self, symbol: str) -> None:
        self.outputs[symbol] = self.outputs.get(symbol, len(self.outputs) + 1)

    def add_to_transitions(
        self, input_symbol: str, input_state: str, output_state: str
    ) -> None:
        exception = self.__check__(input_symbol, input_state, output_state)
        if exception:
            raise exception

        self.transitions_[input_state][input_symbol] = output_state

    def add_to_output_function(
        self, input_symbol: str, input_state: str, output_symbol: str
    ) -> None:
        exception = self.__check__(input_symbol, input_state, "", output_symbol)
        if exception:
            raise exception
        self.output_function_[input_state][input_symbol] = output_symbol

    def __check__(
        self,
        input_symbol: str = "",
        input_state: str = "",
        output_state: str = "",
        output_symbol: str = "",
    ) -> Exception:
        if input_symbol and input_symbol not in self.inputs:
            return ValueError("Input symbol must be in input alphabet")
        if input_state and input_state not in self.states:
            return ValueError("Input state must be in states")
        if output_symbol and output_symbol not in self.outputs:
            return ValueError("Output symbol must be in output alphabet")
        if output_state and output_state not in self.states:
            return ValueError("Output state must be in states")

    def transition(self, symbol: str, state: str) -> tuple[str, str]:
        s = self.transitions_[state][symbol]
        o = self.output_function_[state][symbol]
        return s, o

    def has_in_transitions(self, state: str, symbol: str):
        return self.transitions_[state][symbol] != ""

    def has_in_output_function(self, state: str, symbol: str):
        return self.output_function_[state][symbol] != ""

    def __read__(self, word: str) -> tuple[list[str], str]:
        states, output = [""] * (len(word) + 1), [""] * len(word)
        states[0] = self.initial_state
        for i, w in enumerate(word):
            states[i + 1], output[i] = self.transition(w, states[i])
        return states[:-1], "".join(output)

    def read(self, word: str) -> str:
        _, output = self.__read__(word)
        return output

    def to_number(self, word: str) -> tuple[float, float]:
        n = len(self.inputs) + 1
        number = sum(
            self.inputs[word[-i]] / n ** (i - 1) for i in range(1, len(word) + 1)
        )
        return number

    def words(self, length: int, prefix: str = "") -> Generator[str, None, None]:
        for seq in product(self.inputs, repeat=length):
            yield f"{prefix}{''.join(seq)}"

    def pairs_generator(
        self, length: int, input_prefix: str = "", last_state: str = ""
    ) -> Generator[tuple[str, str], None, None]:
        if last_state not in self.states:
            raise ValueError("Last state must be in given states")

        for in_word in self.words(length, input_prefix):
            states, out_word = self.__read__(in_word)
            if not last_state or states[-1] == last_state:
                yield in_word, out_word

    @staticmethod
    def detailed_build(
        initial_state: str,
        transitions: dict[str, list[str]],
        output_function: dict[str, list[str]],
    ) -> tuple[Union["Automata", None], list[str]]:
        """Builds automata and return list of errors if it's incorrect"""

        states = list(set(transitions).union(set(output_function)))
        inputs, outputs = set(), set()
        for state_tranistions in transitions.values():
            inputs.update(in_ for in_, _ in state_tranistions)

        for state_tranistions in output_function.values():
            # if some input not in transitions
            ins, outs = zip(*state_tranistions)
            inputs.update(ins)
            outputs.update(outs)

        automata = Automata(states, initial_state, sorted(inputs), sorted(outputs))

        errors = []
        if not initial_state:
            errors.append("There is no initial state")

        if len(transitions.keys() ^ output_function.keys()) != 0:
            missing_states = output_function.keys() - transitions.keys()
            if len(missing_states) != 0:
                errors.append(
                    f"States {', '.join(missing_states)} are missing in the transition function"
                )

            missing_states = transitions.keys() - output_function.keys()
            if len(missing_states) != 0:
                errors.append(
                    f"States {', '.join(missing_states)} are missing in the output function"
                )
            return None, errors

        repeated = set()
        missing_transitions = {}

        for src_state, state_tranistions in transitions.items():
            state_inputs = set()
            for in_, dst_state in state_tranistions:
                if automata.has_in_transitions(src_state, in_):
                    repeated.add(src_state)
                else:
                    automata.add_to_transitions(in_, src_state, dst_state)
                state_inputs.add(in_)
            if len(state_inputs) != len(inputs):
                missing_transitions[src_state] = inputs - state_inputs

        for src_state, state_tranistions in output_function.items():
            state_inputs = set()
            for in_, out_ in state_tranistions:
                if automata.has_in_output_function(src_state, in_):
                    repeated.add(dst_state)
                else:
                    automata.add_to_output_function(in_, src_state, out_)
                state_inputs.add(in_)
            if len(state_inputs) != len(inputs):
                missing_transitions[src_state] = inputs - state_inputs

        for state in repeated:
            errors.append(
                f"State {state} has more then one transition for the same input symbol"
            )
        for state, state_inputs in missing_transitions.items():
            errors.append(
                f"State {state} misses transitions by the {', '.join(state_inputs)} input symbols"
            )
        if len(errors) != 0:
            return None, errors
        return automata, errors
