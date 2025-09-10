import math
from dataclasses import dataclass
from threading import Event
from typing import Callable, Optional

from matplotlib.axes import Axes

from core.automata import Automata
from utiles.utiles import StoppableFunction, generate_colors


@dataclass
class Points:
    x: list[int]
    y: list[int]
    xlim: Optional[tuple[int, int]] = None
    ylim: Optional[tuple[int, int]] = None
    is_plot: bool = False
    color: str = "red"


def padic_to_geom(num: str, n: int, base: int) -> float:
    if base % 2 == 0:
        digit_len = len(bin(base)[2:]) - 1
        num_len = digit_len * n

        str_num = bin(num)[2::]
        if num >= 0:
            str_num = str_num.zfill(num_len)
        else:
            str_num = str_num[1::].ljust(num_len, "1")

        digits = [
            int(str_num[i : i + digit_len], base=2)
            for i in range(0, num_len, digit_len)
        ]
    else:
        digits = [0] * n
        for i in range(n):
            digits[i] = num % base
            num //= base
    return sum(digits[n - i - 1] / n**i for i in range(n))


def by_function(
    func: Callable[[int], int],
    base: int,
    length: int,
) -> StoppableFunction[None, tuple[Points]]:
    def calculate(cond: Event):
        xlim = 1, base + 1
        ylim = 1, base + 1
        x, y = [], []
        for i in range(length):
            for num in range(base**i, base ** (i + 1)):
                if cond.is_set():
                    return (Points(x, y, xlim, ylim),)
                x.append(padic_to_geom(num, i, base))
                y.append(padic_to_geom(func(num), i, base))
        return (Points(x, y, xlim, ylim),)

    return calculate


def by_automata(
    automata: Automata, length: int, prefix: str, suffix: str, last_state: str
) -> StoppableFunction[None, tuple[Points]]:
    def calculate(cond: Event):
        xlim = 1, len(automata.inputs) + 1
        ylim = 1, len(automata.outputs) + 1

        x, y = [], []
        for i in range(1, length):
            pairs = automata.pairs_generator(i, prefix, suffix, last_state)
            for in_word, out_word in pairs:
                if cond.is_set():
                    return (Points(x, y, xlim, ylim),)
                x.append(automata.input_number(in_word))
                y.append(automata.output_number(out_word))
        return (Points(x, y, xlim, ylim),)

    return calculate


def curves(automata: Automata) -> StoppableFunction[None, tuple[Points]]:
    sorted_inputs = sorted(automata.inputs, key=lambda x: automata.inputs[x])
    k = len(automata.states)
    m = len(automata.outputs)

    def calculate(cond: Event):
        x = [0] * k
        x[0] = 1
        for i in range(1, k):
            x[i] = x[i - 1] + 1 / 2**i

        plots = []
        colors = generate_colors(len(sorted_inputs))

        def f(x, deltas):
            res = 0
            for delta in deltas:
                res += (m + 1) ** -(math.log2(2 / (2 - x)) - 1 - delta)
            return res

        for in_ in sorted_inputs:
            if cond.is_set():
                break

            out_word = automata.read(in_ * k)
            deltas = {num: [] for num in automata.outputs.values()}
            for j in range(k):
                out = automata.outputs[out_word[-j - 1]]
                deltas[out].append((k - 1 - j))

            y = [0] * len(x)
            for i in range(len(x)):
                if cond.is_set():
                    return tuple(plots)

                y[i] = sum(out * f(x[i], vals) for out, vals in deltas.items())

            plots.append(Points(x, y, color=next(colors), is_plot=True))

        return tuple(plots)

    return calculate


def draw(
    ax: Axes,
    *points: Points,
    border_shift: int = 0.2,
    title: str = "",
    grid: bool = True,
) -> None:
    ax.set_title(title)
    ax.grid(grid)

    xmins, xmaxs, ymins, ymaxs = [], [], [], []
    for p in points:
        if not p.is_plot:
            ax.scatter(p.x, p.y, color=p.color, s=5)
        else:
            ax.plot(p.x, p.y, color=p.color)

        if p.xlim is not None:
            xmins.append(p.xlim[0] - border_shift)
            xmaxs.append(p.xlim[1] + border_shift)
        if p.ylim is not None:
            ymins.append(p.ylim[0] - border_shift)
            ymaxs.append(p.ylim[1] + border_shift)

    if xmins and xmaxs:
        ax.set_xlim(min(xmins), max(xmaxs))
    if ymins and ymaxs:
        ax.set_ylim(min(ymins), max(ymaxs))

