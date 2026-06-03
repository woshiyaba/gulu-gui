from decimal import ROUND_HALF_UP, Decimal


def round_half_up(value: float | int | str, digits: int = 0) -> float:
    """
    四舍五入到指定小数位。

    区别于 Python 内置 round 的银行家舍入（round half to even），
    本函数始终使用 ROUND_HALF_UP（逢五进一），与游戏内展示口径一致。

    - digits=0 返回整数值的 float（取整请在外层 int() 转换）
    - digits>0 保留对应小数位
    """
    quant = Decimal(1) if digits <= 0 else Decimal(1).scaleb(-digits)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))
