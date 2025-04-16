# Codex Output

The following suggestions aim to drastically reduce code volume across the ResumeCoach project without changing functionality.

## 1. General Improvements
- Consolidate and remove unused dependencies (e.g., replace pickle/base64 with JSON for session history, drop `pyautogui` if only used privately).
- Introduce API codegen (OpenAPI/Swagger) to eliminate manual TypeScript/Python interface definitions.
- Centralize environment variable loading into shared utility to avoid repeated `os.environ.get` and `import.meta.env` logic.
- Adopt a mono‑repo pattern (Yarn workspaces or similar) to share common types, utilities, and reduce duplication.
- Automate formatting, linting, and type checks with pre‑commit/CICD to remove ad hoc script scaffolding.

## 2. Backend (Lambda) Refactoring
- Replace manual path/method routing with a microframework (AWS Chalice or FastAPI+Mangum) to remove large if/else blocks.
- Factor serialization/deserialization of session data into reusable decorators or utility classes.
- Store LLM prompt templates externally (JSON/YAML) and load at runtime to shrink inline code.
- Use Pydantic models for request validation and response serialization rather than custom JSON parsing and `create_response` logic.
- Move from pickle/base64 to pure JSON storage in DynamoDB for chat history, eliminating dependency on pickle and reducing complexity.
- Leverage AWS Lambda Powertools for structured logging, metrics, and error handling to replace custom implementations.

## 3. Frontend (React) Simplification
- Adopt React Query or SWR for data fetching (`/items`, `/analyze`, `/chat`), collapsing custom loading, error, and caching logic into standardized hooks.
- Generate TypeScript types from an OpenAPI specification to remove manual interface duplication.
- Abstract repeated UI patterns (buttons, textareas, status banners) into reusable components to reduce code in `App.tsx`.
- Introduce a UI component library (e.g., Chakra UI, Material UI) or CSS framework (Tailwind) to replace custom CSS files, significantly reducing styling code.
- Encapsulate localStorage/sessionStorage logic in a custom React hook (e.g., `usePersistedState`), removing inline persistence code.

## 4. Infrastructure (CDK) Optimization
- Use higher‑level CDK constructs and patterns (e.g., `aws-s3-deployment`, `HostedZone`, `DnsValidatedCertificate`) consistently to minimize custom boilerplate.
- Parameterize hard‑coded values (domain, table names) via CDK context or parameters to avoid duplicate code for different environments.
- Split large `infrastructure-stack.ts` into nested or multiple stacks for modularity, reducing file size per stack.
- Leverage built‑in `NodejsFunction` bundling for Python functions (or migrate to Node.js) to remove custom Docker bundling commands.

## 5. Documentation Automation
- Generate `project_code.md` and `RECENT_COMMIT_LOG.md` via CI and remove them from source control, cutting thousands of lines of generated content.
- Document API surface with OpenAPI/Swagger and host interactive docs, eliminating manual tables in README.
- Migrate in-depth README sections into a dedicated docs site (Docusaurus/Sphinx) and maintain a concise root README.
