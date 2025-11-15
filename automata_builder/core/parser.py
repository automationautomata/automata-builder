import ast
from itertools import cycle


def _operators_() -> dict[ast.operator, str]:
    return {
        ast.Add: "+",
        ast.Sub: "-",
        ast.Mult: "*",
        ast.Div: "/",
        ast.USub: "-",
        ast.BitAnd: "&",
        ast.BitOr: "|",
        ast.BitXor: "^",
        ast.Not: "!",
        ast.Mod: "%",
        ast.FloorDiv: "//",
        ast.Pow: "**",
        ast.LShift: "<<",
        ast.RShift: ">>",
    }


def allowed_operations() -> list[str]:
    return list(_operators_().values())


class ExpressionError(ValueError):
    pass


def frac_to_padic(numer: int, denom: int, base: int, min_number_len: int = 32) -> int:
    i = 0
    numbers = {}
    while numer not in numbers:
        for remainder in range(base):
            n = numer - remainder * denom
            if n % base == 0:
                numbers[n] = i
                break
        i += 1
    period_start = numbers[numer]

    series = [0] * len(numbers)
    for num, i in numbers:
        series[i] = num

    res = sum(num * base**i for i, num in enumerate(series))
    if len(numbers) < min_number_len:
        period = cycle(series[period_start:])
        prev = base ** (len(numbers) - 1)
        for i in range(len(numbers), min_number_len):
            res += next(period) * prev * i

    return res


def parse_expression(expression: str, base: int, var_name: str = "x") -> str:
    """Parse 1-Lipschitz function"""
    operators = _operators_()

    def parse(node: ast.AST, variables: set) -> tuple[str, bool]:
        if isinstance(node, ast.Expression):
            return parse(node.body, variables)

        if isinstance(node, ast.Constant):
            return f"{node.value}", False

        if isinstance(node, ast.BinOp):
            if type(node.op) not in operators:
                raise ExpressionError(f"Incorrect operation: {type(node.op)}")
            op = operators[type(node.op)]

            left, has_var_l = parse(node.left, variables)
            if not (has_var_l or left.isnumeric()):
                left = f"{eval(left)}"

            right, has_var_r = parse(node.right, variables)
            if not (has_var_r or right.isnumeric()):
                right = f"{eval(right)}"

            if op == "/":
                if has_var_r or int(right) % base == 0:
                    raise ExpressionError(
                        f"Incorrect division: {base} is divisior of {right}"
                    )
                right = f"{frac_to_padic(1, int(right), base)}"

            elif op in {"<<", ">>"} and (has_var_r or right != "1" or int(right) < 0):
                raise ExpressionError("Incorrect shift")

            return f"({left} {op} {right})", has_var_l or has_var_r

        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in operators:
                raise ExpressionError(f"Incorrect operation: {type(node.op)}")

            operand, has_var = parse(node.operand, variables)
            return f"({operators[type(node.op)]}{operand})", has_var

        if isinstance(node, ast.Name):
            if node.id in variables:
                return node.id, True
            raise ExpressionError(f"Unknown variable: {node.id}")

        raise ExpressionError(f"Unsupported expression: {ast.dump(node)}")

    tree = ast.parse(expression, mode="eval")
    parsed_expr, _ = parse(tree, {var_name})
    return parsed_expr
