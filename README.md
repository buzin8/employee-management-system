# Employee Management System

A Flask-based employee dashboard with SQLite for local development and PostgreSQL for persistent deployment.

## Run locally

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

The app uses a local `employees.db` file by default. To use PostgreSQL locally, copy `.env.example` to `.env` and set `DATABASE_URL` to your PostgreSQL connection string. The app creates its employee table automatically and seeds the sample employees only when the table is empty.

## Deploy to Vercel

Vercel detects the Flask `app` in `app.py` and uses `requirements.txt` for dependencies. Set `DATABASE_URL` to your PostgreSQL connection string and `FLASK_SECRET_KEY` to a randomly generated value in the Vercel project environment variables, then deploy. The app refuses to start on Vercel if `DATABASE_URL` is missing, rather than silently using temporary storage.

Do not commit `.env` or expose `DATABASE_URL`. This app does not yet include authentication; add access control before storing sensitive employee information.
