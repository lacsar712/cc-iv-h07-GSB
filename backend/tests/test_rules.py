from rules import FF_MIN, judge


def test_threshold_fill_factor_is_qualified():
    verdict, reason = judge(FF_MIN)

    assert verdict == "合格"
    assert "不低于" in reason


def test_lower_fill_factor_remains_attenuated():
    verdict, reason = judge(FF_MIN - 0.000001)

    assert verdict == "衰减"
    assert "低于" in reason


def test_seed_attenuated_sample_is_not_released():
    verdict, _ = judge(0.61)

    assert verdict == "衰减"
