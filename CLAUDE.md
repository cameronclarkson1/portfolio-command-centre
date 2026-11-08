# Portfolio Command Centre — Claude Code Operating Rules

## Repository layout

```
api/          FastAPI backend (deployed to Railway via Docker)
repo/         Production services — the deployed Python code
  services/   Valuation engine, DCF model, relative valuation, etc.
  providers/  FMP, Finnhub, SEC Edgar, yfinance data adapters
  data/       Damodaran betas, static reference tables
frontend/     Streamlit app (NOT in the Docker image — local dev only)
nextjs-frontend/  Next.js UI (deployed to Vercel)
backtest/     Backtesting scripts (local only)
```

**Production deployment path:**
`Dockerfile` copies `api/` + `repo/` only.
`api/main.py` adds `repo/` to `sys.path`.
All API routes resolve to `repo/services/`.
`frontend/services/` is **not deployed**.

## Autonomous development permissions

Claude Code is authorised to independently (no approval needed):

- Fix bugs and regressions
- Improve existing features
- Refine UI/UX and styling
- Improve performance and efficiency
- Refactor code
- Write and run tests
- Resolve technical debt
- Stage files (`git add`)
- Commit completed bug fixes and minor improvements
- Create and manage development branches

**Always requires approval before:**

- Introducing entirely new features
- Making major architectural changes
- Changing financial models or investment methodologies (DCF growth
  assumptions, WACC methodology, discount rates, model weights,
  rating thresholds, scoring rules)
- Changing core application functionality
- Removing existing functionality
- Deploying to production (git push to origin/master)
- Introducing significant ongoing costs

## Git workflow

Use Bash (not PowerShell) for all git operations — Bash is configured
in `.claude/settings.json` with the appropriate allow rules.

Commit on the `master` branch for routine fixes.
Create a feature branch for anything that touches more than two
unrelated areas of the codebase.

Do not push to origin without explicit user approval.

## Testing

```bash
# Production services (repo/)
python -m pytest repo/services/tests/ -v

# Frontend Streamlit services (frontend/)
python -m pytest frontend/services/tests/ -v

# Investment bot tests
python -m pytest investment_bot/tests/ -v
```

All three suites must pass before committing any change that touches
`repo/services/` or `frontend/services/`.

## Financial model constraints

Do not change without explicit approval:
- DCF growth-rate assumptions or staging logic
- WACC / discount-rate methodology
- Cross-validation thresholds (3× / 0.33× ratio)
- BUCKET_WEIGHTS or model weights per sector
- Valuation rating thresholds (±5%, ±20%)
- Data providers or fundamental-data field mappings

## Permission configuration

`.claude/settings.json` — committed project-wide rules.
`.claude/settings.local.json` — machine-local rules (not committed).

The `allow` rules in `settings.json` let Claude perform routine dev
operations without an interactive prompt. The `deny` rules block
destructive git operations (force-push, hard-reset, clean -f).

To extend or restrict permissions, edit `.claude/settings.json` and
commit the change with a note explaining the reason.
