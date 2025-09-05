# 🏠 Mortgage Dashboard

An interactive **Mortgage & Rent vs Buy calculator** built with **Flask**, **HTMX**, **TailwindCSS**, and **Chart.js**.  
It provides instant updates, themed charts, amortization tables, and exportable PDF reports.

![screenshot](docs/screenshot-light.png)  
*(Light theme — try Medium & Dark too!)*

---

## ✨ Features

- 🔄 **Live Updates with HTMX** — no "Calculate" button, results auto-refresh as you type  
- 🎨 **Theme Switcher** — Light / Medium / Dark modes with persisted choice  
- 📊 **Interactive Charts**:
  - Payment Breakdown (PI/TI/HOA/PMI)
  - Rent vs Buy (with optional resale scenario)
  - Cumulative Interest
- 📑 **Amortization Table** — pageable view of monthly details (P, I, PMI, balance, etc.)  
- 🏷 **Scenario Inputs**:
  - Home price, interest rate, term, start date
  - Down payment % + $ (synced)
  - PMI toggle / waiver
  - Property tax, insurance, HOA, maintenance
  - Rent growth assumptions
  - Resale date, value, and selling costs
  - Tax deduction toggle
  - Refinance comparison
- 📄 **Export to PDF** — full amortization schedule and charts for sharing or printing  
- 📱 **Responsive Design** — works on desktop, tablet, or phone

---

## 🚀 Getting Started

### 1. Clone and install

```bash
git clone https://github.com/yourname/mortgage-dashboard.git
cd mortgage-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

flask --app app run --debug
Visit http://127.0.0.1:5000 in your browser.


mortgage-dashboard/
├── app.py              # Flask entrypoint
├── calculator.py       # Finance math helpers (payments, amortization, PMI)
├── report.py           # PDF export via reportlab
├── templates/
│   ├── base.html       # Layout + header + theme switcher
│   ├── index.html      # Main dashboard page with form
│   └── _results.html   # HTMX partial swap for results
├── static/
│   └── charts.js       # Chart.js setup + theme-aware rendering
├── requirements.txt
└── README.md


🧩 Tech Stack

Flask
 — backend
HTMX
 — dynamic front-end updates without a SPA
TailwindCSS
 — styling
Chart.js
 — charts
ReportLab
 — PDF generation


Demo
Here is a working live demo:

![](MortgageDashboard.png)
---

