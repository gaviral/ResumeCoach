**1. Configuration & Secrets → Lambda environment variables**  
The README lists three environment variables that the Lambda function needs—`ITEMS_TABLE_NAME`, `SESSIONS_TABLE_NAME`, and `LOG_LEVEL`. In the code, however, `backend/handler.py` (around lines 25-40) also expects **`OPENAI_API_PARAM_NAME`**, which is injected by the CDK stack and tells the function where in SSM Parameter Store the OpenAI key lives. Because this fourth variable isn’t documented, anyone running the function locally (SAM/Docker) or configuring it manually in the AWS console will omit it; the handler then logs _“FATAL: … not set”_ and every LLM call returns 503. **Severity – Medium.** The fix is to add `OPENAI_API_PARAM_NAME` to the README’s “Lambda env-vars” table (e.g., “Name of the SSM parameter that stores the OpenAI API key; falls back to `OPENAI_API_KEY` for local testing”).

**2. CI / CD Pipeline secrets**  
In the README’s CI section only the three AWS access-key secrets are mentioned. The actual workflow file (`.github/workflows/ci.yml`) also exports **`VITE_API_URL`** into the build, forwarding it from `secrets.VITE_API_URL`. When contributors fork the repo or a new maintainer sets up the pipeline, this missing secret will make the React build embed the literal string “undefined” as the base API URL—breaking runtime calls even though the build passes. **Severity – Low.** Document `VITE_API_URL` alongside the AWS secrets as “Base URL of the deployed API Gateway, injected into the Vite build.”

**3. CI step list (ESLint)**  
The README claims that step 1 of the pipeline runs ESLint after `npm ci`. In reality, `npm run check` (defined in the root `package.json` and invoked by CI) does only `tsc -b && vite build`; ESLint isn’t run anywhere in CI. The mismatch means developers expect lint errors to fail the build when they won’t, so style issues can slip into `main`. **Severity – Medium.** Either (a) remove the word “ESLint” from the README step list _or_ (b) add a new workflow step—`npm run -w frontend lint -- --max-warnings=0`—before the build so the docs and automation line up.

**4. Python dependency installer (`uv` vs `pip`)**  
The README summarises step 2 of CI as “pip install → pytest”, yet the workflow uses **`uv pip install`**, a drop-in replacement that’s much faster than vanilla pip. While this doesn’t break anything, developers who mimic the README exactly may see longer install times or mismatched lock hashes and wonder why. **Severity – Info.** Update the wording to “Python dependencies are installed with [uv](https://github.com/astral-sh/uv), then pytest runs.” No code change required.

**5. IAM permission for SSM key retrieval**  
The README correctly says the Lambda fetches `/ResumeCoach/OpenAIApiKey` from SSM but doesn’t mention that the Lambda role now has an attached policy allowing `ssm:GetParameter`. That policy is added in `infrastructure/lib/infrastructure-stack.ts` (look for `backendLambda.addToRolePolicy`). Readers might otherwise assume they must add the permission manually. **Severity – Low.** Append a note to the “Secrets” row in the Tech-stack table: “The CDK stack automatically grants the function `ssm:GetParameter` on this parameter.”

**6. Known Limitations – CloudFront origin class**  
Under “Known Limitations” the README says the project still uses the deprecated `S3Origin` class and plans to migrate to `S3BucketOrigin`. The CDK stack has already switched—see the call to `origins.S3BucketOrigin.withOriginAccessIdentity` in the distribution definition. The limitation is outdated and may confuse maintainers. **Severity – Low.** Delete that bullet or replace it with another genuine limitation.

**7. System-architecture diagram note**  
In the Mermaid diagram a footnote reads “(S3 origin class upgrade pending)”. As explained above, the upgrade is complete, so the comment is obsolete and slightly misleading. **Severity – Info.** Remove or re-phrase the note to reflect the current state.

**8. Local Development – environment variable fallback**  
The README never tells developers that they can bypass SSM entirely by exporting **`OPENAI_API_KEY`**. Yet `handler.py` intentionally falls back to that variable if `OPENAI_API_PARAM_NAME` is absent—handy for quick local tests. New contributors may waste time mocking SSM when a single `export` would work. **Severity – Info.** In the Local-development section add a sentence like: “For local runs you can simply `export OPENAI_API_KEY=sk-…`; the Lambda will use it when the SSM parameter name isn’t provided.”

**9. Dev-tooling list omits Black**  
The Technology-stack table lists “ESLint, Prettier, Husky, lint-staged, Pygments” but forgets **Black**. The `lint-staged` config formats any staged `*.py` file with `python -m black`, and Black is pinned in `requirements.txt`. Leaving it out understates enforced tooling and may surprise Python contributors. **Severity – Info.** Add “Black” to that bullet list.

**10. Production URL certainty**  
The README front-matter states that the app “is live at https://coach.aviralgarg.com”. The repository indeed provisions that domain, but the repo alone can’t confirm whether the site is actually up or still points to this stack. If the domain lapses or a DNS change occurs, the README becomes inaccurate. **Severity – Needs-manual-confirmation.** Either verify periodically and keep the link, or soften the wording to “When deployed, the app is served at …” or move the link to a status badge that you update as part of release ops.
