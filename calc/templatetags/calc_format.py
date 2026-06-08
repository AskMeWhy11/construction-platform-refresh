from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def spaces(value, decimals=0):
    """Число с пробелами-разделителями разрядов.

    {{ x|spaces }}      → 6 859 100 232
    {{ x|spaces:2 }}    → 1 234 567.89
    """
    if value is None or value == "":
        return ""
    try:
        num = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value

    try:
        decimals = int(decimals)
    except (ValueError, TypeError):
        decimals = 0

    quant = Decimal(1).scaleb(-decimals) if decimals else Decimal(1)
    num = num.quantize(quant)

    sign = "-" if num < 0 else ""
    num = abs(num)

    int_part, _, frac_part = f"{num:.{decimals}f}".partition(".")

    # группировка по 3 разряда неразрывным пробелом
    groups = []
    while len(int_part) > 3:
        groups.insert(0, int_part[-3:])
        int_part = int_part[:-3]
    groups.insert(0, int_part)
    int_fmt = "\u202f".join(groups)  # narrow no-break space

    result = f"{sign}{int_fmt}"
    if decimals:
        result += f",{frac_part}"
    return result