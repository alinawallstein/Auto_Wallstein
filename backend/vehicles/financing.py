from decimal import Decimal, ROUND_HALF_UP, localcontext


def calculate_financing(price, downpayment, term_months, annual_rate):
    price = Decimal(price).quantize(Decimal('0.01'))
    downpayment = Decimal(downpayment).quantize(Decimal('0.01'))
    annual_rate = Decimal(annual_rate).quantize(Decimal('0.01'))
    term_months = int(term_months)
    financed = price - downpayment
    if financed < 0 or term_months < 1:
        raise ValueError('Ungültige Finanzierungswerte.')
    with localcontext() as ctx:
        ctx.prec = 28
        monthly_rate = (Decimal(1) + annual_rate / Decimal(100)) ** (Decimal(1) / Decimal(12)) - Decimal(1)
        if monthly_rate == 0:
            payment = financed / Decimal(term_months)
        else:
            factor = (Decimal(1) + monthly_rate) ** term_months
            payment = financed * monthly_rate * factor / (factor - Decimal(1))
    return {'price': price, 'downpayment': downpayment, 'term_months': term_months, 'annual_rate': annual_rate, 'financed': financed.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), 'monthly_rate': payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), 'final_payment': None}
