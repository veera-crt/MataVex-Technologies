# MataVex Technologies - Core Infrastructure

This repository contains the full-stack code for the MataVex Technologies platform, built for performance, security, and industrial project delivery.

## 📁 Project Structure

```text
├── app.py              # Main Flask server (Entry Point)
├── .env                # Centralized configuration (Secrets & URLs)
├── backend/            # Core backend logic (Python Package)
│   ├── __init__.py     # Package orchestration
│   ├── database_node.py # PostgreSQL connectivity
│   ├── auth_node.py     # Identity & Security
│   └── invoice_utility.py # PDF generation & SMTP Sync
├── frontend/           # Storefront assets
│   ├── index.html      # Main portal
│   ├── assets/         # Branding & Visuals
│   ├── css/            # Unified design system
│   └── js/             # Interactive logic (main.js)
└── invoices/           # Archival storage for generated invoices
```

## 🚀 Getting Started

### 1. Environment Setup
Ensure you have a Python Virtual Environment initialized and dependencies installed:
```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install flask flask-cors psycopg2-binary razorpay reportlab google-auth python-dotenv
```

### 2. Configuration
Your `.env` file in the root must contain:
- `DATABASE_URL`: Neon PostgreSQL connection string.
- `GOOGLE_CLIENT_ID`: For secure user authentication.
- `RAZORPAY_KEY_*`: For transaction processing.
- `EMAIL_USER` & `EMAIL_PASS`: For automated invoice delivery.

### 3. Running the Site
To launch the production-ready node:
```bash
python3 app.py
```

## 🛠️ Maintenance Utilities
- **Links Management**: Run `backend/links.py` to synchronize download URLs for projects.
- **Library Sync**: Ensure the `library` and `payments` tables are active for user acquisitions.

---
© 2026 MataVex Technologies. Secure Project Infrastructure.
