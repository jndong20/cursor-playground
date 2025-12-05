import math
import unittest

from calculator import CalculationError, calculate


class CalculateTests(unittest.TestCase):
    def test_add(self) -> None:
        result = calculate("add", [1, 2, 3.5])
        self.assertEqual(result, 6.5)

    def test_sub(self) -> None:
        result = calculate("sub", [10, 1, 2])
        self.assertEqual(result, 7)

    def test_mul(self) -> None:
        result = calculate("mul", [2, 3, 4])
        self.assertEqual(result, 24)

    def test_div(self) -> None:
        result = calculate("div", [20, 2, 2])
        self.assertEqual(result, 5)

    def test_division_by_zero(self) -> None:
        with self.assertRaises(CalculationError):
            calculate("div", [5, 0])

    def test_invalid_operation(self) -> None:
        with self.assertRaises(CalculationError):
            calculate("pow", [2, 3])

    def test_insufficient_operands(self) -> None:
        with self.assertRaises(CalculationError):
            calculate("add", [1])

    def test_float_precision(self) -> None:
        result = calculate("div", [1, 3])
        self.assertTrue(math.isclose(result, 1 / 3))


if __name__ == "__main__":
    unittest.main()

