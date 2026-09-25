from solution import power


def test_zero_exponent():
    assert power(7, 0) == 1


def test_positive_exponents():
    assert power(2, 10) == 1024
    assert power(5, 3) == 125
    assert power(-2, 3) == -8
