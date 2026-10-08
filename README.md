# Enterprise AI Claims — Week 2

AI recommends **Accept or Reject** for every expense. The manager makes every final decision. No AI investigation or automatic decision is executed.

Start with [Week 2 setup, workflow and code guide](docs/Week2.md). The app provides a claim queue, AI recommendations with policy/evidence references, manager Accept/Reject controls, a read-only chatbot and audited outcomes.

Week 2 uses its own database `claims_week2` and worker queue `claims-week2`. The completed Week 3 and autonomous Week 4 applications remain on their separate branches. Older docs are historical records; [Week2.md](docs/Week2.md) describes this branch.

After dependency and database setup, run `bash scripts/demo.sh` or follow the three manual terminal commands in the guide. Open http://127.0.0.1:5173, click Run for recommendations, then decide each expense in Manager review.
