# Enterprise AI Claims — Week 1

AI states and summarizes expense facts. The manager chooses **Accept, Reject or Investigate** for each claim. The chatbot answers clarifying questions with source references.

There are no AI recommendations, AI investigations or automatic decisions. Investigate leaves the manager review open until a final Accept or Reject action.

See [Week 1 setup and code guide](docs/Week1.md). Week 1 uses its own `claims_week1` database and `claims-week1` queue. Weeks 2–4 remain on separate branches. After setup, run `bash scripts/demo.sh`, open http://127.0.0.1:5173, click Run for fact summaries, and use Manager review for decisions.

For teaching, read the [complete codebase guide](docs/TEACHING_GUIDE.md) and [Week 1–4 behavior comparison](docs/WEEK_BY_WEEK.md).
