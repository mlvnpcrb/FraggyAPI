# Vercel automatic deployment investigation — findings only

Reviewed 2026-10-19 (Asia/Manila). Read-only GitHub API and repository inspection;
no Vercel API access, settings edits, cancellation, push or deployment in this work.

## Evidence

- Approved Phase 2L head: `99737e199d4b4e8b1f8243d06e2febb9640a88cf`.
- [Commit statuses](https://api.github.com/repos/mlvnpcrb/FraggyAPI/commits/99737e199d4b4e8b1f8243d06e2febb9640a88cf/status)
  show a separate **Vercel** success status: “Deployment has completed,” linked to
  [the deployment inspector](https://vercel.com/mlvnpcrbs-projects/fraggyapi-demo/5jPiGFrqivxL382G7GuJTAHBFYTZ).
  It was posted at **16:35:00 Manila time** on 2026-10-19.
- The Vercel GitHub App posted a separate `Vercel Preview Comments` check and a
  [bot comment on PR #12](https://github.com/mlvnpcrb/FraggyAPI/pull/12) naming
  `fraggyapi-demo`, displaying **Ready** and a **Preview** link. Its metadata
  identifies a GitHub integration and root directory `apps/web`.
- The repository workflow's `vercel-demo` job installs dependencies, builds Next.js
  and runs `node scripts/check_vercel_demo.mjs` locally. It contains no Vercel CLI,
  deployment API call, promotion or deployment token usage. The main `checks` job
  also has no deployment command.
- [Phase 2L PR CI](https://github.com/mlvnpcrb/FraggyAPI/actions/runs/39223734785)
  finished after the Vercel status. The automatic Vercel build did not wait for
  the full foundation checks to pass.
- The changed files were backend/scripts/docs/workflow/package scripts; no
  `apps/web` source was changed. The integration nevertheless built the project.
  Existing `apps/web/vercel.json` configures commands/framework, not Git branch
  deployment controls. Earlier [preview instructions](vercel-demo.md) explicitly
  recommended leaving automatic Git deployments disconnected for a controlled
  preview; observed GitHub App behavior differs from that intended operational
  setup.

## Finding and limits

The evidence supports **the installed Vercel GitHub integration automatically
building this commit/PR**, independently of the GitHub Actions build-only job.
Most likely, automatic branch/PR preview builds are allowed on the connected
project and no effective ignore rule excluded this backend-only change.

The actual Git event (push vs PR webhook), branch rules, Ignored Build Step,
monorepo affected-project settings, Production branch and authentication settings
cannot be inspected through current tools. These are hypotheses about settings,
not verified values. The GitHub bot's Preview label is not an independent Vercel
API confirmation of `target`. The actual `dpl_…` ID, current API state and target
remain unavailable; do not substitute the inspector path token for a deployment ID.

The user reported Vercel team access denied (403); no callable Vercel connector is
available here. No cancellation was attempted or confirmed. No authentication,
existing protected preview, separate `fraggy` project or project settings were
modified through this investigation. Direct Vercel Git documentation access also
failed proxy CONNECT 403; no current documentation text was invented.

## Implication for future delivery — requires separate approval

Do not push another branch or open a PR while “no deployments” remains the rule
unless an authorized operator first confirms a safe integration path. A PR marked
draft or `[skip ci]` is not a verified way to suppress Vercel. Do not guess a
`vercel.json` override or treat GitHub Actions success as deployment prevention.

An authorized owner can later review the connected repository, permitted preview
branches, build-ignore behavior, affected-project detection and exact production
branch. A narrowly scoped deployment-control change could then be proposed for
approval. This report neither requests nor makes that change. Keep the protected
existing preview and all PRs #8–#12 unmerged.
