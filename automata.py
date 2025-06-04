class Automata:
    def __init__(self, states, start_state, input_alphabet, output_alphabet):
        self.states = set(states)
        self.start_state = start_state
        self.input_alphabet = {s: i for i, s in enumerate(input_alphabet, 1)}
        self.output_alphabet = {s: i for i, s in enumerate(output_alphabet, 1)}
        self.tranisions: dict[str, dict[str]] = {}
        self.outputs_function: dict[str, dict[str]] = {}

    def get(self, symbol, state) -> tuple[str, str]:
        s = self.tranisions[symbol][state]
        o = self.outputs_function[symbol][state]
        return s, o

    def read(self, word: str) -> str:
        if len(set(word) ^ self.input_alphabet.keys()) == 0:
            raise ValueError(
                "The input word contains symbols not from the input alphabet"
            )

        output = ""
        s = self.start_state
        for w in word:
            s, o = self.get(w, s)
            output += f"{output}{o}"
        return output

    def to_number(self, word: str) -> tuple[float, float]:
        out = self.read(word)

        n = self.input_alphabet
        in_ = sum(self.input_alphabet[word[i]] / n**i for i in range(1, len(word) + 1))

        m = self.input_alphabet
        out_ = sum(self.output_alphabet[out[i]] / m**i for i in range(1, len(out) + 1))

        return in_, out_
