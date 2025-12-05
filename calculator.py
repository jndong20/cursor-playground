from __future__ import annotations

import argparse
import sys
from typing import Iterable, List


class CalculationError(ValueError):
    """계산 과정에서 발생하는 오류를 표현하는 예외입니다."""


def calculate(operation: str, operands: Iterable[float]) -> float:
    """주어진 연산자와 피연산자로 사칙연산을 수행합니다.

    Args:
        operation: 수행할 연산 이름 (`add`, `sub`, `mul`, `div` 중 하나)
        operands: 연산에 사용할 숫자들의 반복 가능 객체

    Returns:
        연산 결과를 float 값으로 반환합니다.

    Raises:
        CalculationError: 잘못된 연산자, 피연산자 부족, 0으로 나누기 등 오류가 발생한 경우
    """

    numbers: List[float] = list(operands)
    if operation not in {"add", "sub", "mul", "div"}:
        raise CalculationError(f"지원하지 않는 연산입니다: {operation}")

    if len(numbers) < 2:
        raise CalculationError("최소 두 개 이상의 피연산자가 필요합니다.")

    result = numbers[0]

    if operation == "add":
        for value in numbers[1:]:
            result += value
    elif operation == "sub":
        for value in numbers[1:]:
            result -= value
    elif operation == "mul":
        for value in numbers[1:]:
            result *= value
    elif operation == "div":
        for value in numbers[1:]:
            if value == 0:
                raise CalculationError("0으로 나눌 수 없습니다.")
            result /= value

    return result


def parse_arguments(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="간단한 사칙연산 CLI 계산기",
    )
    parser.add_argument(
        "operation",
        choices=("add", "sub", "mul", "div"),
        help="실행할 연산 (add, sub, mul, div)",
    )
    parser.add_argument(
        "operands",
        nargs="+",
        help="연산에 사용할 숫자 (공백으로 구분)",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    try:
        args = parse_arguments(argv)
        try:
            numbers = [float(value) for value in args.operands]
        except ValueError as exc:
            raise CalculationError("피연산자는 숫자여야 합니다.") from exc

        result = calculate(args.operation, numbers)
    except CalculationError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())

