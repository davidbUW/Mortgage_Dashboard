# calculator.py
"""
Core financial calculations for the Mortgage Dashboard:
- Monthly P&I payment
- Full amortization schedule (with calendar dates)
- Rent vs Buy comparison (cumulative)
- Monthly tax savings (interest + property tax)
- Refinance comparison
- Resale impact / equity at sale
"""

from datetime import date


def add_months(d: date, n: int) -> date:
    """Add n months to date d without external libraries, clamping to end-of-month."""
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    days_in_month = [
        31,
        29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ][m - 1]
    day = min(d.day, days_in_month)
    return date(y, m, day)


def calculate_monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """Standard fixed-rate mortgage payment (P&I only)."""
    r = (annual_rate / 100.0) / 12.0
    n = years * 12
    if r == 0:
        return principal / n
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def calculate_amortization(principal: float, annual_rate: float, years: int, start_date: date):
    """
    Produce full amortization schedule.

    Each row dict contains:
      month, date, interest, principal, payment, pi, cumulative_interest, balance
    """
    payment = round(calculate_monthly_payment(principal, annual_rate, years), 2)
    r = (annual_rate / 100.0) / 12.0
    n = years * 12
    balance = principal
    cumulative_interest = 0.0
    schedule = []

    for i in range(1, n + 1):
        interest = round(balance * r, 2)
        principal_paid = round(payment - interest, 2)

        # Adjust last payment to avoid negative balance from rounding
        if principal_paid > balance:
            principal_paid = round(balance, 2)
            payment_eff = round(interest + principal_paid, 2)
        else:
            payment_eff = payment

        balance = round(balance - principal_paid, 2)
        cumulative_interest = round(cumulative_interest + interest, 2)
        pay_date = add_months(start_date, i - 1)

        schedule.append(
            {
                "month": i,
                "date": pay_date,
                "interest": interest,
                "principal": principal_paid,
                "payment": payment_eff,
                "pi": payment_eff,  # alias for P&I for clarity in templates
                "cumulative_interest": cumulative_interest,
                "balance": max(balance, 0.0),
            }
        )
        if balance <= 0.0:
            break
    return schedule


def tax_savings_monthly(amortization: list, tax_rate_pct: float, property_tax_monthly: float, enabled: bool) -> list:
    """
    Approximate monthly tax savings = (interest_this_month + property_tax_monthly) * tax_rate.

    Returns a list aligned to amortization length. If disabled or tax_rate <= 0, returns zeros.
    """
    if not enabled or tax_rate_pct <= 0:
        return [0.0 for _ in amortization]
    t = tax_rate_pct / 100.0
    return [round((row["interest"] + property_tax_monthly) * t, 2) for row in amortization]


def calculate_rent_vs_buy(
    inputs: dict,
    amortization: list,
    tax_sav_monthly: list | None = None,
    pmi_monthly: list | None = None,
):
    """
    Compare renting vs buying up to the length of `amortization`.

    inputs:
      rent: starting rent per month
      rent_growth: annual % growth (e.g., 3 for 3%)
      maint_monthly, taxes_monthly, insurance_monthly, hoa_monthly

    tax_sav_monthly: optional list (len == amortization) of monthly tax savings to subtract
    pmi_monthly: optional list (len == amortization) of PMI to add while active
    """
    rent = float(inputs.get("rent", 0.0))
    rent_growth = float(inputs.get("rent_growth", 0.0)) / 100.0
    maint = float(inputs.get("maint_monthly", 0.0))
    taxes = float(inputs.get("taxes_monthly", 0.0))
    insurance = float(inputs.get("insurance_monthly", 0.0))
    hoa = float(inputs.get("hoa_monthly", 0.0))

    rent_costs, buy_costs = [], []
    cum_rent, cum_buy = 0.0, 0.0

    for i, row in enumerate(amortization, start=1):
        # Rent grows annually
        if i > 1 and (i - 1) % 12 == 0:
            rent *= (1.0 + rent_growth)

        # Cumulative rent
        cum_rent += rent
        rent_costs.append(round(cum_rent, 2))

        # Ownership outflow this month
        monthly_cost = row["payment"] + taxes + insurance + hoa + maint

        # Add PMI if provided
        if pmi_monthly:
            monthly_cost += float(pmi_monthly[i - 1])

        # Subtract tax savings if provided
        if tax_sav_monthly:
            monthly_cost -= float(tax_sav_monthly[i - 1])

        cum_buy += monthly_cost
        buy_costs.append(round(cum_buy, 2))

    return {"rent": rent_costs, "buy": buy_costs}



def calculate_refi(current_full_sched: list, refi_rate: float, refi_years: int, refi_start_date: date, closing_costs: float):
    """
    Compare continuing the CURRENT loan vs REFINANCING, starting from `refi_start_date`.

    Method:
      1) Find the first row in the current amortization whose 'date' >= refi_start_date.
      2) Let 'remaining_balance' be the balance at that index-1 (i.e., right BEFORE that payment is made),
         or at the index if you prefer to assume refi exactly on the payment cycle.
      3) Current path interest from refi date to payoff = (final cumulative interest) - (cumulative interest up to idx-1).
      4) Refi path interest = total interest of a NEW loan: principal=remaining_balance, rate=refi_rate,
         term=refi_years, start=refi_start_date, plus closing_costs.
    Returns:
      dict: { current_interest, refi_interest, difference, conclusion, remaining_balance, refi_start_index }
    """
    if not current_full_sched:
        return {"current_interest": 0.0, "refi_interest": 0.0, "difference": 0.0, "conclusion": "—"}

    # 1) find index for refi start
    idx = len(current_full_sched) - 1
    for i, row in enumerate(current_full_sched):
        if row["date"] >= refi_start_date:
            idx = i
            break

    # Interest already paid up to the month BEFORE idx
    prev_cum_int = current_full_sched[idx - 1]["cumulative_interest"] if idx > 0 else 0.0
    final_cum_int = current_full_sched[-1]["cumulative_interest"]
    current_remaining_interest = round(final_cum_int - prev_cum_int, 2)

    # Remaining balance right before refi start month
    remaining_balance = current_full_sched[idx - 1]["balance"] if idx > 0 else current_full_sched[0]["balance"]

    # 4) Build refi schedule from that balance
    refi_sched = calculate_amortization(
        principal=remaining_balance,
        annual_rate=refi_rate,
        years=refi_years,
        start_date=refi_start_date
    )
    refi_interest_total = refi_sched[-1]["cumulative_interest"] + float(closing_costs)

    diff = round(current_remaining_interest - refi_interest_total, 2)
    conclusion = "✅ Refi saves money" if diff > 0 else "❌ Refi costs more"
    return {
        "current_interest": round(current_remaining_interest, 2),
        "refi_interest": round(refi_interest_total, 2),
        "difference": diff,
        "conclusion": conclusion,
        "remaining_balance": round(remaining_balance, 2),
        "refi_start_index": idx + 1,  # 1-based for display
    }



def apply_resale_impact(amortization: list, resale_price: float, resale_date: date, selling_cost_pct: float):
    """
    Determine balance at (or just before) the resale_date and compute net equity:
      equity = net_proceeds(resale_price - selling_costs) - remaining_balance

    Returns dict with sale_index, equity and components.
    """
    sale_idx = len(amortization) - 1
    for i, row in enumerate(amortization):
        if row["date"] >= resale_date:
            sale_idx = i
            break
    balance = amortization[sale_idx]["balance"]
    selling_costs = round(resale_price * (selling_cost_pct / 100.0), 2)
    net_proceeds = round(resale_price - selling_costs, 2)
    equity = round(net_proceeds - balance, 2)
    return {
        "sale_index": sale_idx,
        "resale_price": round(resale_price, 2),
        "selling_costs": selling_costs,
        "net_proceeds": net_proceeds,
        "balance": round(balance, 2),
        "equity": equity,
    }

def pmi_schedule(amortization: list, home_price: float, pmi_rate_annual_pct: float,
                 enabled: bool, exempt: bool = False, stop_at_ltv80: bool = True) -> list:
    """
    Simple PMI model:
      - If not enabled or exempt or rate <= 0, all zeros
      - Otherwise charge monthly PMI = (pmi_rate_annual_pct% * original_loan_amount)/12
      - Stop when current LTV <= 80% (balance <= 80% of home_price), if stop_at_ltv80
    """
    if not enabled or exempt or pmi_rate_annual_pct <= 0 or not amortization:
        return [0.0 for _ in amortization]

    original_balance = amortization[0]["balance"] + amortization[0]["principal"]  # ≈ original principal
    monthly_pmi = (pmi_rate_annual_pct / 100.0) * original_balance / 12.0
    out = []
    for row in amortization:
        bal = row["balance"]
        if stop_at_ltv80 and bal <= 0.8 * home_price:
            out.append(0.0)
        else:
            out.append(round(monthly_pmi, 2))
    return out
