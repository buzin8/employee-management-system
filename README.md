# Employee Management System

A Flask-based employee dashboard with a SQLite-backed local demo.

## Run locally

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Deploy to Vercel

Vercel detects the Flask `app` in `app.py` and uses `requirements.txt` for dependencies. Import this repository into Vercel, set `FLASK_SECRET_KEY` to a randomly generated value in the project environment variables, and deploy.

This deployment is configured as a demo. It stores SQLite data under `/tmp`, which is temporary and can reset between function instances or deployments. Do not enter real employee information. Use a persistent database and authentication before using this app for real employee records.
