# report.py
"""
Formal PDF report using ReportLab:
- Assumptions & inputs
- Maintenance breakdown
- Key metrics
- Refi analysis
- Resale impact
- FULL amortization schedule (all months)
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak


def generate_pdf(buffer, inputs, metrics, amortization, resale_info=None, refi_info=None, tax_savings=None):
    """Build a multi-page landscape PDF into `buffer`."""
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("<b>Mortgage Analysis Report</b>", styles["Title"]))
    story.append(Spacer(1, 8))

    # Assumptions
    story.append(Paragraph("<b>Assumptions</b>", styles["Heading2"]))
    assum = [
        ["Home Price", f"${inputs.get('price', 0):,.0f}"],
        ["Down Payment", f"{inputs.get('down_pct', 0)}% (${inputs.get('down_payment', 0):,.0f})"],
        ["Loan Amount", f"${inputs.get('principal', 0):,.0f}"],
        ["Rate", f"{inputs.get('rate', 0)}%"],
        ["Term", f"{inputs.get('years', 0)} years"],
        ["Start Date", inputs.get("start_date_str", "-")],
        ["Taxes", f"${inputs.get('taxes_monthly', 0) * 12:,.0f}/yr"],
        ["Insurance", f"${inputs.get('insurance_monthly', 0) * 12:,.0f}/yr"],
        ["HOA", f"${inputs.get('hoa_monthly', 0) * 12:,.0f}/yr"],
    ]
    t = Table(assum, hAlign="LEFT")
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey)]))
    story.append(t)
    story.append(Spacer(1, 8))

    # Maintenance table
    if "maintenance" in inputs:
        story.append(Paragraph("<b>Maintenance (Annual)</b>", styles["Heading2"]))
        md = [[k.capitalize(), f"${v:,.0f}"] for k, v in inputs["maintenance"].items()]
        mt = Table(md, hAlign="LEFT")
        mt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey)]))
        story.append(mt)
        story.append(Spacer(1, 8))

    # Metrics
    story.append(Paragraph("<b>Key Metrics</b>", styles["Heading2"]))
    md = [
        ["Monthly P&I", f"${metrics.get('monthly_pi', 0):,.2f}"],
        ["First Month Total", f"${metrics.get('first_month_total', 0):,.2f}"],
        ["Total Interest (life)", f"${metrics.get('total_interest', 0):,.0f}"],
    ]
    if tax_savings and len(tax_savings) > 0:
        md.append(["Annual Tax Savings (Year 1)", f"${tax_savings[0]:,.0f}"])
    t2 = Table(md, hAlign="LEFT")
    t2.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey)]))
    story.append(t2)
    story.append(Spacer(1, 8))

    # Refinance analysis
    if refi_info:
        story.append(Paragraph("<b>Refinance Analysis</b>", styles["Heading2"]))
        rd = [
            ["Current Interest", f"${refi_info['current_interest']:,.0f}"],
            ["Refi Interest + Costs", f"${refi_info['refi_interest']:,.0f}"],
            ["Difference", f"${refi_info['difference']:,.0f}"],
            ["Conclusion", refi_info["conclusion"]],
        ]
        rt = Table(rd, hAlign="LEFT")
        rt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey)]))
        story.append(rt)
        story.append(Spacer(1, 8))

    # Resale impact
    if resale_info:
        story.append(Paragraph("<b>Resale Impact</b>", styles["Heading2"]))
        rs = [
            ["Resale Price", f"${resale_info['resale_price']:,.0f}"],
            ["Selling Costs", f"${resale_info['selling_costs']:,.0f}"],
            ["Net Proceeds", f"${resale_info['net_proceeds']:,.0f}"],
            ["Loan Balance at Sale", f"${resale_info['balance']:,.0f}"],
            ["Net Equity Realized", f"${resale_info['equity']:,.0f}"],
        ]
        rtab = Table(rs, hAlign="LEFT")
        rtab.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey)]))
        story.append(rtab)
        story.append(Spacer(1, 8))

    # Full amortization schedule
    story.append(PageBreak())
    story.append(Paragraph("<b>Amortization Schedule (Full)</b>", styles["Heading2"]))
    header = ["Month", "Date", "Payment", "Principal", "Interest", "P&I", "Cumulative Interest", "Balance"]
    rows = [header]
    for row in amortization:
        rows.append(
            [
                row["month"],
                row["date"].strftime("%b %Y"),
                f"${row['payment']:,.2f}",
                f"${row['principal']:,.2f}",
                f"${row['interest']:,.2f}",
                f"${row['pi']:,.2f}",
                f"${row['cumulative_interest']:,.2f}",
                f"${row['balance']:,.2f}",
            ]
        )
    at = Table(rows, repeatRows=1)
    at.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(at)

    doc.build(story)
