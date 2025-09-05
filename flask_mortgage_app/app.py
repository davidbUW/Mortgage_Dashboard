# app.py
"""
Flask entrypoint for the Mortgage Dashboard.

Features:
- Auto-updating dashboard via HTMX (no "Calculate" button)
- Down payment slider + dollar input (synced)
- Amortization scope selector (12 / 60 / Full 360)
- Rent vs Buy comparison (with optional tax-deduction effect)
- Refinance comparison card (with conclusion)
- Resale impact and equity-at-sale applied to Buy curve
- Formal PDF report export (/pdf) with the FULL amortization schedule
"""

from flask import Flask, render_template, request, send_file
from datetime import date, datetime
import io
import math


from calculator import (
    calculate_amortization,
    calculate_monthly_payment,
    calculate_rent_vs_buy,
    calculate_refi,
    apply_resale_impact,
    tax_savings_monthly
)

from report import generate_pdf

app = Flask(__name__)


def today_date() -> date:
    """Return today's system date as a `date` (no time component)."""
    now = datetime.today()
    return date(now.year, now.month, now.day)


@app.route("/", methods=["GET"])
def index():
    """Render the main dashboard with sensible defaults."""
    d0 = today_date()
    defaults = {
        "pmi_rate": 0.6,          # annual % of original loan (typical conventional PMI range ~0.3–1.5)
        "pmi_exempt": False,      # special waiver/exemption
        "resale_enable": True,    # gate resale features with a checkbox
        "price": 300000,
        "down_pct": 20,
        "rate": 6.5,
        "years": 30,
        "pmi": 0,  # (placeholder if you later want PMI logic)
        "taxes_monthly": 300,
        "insurance_monthly": 100,
        "hoa_monthly": 50,
        "maintenance": {
            "roof": 500,
            "hvac": 400,
            "plumbing": 200,
            "appliances": 300,
            "lawn": 200,
            "upgrades": 500,
            "other": 100,
        },
        "rent": 1200,
        "rent_growth": 3,
        "start_date": d0,
        "resale_value": 400000,
        "resale_date": date(d0.year + 10, d0.month, d0.day),
        "selling_cost_pct": 6,
        "tax_deduction": False,
        "tax_rate": 24,
        "amort_scope": 12,  # initial table size
        "refi_enable": True,
        "refi_rate": 6.0,
        "refi_years": 30,
        "refi_closing": 3000,
    }
    return render_template("index.html", defaults=defaults)


def parse_bool(val) -> bool:
    """Parse common truthy strings from HTML form inputs."""
    return str(val).lower() in ("1", "true", "on", "yes", "y")


@app.route("/results", methods=["POST"])
def results():
    """Compute results and return the partial `_results.html` for HTMX swap."""
    # --- Core inputs
    price = float(request.form.get("price", 0))
    down_pct = float(request.form.get("down_pct", 0))
    down_payment = (down_pct / 100.0) * price
    principal = max(price - down_payment, 0.0)
    rate = float(request.form.get("rate", 0))
    years = int(request.form.get("years", 30))
    start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()

    # --- PMI Inputs ---
    pmi_rate = float(request.form.get("pmi_rate", 0) or 0)  # annual % of loan
    pmi_exempt = str(request.form.get("pmi_exempt", "")).lower() in ("1","true","on","yes","y")

    # PMI & resale toggles
    pmi_rate = float(request.form.get("pmi_rate", 0) or 0)
    pmi_exempt = str(request.form.get("pmi_exempt", "")).lower() in ("1","true","on","yes","y")
    resale_enable = str(request.form.get("resale_enable", "")).lower() in ("1","true","on","yes","y")

    # --- Maintenance (annual buckets → monthly in calculations)
    maintenance = {
        "roof": float(request.form.get("maint_roof", 0) or 0),
        "hvac": float(request.form.get("maint_hvac", 0) or 0),
        "plumbing": float(request.form.get("maint_plumbing", 0) or 0),
        "appliances": float(request.form.get("maint_appliances", 0) or 0),
        "lawn": float(request.form.get("maint_lawn", 0) or 0),
        "upgrades": float(request.form.get("maint_upgrades", 0) or 0),
        "other": float(request.form.get("maint_other", 0) or 0),
    }
    maint_monthly = sum(maintenance.values()) / 12.0

    # --- Other monthly costs
    taxes_monthly = float(request.form.get("taxes_monthly", 0) or 0)
    insurance_monthly = float(request.form.get("insurance_monthly", 0) or 0)
    hoa_monthly = float(request.form.get("hoa_monthly", 0) or 0)

    # --- Rent assumptions
    rent = float(request.form.get("rent", 0) or 0)
    rent_growth = float(request.form.get("rent_growth", 0) or 0)

    # --- Resale assumptions
    resale_value = float(request.form.get("resale_value", 0) or 0)
    resale_date = datetime.strptime(request.form.get("resale_date"), "%Y-%m-%d").date()
    selling_cost_pct = float(request.form.get("selling_cost_pct", 6) or 6)

    # --- Taxes (optional)
    tax_deduction = parse_bool(request.form.get("tax_deduction"))
    tax_rate = float(request.form.get("tax_rate", 0) or 0)

    # --- Display scope for amortization table
    scope = int(request.form.get("amort_scope", 12))

    # --- Refi inputs (optional)
    refi_enable = parse_bool(request.form.get("refi_enable"))
    refi_rate = float(request.form.get("refi_rate", 0) or 0)
    refi_years = int(request.form.get("refi_years", years) or years)
    refi_closing = float(request.form.get("refi_closing", 0) or 0)
    refi_start_date_str = request.form.get("refi_start_date")
    refi_start_date = datetime.strptime(refi_start_date_str, "%Y-%m-%d").date() if refi_start_date_str else start_date

    # --- derived helpers ---
    maint_monthly = sum(maintenance.values()) / 12.0

    # --- Calculations
    amort = calculate_amortization(principal, rate, years, start_date)
    monthly_pi = calculate_monthly_payment(principal, rate, years)
    tax_sav = tax_savings_monthly(amort, tax_rate, taxes_monthly, tax_deduction)

    # PMI schedule aligned to amortization
    from calculator import pmi_schedule  # top-level import also fine if you prefer
    pmi_list = pmi_schedule(
        amortization=amort,
        home_price=price,
        pmi_rate_annual_pct=pmi_rate,
        enabled=(down_pct < 20.0),   # auto-enable if DP < 20
        exempt=pmi_exempt,
        stop_at_ltv80=True
    )

    # --- Rent vs Buy (full term, no equity subtraction) ---
    # --- ALWAYS build the FULL rent vs buy series first ---
    rent_buy_full = calculate_rent_vs_buy(
        {
            "rent": rent,
            "rent_growth": rent_growth,
            "maint_monthly": maint_monthly,
            "taxes_monthly": taxes_monthly,
            "insurance_monthly": insurance_monthly,
            "hoa_monthly": hoa_monthly,
        },
        amort,
        tax_sav_monthly=tax_sav if tax_deduction else None,
        pmi_monthly=pmi_list,
    )

    # Default: when resale disabled, use the full series as the working series
    rent_buy = rent_buy_full
    resale = None
    sale_idx = len(amort) - 1

    # --- Optional resale path (truncate + equity adjustment) ---
    if resale_enable:
        resale = apply_resale_impact(amort, resale_value, resale_date, selling_cost_pct)
        sale_idx = resale["sale_index"]

        rent_buy_trunc = calculate_rent_vs_buy(
            {
                "rent": rent,
                "rent_growth": rent_growth,
                "maint_monthly": maint_monthly,
                "taxes_monthly": taxes_monthly,
                "insurance_monthly": insurance_monthly,
                "hoa_monthly": hoa_monthly,
            },
            amort[: sale_idx + 1],
            tax_sav_monthly=(tax_sav[: sale_idx + 1] if tax_deduction else None),
            pmi_monthly=pmi_list[: sale_idx + 1],
        )

        # subtract equity at sale from the last buy point (TCO view)
        if rent_buy_trunc.get("buy"):
            equity = float(resale.get("equity", 0.0)) if resale else 0.0
            last = rent_buy_trunc["buy"][-1]
            rent_buy_trunc["buy"][-1] = round(max(last - equity, 0.0), 2)

        rent_buy = rent_buy_trunc

    # --- metrics (include PMI in first month total) ---
    first_month_total = (
        amort[0]["payment"]
        + taxes_monthly + insurance_monthly + hoa_monthly
        + maint_monthly
        + (pmi_list[0] if pmi_list else 0.0)
        - (tax_sav[0] if (tax_deduction and tax_sav) else 0.0)
    )
    metrics = {
        "monthly_pi": round(monthly_pi, 2),
        "first_month_total": round(first_month_total, 2),
        "total_interest": amort[-1]["cumulative_interest"],
    }

    # Amortization table size
    # --- Paging: page_size = rows per page (was "amort_scope"); page = current page
    page_size_raw = request.form.get("amort_scope", "12")
    page_size = 360 if str(page_size_raw).lower() in ("360", "full") else int(page_size_raw)
    page = int(request.form.get("page", 1))
    total_rows = len(amort)
    total_pages = max(1, math.ceil(total_rows / page_size))

    # Keep page in bounds
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    end = min(start + page_size, total_rows)
    amort_subset = amort[start:end]


    # Refi compare
    refi_info = None
    if refi_enable:
        refi_info = calculate_refi(
            current_full_sched=amort,
            refi_rate=refi_rate,
            refi_years=refi_years,
            refi_start_date=refi_start_date,
            closing_costs=refi_closing
        )


    return render_template(
        "_results.html",
        price=price,
        down_pct=down_pct,
        down_payment=down_payment,
        principal=principal,
        rate=rate,
        years=years,
        start_date=start_date,
        taxes_monthly=taxes_monthly,
        insurance_monthly=insurance_monthly,
        hoa_monthly=hoa_monthly,
        maintenance=maintenance,
        metrics=metrics,
        amortization=amort_subset,
        amort_full=amort,
        rent_buy=rent_buy,                 # up-to-resale, equity-subtracted
        rent_buy_full=rent_buy_full,       # FULL 360 months
        resale_info=resale,
        tax_savings=tax_sav,
        tax_deduction=tax_deduction,
        tax_rate=tax_rate,
        refi_info=refi_info,
        amort_scope=scope,
        page=page,
        total_pages=total_pages,
        page_size=page_size,
        total_rows=total_rows,
        refi_start_date=refi_start_date,
        pmi_rate=pmi_rate,
        pmi_exempt=pmi_exempt,
        pmi_first_month=pmi_list[0] if pmi_list else 0.0,
        resale_enable=resale_enable,
        pmi_list=pmi_list,
    )
    

@app.route("/pdf", methods=["POST"])
def pdf():
    """Generate and return a formal PDF report (inline view)."""
    # Parse (same as /results, condensed where possible)
    price = float(request.form.get("price", 0))
    down_pct = float(request.form.get("down_pct", 0))
    down_payment = (down_pct / 100.0) * price
    principal = max(price - down_payment, 0.0)
    rate = float(request.form.get("rate", 0))
    years = int(request.form.get("years", 30))
    start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
    refi_start_date_str = request.form.get("refi_start_date")
    refi_start_date = datetime.strptime(refi_start_date_str, "%Y-%m-%d").date() if refi_start_date_str else start_date


    taxes_monthly = float(request.form.get("taxes_monthly", 0) or 0)
    insurance_monthly = float(request.form.get("insurance_monthly", 0) or 0)
    hoa_monthly = float(request.form.get("hoa_monthly", 0) or 0)

    maintenance = {
        "roof": float(request.form.get("maint_roof", 0) or 0),
        "hvac": float(request.form.get("maint_hvac", 0) or 0),
        "plumbing": float(request.form.get("maint_plumbing", 0) or 0),
        "appliances": float(request.form.get("maint_appliances", 0) or 0),
        "lawn": float(request.form.get("maint_lawn", 0) or 0),
        "upgrades": float(request.form.get("maint_upgrades", 0) or 0),
        "other": float(request.form.get("maint_other", 0) or 0),
    }
    maint_monthly = sum(maintenance.values()) / 12.0

    rent = float(request.form.get("rent", 0) or 0)
    rent_growth = float(request.form.get("rent_growth", 0) or 0)

    resale_value = float(request.form.get("resale_value", 0) or 0)
    resale_date = datetime.strptime(request.form.get("resale_date"), "%Y-%m-%d").date()
    selling_cost_pct = float(request.form.get("selling_cost_pct", 6) or 6)

    tax_deduction = parse_bool(request.form.get("tax_deduction"))
    tax_rate = float(request.form.get("tax_rate", 0) or 0)

    refi_enable = parse_bool(request.form.get("refi_enable"))
    refi_rate = float(request.form.get("refi_rate", 0) or 0)
    refi_years = int(request.form.get("refi_years", years) or years)
    refi_closing = float(request.form.get("refi_closing", 0) or 0)

    # Compute
    amort = calculate_amortization(principal, rate, years, start_date)
    monthly_pi = calculate_monthly_payment(principal, rate, years)
    tax_sav = tax_savings_monthly(amort, tax_rate, taxes_monthly, tax_deduction)
    resale = apply_resale_impact(amort, resale_value, resale_date, selling_cost_pct)


    metrics = {
        "monthly_pi": round(monthly_pi, 2),
        "first_month_total": round(
            amort[0]["payment"]
            + taxes_monthly
            + insurance_monthly
            + hoa_monthly
            + maint_monthly
            - (tax_sav[0] if tax_sav else 0),
            2,
        ),
        "total_interest": amort[-1]["cumulative_interest"],
    }

    refi_info = None
    if refi_enable:
        refi_info = calculate_refi(
            current_full_sched=amort,
            refi_rate=refi_rate,
            refi_years=refi_years,
            refi_start_date=refi_start_date,
            closing_costs=refi_closing
        )


    inputs = {
        "price": price,
        "down_pct": down_pct,
        "down_payment": down_payment,
        "principal": principal,
        "rate": rate,
        "years": years,
        "start_date_str": start_date.strftime("%b %Y"),
        "taxes_monthly": taxes_monthly,
        "insurance_monthly": insurance_monthly,
        "hoa_monthly": hoa_monthly,
        "maintenance": maintenance,
        "refi_start_date": refi_start_date,

    }

    # Build PDF to memory and stream inline
    buf = io.BytesIO()
    generate_pdf(
        buf,
        inputs,
        metrics,
        amort,
        resale_info=resale,
        refi_info=refi_info,
        tax_savings=None if not tax_deduction else [sum(tax_sav[:12])],
    )
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=False, download_name="mortgage_report.pdf")


if __name__ == "__main__":
    # Run locally
    app.run(host="127.0.0.1", port=5000, debug=True)
