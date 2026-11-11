# Frontend

Next.js UI for the inquiry demo.

```powershell
npm install
$env:NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000"
npm run dev
```

Pages: Dashboard, New Inquiry, Inquiry Details, Evaluations.

Email send always goes through the backend approval gates — the UI cannot bypass them.
