import math
from dataclasses import dataclass
from threading import Event
from typing import Callable, Optional

from matplotlib.axes import Axes

from automata_builder.core.automata import Automata
from automata_builder.utiles.utiles import StoppableFunction


@dataclass
class Points:
    x: list[int]
    y: list[int]
    xlim: Optional[tuple[int, int]]
    ylim: Optional[tuple[int, int]]
    is_plot: bool = False
    color: str = "red"


def padic_to_geom(num: int, n: int, base: int) -> float:
    if base % 2 == 0:
        str_num = bin(num)[2::]
        if num < 0:
            str_num = str_num[1::]
            filling_symb = "1"
        else:
            filling_symb = "0"

        digit_len = int(math.log2(base))
        digits_num = n * digit_len

        if len(str_num) < digits_num:
            str_num = str_num.rjust(digits_num, filling_symb)
        elif len(str_num) > digits_num:
            str_num = str_num[len(str_num) - digits_num :]

        digits = [0] * digits_num
        for i, j in enumerate(range(0, len(str_num), digit_len)):
            digits[i] = int(str_num[j : j + digit_len], base=2)
    else:
        digits = [0] * n
        for i in range(n):
            if num == 0:
                break
            digits[i] = num % base
            num //= base

    res = 0
    for i in range(n):
        res += (digits[-i - 1] + 1) * (base + 1) ** -i
    return res


def by_function(
    func: Callable[[int], int],
    base: int,
    length: int,
) -> StoppableFunction[None, tuple[Points]]:
    def wrap(cond: Event):
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

    return wrap


def by_automata(
    automata: Automata, length: int, prefix: str, suffix: str, last_state: str
) -> StoppableFunction[None, tuple[Points]]:
    def warp(cond: Event):
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

    return warp


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
