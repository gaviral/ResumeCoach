**Project Tenets**

1.  **Prioritize Market Relevance & Hireability (Mid-tier US/Canada):** Choices must align with skills/tools demonstrably valued by target employers, justified by research.
2.  **Build Incrementally, Learn Foundational Concepts First:** Start simple, understand basics, iterate. Local before cloud.
3.  **Uphold Engineering Best Practices (Modularity, Testing, Docs):** Maintain high standards for code quality, structure, testing (BE/FE), and documentation throughout.
4.  **Optimize for Cost-Effectiveness & Leverage Free Tiers:** Minimize costs, use free tiers, prefer local dev/test.
5.  **Justify Technology Choices Explicitly (Market Focus):** Select tools based on researched market relevance *and* technical fit, not just novelty.

Now, let's apply these tenets to flesh out the roadmap provided in the Deep Research results, making specific decisions and adding detail.

---

## Detailed & Tenet-Driven Roadmap: LLM Experimentation Platform

**(Derived from Deep Research Report & Guided by Project Tenets)**

**Overall Goal:** Evolve the existing `ResumeCoach` project (within its single GitHub repo) into a public, open-source, modular LLM experimentation platform hosted on GitHub with a live demo. The platform will support multiple use cases, prioritize local experimentation, integrate market-relevant cloud services (AWS Bedrock, OpenAI) and tools (LangChain, LangSmith, MLflow, Ollama, common testing/CI/CD tools), incorporate robust full-stack testing and observability, and use engineering practices valued by mid-tier US/Canada tech companies in 2025.

---

### Phase 1: Refactoring, Local Setup & Foundational Practices

**(Goal: Restructure for modularity, enable local LLM runs via Ollama, establish basic testing (BE/FE) & logging infrastructure, grounding in best practices.)**

1.  **Feature: Repository Structure Refactor (Modular Packages)**
    *   **Description:** Restructure the single GitHub repository using a simple package-based approach to enable modular development. Create distinct top-level directories (e.g., `packages/`) containing sub-packages for different concerns. Refactor existing `frontend`, `backend`, and `infrastructure` code into this structure.
    *   **Decisions & Reasoning:**
        *   *Choice:* Simple directory structure (`packages/`) vs. formal monorepo tools (Nx, Turborepo).
        *   *Reasoning:* T1 (Market): Demonstrates modularity which is key. Formal tools add overhead not strictly required for target MLE roles. T2 (Incremental): Simple structure is easier first. T3 (Practices): Achieves modularity. T5 (Justify): Sufficient, transferable skill without unnecessary complexity.
        *   *Judgment:* Use simple `packages/` structure.
    *   **MLE/SWE Skill:** Modular code design, Python packaging (`pyproject.toml`/`setup.py`), TypeScript project references (`tsconfig.json`), dependency management (`npm`/`pnpm` workspaces ideally), large-scale refactoring, Git management.
    *   **Hireability Signal (Market-Focused):** Shows ability to structure scalable applications (T1, T3), essential SWE skill for any mid-tier company. Keywords: Modular Architecture, Code Refactoring, Full-Stack Development, Software Design.
    *   **Granularity & Iterative Step:** Create `packages/frontend`, `packages/backend-common` (for shared utils/models), `packages/backend-resume-module` (initial specific logic), `packages/infra`. Move code incrementally, adjusting imports, `package.json` dependencies/workspaces, `tsconfig.json` paths, Python import paths, and CDK stack references (`sourceCode:` path for Lambda). Start by refactoring the backend.
    *   **Infra Recommendation:** N/A (Code structure).
    *   **Cost Consideration:** None.
    *   **Tooling Justification (Market Relevance):** Standard directory/packaging practices are universal (T5). Using `pnpm` workspaces (optional but recommended) is a modern approach for managing dependencies in such structures.

2.  **Feature: Integrate Local LLM Execution via Ollama**
    *   **Description:** Add capability to the backend (likely in `backend-common` or a new `backend-llm-providers` package) to call locally running LLMs via Ollama. Abstract the LLM client logic (e.g., using a simple Strategy pattern or Factory) to support multiple providers later (Ollama, OpenAI, Bedrock). Implement the Ollama client first. Test with a popular, performant local model like `Mistral-7B`.
    *   **Decisions & Reasoning:**
        *   *Choice:* Which local model to start with?
        *   *Reasoning:* T1 (Market): Research highlighted Ollama's popularity & Mistral as a key OSS model. T2 (Incremental): Start with one reliable, well-known model. T5 (Justify): Mistral-7B is relevant and good for initial local testing.
        *   *Judgment:* Start with Mistral-7B via Ollama.
        *   *Choice:* How to abstract providers?
        *   *Reasoning:* T2 (Incremental): Simple interface/base class is sufficient. T3 (Practices): Promotes extensibility.
        *   *Judgment:* Use a base class/interface defining an `invoke` method, with concrete implementations for each provider (starting with `OllamaProvider`).
    *   **MLE/SWE Skill:** Ollama usage/integration, API interaction (local HTTP), code abstraction (Interfaces/Strategy pattern), local debugging, Python `requests` or `httpx`.
    *   **Hireability Signal (Market-Focused):** Experience with local OSS models via Ollama is highly relevant based on research (T1, T5). Shows cost-awareness (T4) and practical experimentation skills. Keywords: Ollama, Local LLM, Open Source Models (Mistral), Model Integration, API Integration, Software Design Patterns.
    *   **Granularity & Iterative Step:** Confirm Ollama installed & pull model (`ollama pull mistral`). Create provider abstraction (`LLMProvider` interface/base class). Implement `OllamaProvider` making calls to `http://localhost:11434/api/generate`. Write a basic test script within the backend package to instantiate `OllamaProvider` and call its `invoke` method with a simple prompt.
    *   **Infra Recommendation:** N/A (Local tooling integration).
    *   **Cost Consideration:** Zero cost (T4).
    *   **Tooling Justification (Market Relevance):** Ollama aligns with researched local dev trends (T1, T5).

3.  **Feature: Foundational Backend Testing (Pytest + Mocking)**
    *   **Description:** Set up `pytest`. Implement unit tests for utility functions and core logic within the backend packages. Crucially, write tests for components that *use* the `LLMProvider` abstraction, using Python's built-in `unittest.mock` to patch the `invoke` method and simulate deterministic LLM responses (successes, errors, specific content) for testing surrounding logic.
    *   **Decisions & Reasoning:**
        *   *Choice:* Mocking library?
        *   *Reasoning:* T2 (Incremental), T5 (Justify): `unittest.mock` is built-in, sufficient, standard.
        *   *Judgment:* Use `unittest.mock`.
    *   **MLE/SWE Skill:** Unit testing, TDD principles, `pytest` framework, mocking (`unittest.mock.patch`), testing abstracted interfaces, Python software testing.
    *   **Hireability Signal (Market-Focused):** Demonstrates core SWE discipline essential for mid-tier roles (T1, T3). Shows understanding of testing code with external dependencies. Keywords: Pytest, Unit Testing, Mocking, Backend Testing, Testable Code Design.
    *   **Granularity & Iterative Step:** `pip install pytest pytest-mock` (optional but helpful). Create `tests/` dirs in relevant backend packages. Write tests for simple utils first. Then, write a test for a function that calls `llm_provider.invoke()`, using `@mock.patch('path.to.provider.invoke', return_value='mocked response')` to control the outcome and assert the calling function's behavior.
    *   **Infra Recommendation:** N/A.
    *   **Cost Consideration:** None.
    *   **Tooling Justification (Market Relevance):** `pytest` is the Python standard (T5). `unittest.mock` is built-in.

4.  **Feature: Foundational Frontend Testing (Jest + RTL)**
    *   **Description:** Set up Jest and React Testing Library (RTL) for the `packages/frontend`. Write initial unit/component tests, starting with simple presentational components (checking rendering via `getByText`, etc.) and potentially snapshot tests.
    *   **Decisions & Reasoning:**
        *   *Choice:* Snapshot vs. behavioral tests first?
        *   *Reasoning:* T2 (Incremental): Snapshots are easy for static components. Basic `getByText` checks are fundamental RTL practice. T3 (Practices): RTL encourages testing user-perceivable output.
        *   *Judgment:* Start with simple rendering checks using RTL queries (`getByText`, `queryByRole`, etc.). Use snapshots sparingly for purely presentational components if desired.
    *   **MLE/SWE Skill:** Frontend testing, Jest, React Testing Library (RTL), component testing, basic snapshot testing (optional), TypeScript testing.
    *   **Hireability Signal (Market-Focused):** Shows commitment to full-stack quality (T1, T3), using industry-standard tools (T5). Relevant for roles requiring FE awareness. Keywords: Jest, React Testing Library, Frontend Testing, Component Testing, Full-Stack Development.
    *   **Granularity & Iterative Step:** Install dependencies (`@testing-library/react`, etc.). Configure Jest (e.g., in `vite.config.ts`). Write a test for a simple button or display component, asserting its text content is rendered using `screen.getByText(...)`.
    *   **Infra Recommendation:** N/A.
    *   **Cost Consideration:** None.
    *   **Tooling Justification (Market Relevance):** Jest/RTL are the React standard (T5).

5.  **Feature: Basic Structured Logging (Lambda Powertools + CloudWatch)**
    *   **Description:** Integrate `aws-lambda-powertools-python`'s `Logger` utility into the backend Lambda function(s) for structured JSON logging. Configure logging levels. Ensure logs are captured in CloudWatch Logs and are easily queryable (via CloudWatch Logs Insights).
    *   **Decisions & Reasoning:**
        *   *Choice:* Base `logging` vs. Powertools `Logger`?
        *   *Reasoning:* T1 (Market): Powertools is AWS best practice, valuable skill. T2 (Incremental): Small step, high value. T3 (Practices): Enforces good structure. T5 (Justify): Relevant AWS serverless skill.
        *   *Judgment:* Use `aws-lambda-powertools-python`.
    *   **MLE/SWE Skill:** Structured logging, `aws-lambda-powertools-python`, AWS CloudWatch Logs, CloudWatch Logs Insights (basic queries), serverless observability fundamentals.
    *   **Hireability Signal (Market-Focused):** Demonstrates knowledge of AWS serverless best practices (T1, T3, T5) and operational awareness crucial for production systems. Keywords: Structured Logging, AWS Lambda Powertools, AWS CloudWatch, Observability, Serverless.
    *   **Granularity & Iterative Step:** Add `aws-lambda-powertools` to backend requirements. Import `Logger` from `aws_lambda_powertools`. Instantiate `logger = Logger(service="resume-module")`. Use `@logger.inject_lambda_context` decorator on handler. Replace `print`/`logging` calls with `logger.info()`, `logger.error()`, etc. Deploy and run a query in CloudWatch Logs Insights (e.g., `fields @timestamp, @message | sort @timestamp desc | limit 20`).
    *   **Infra Recommendation:** AWS CloudWatch (Managed) - Standard. Powertools is a library.
    *   **Cost Consideration:** Powertools free. CloudWatch Logs very low cost / generous free tier (T4).
    *   **Tooling Justification (Market Relevance):** Powertools is AWS recommended best practice for Lambda (T5). CloudWatch is standard AWS logging (T1).

---

### Phase 2: Foundational Local Experimentation & Evaluation (Resume Module + LangSmith) + Basic CI

**(Goal: Implement core resume analysis using local LLMs/LangChain, integrate LangSmith tracing, compare local models, set up basic CI.)**

1.  **Feature: Implement Resume Module Backend (Local LLM + LCEL)**
    *   **Description:** Build the core logic for the `packages/backend-resume-module` using LangChain Expression Language (LCEL). This chain should take resume/JD text, use the `OllamaProvider` (configured for Mistral-7B first), apply a well-defined prompt template, and parse the output. Experiment qualitatively by running different inputs and potentially trying another local model (e.g., Llama 3 8B if feasible) via Ollama to compare results.
    *   **Decisions & Reasoning:**
        *   *Choice:* LCEL vs. legacy Chains?
        *   *Reasoning:* T1 (Market), T5 (Justify): LCEL is modern LangChain standard.
        *   *Judgment:* Use LCEL.
        *   *Choice:* Which models to compare locally?
        *   *Reasoning:* T1 (Market): Mistral & Llama are highly relevant based on research. T2 (Incremental): Comparing two popular local models is a good first experiment.
        *   *Judgment:* Compare Mistral-7B and Llama-3-8B-Instruct (or similar available Llama 3 variant).
    *   **MLE/SWE Skill:** LangChain Expression Language (LCEL), `ChatPromptTemplate`, `ChatOllama`, `StrOutputParser`, Prompt Engineering (v1), local model comparison, Python application logic.
    *   **Hireability Signal (Market-Focused):** Practical LangChain/LCEL usage (T1, T5), local OSS model experimentation (T1), core LLM application building. Keywords: LangChain, LCEL, Prompt Engineering, Ollama, Mistral, Llama 3, Model Comparison.
    *   **Granularity & Iterative Step:** Define `ChatPromptTemplate`. Create `ChatOllama` instance pointing to `mistral`. Chain using LCEL (`prompt | model | parser`). Test invocation with sample data. Modify `ChatOllama` instance to point to `llama3`. Rerun and compare outputs qualitatively.
    *   **Infra Recommendation:** N/A (Local).
    *   **Cost Consideration:** Zero LLM cost (T4).
    *   **Tooling Justification (Market Relevance):** LCEL is current LangChain practice. Mistral/Llama are relevant OSS models (T1, T5).

2.  **Feature: Integrate LangSmith for Tracing Local Runs**
    *   **Description:** Integrate LangSmith SDK. Configure environment variables (`LANGCHAIN_TRACING_V2`, etc.). Ensure traces for the LCEL chains executed in the previous step (using local Ollama models) appear correctly in the LangSmith UI. Focus on analyzing the traces for execution flow, latency of steps, and logged inputs/outputs.
    *   **Decisions & Reasoning:**
        *   *Choice:* Focus on tracing only?
        *   *Reasoning:* T2 (Incremental), Evaluation Tenet: Tracing first.
        *   *Judgment:* Focus only on tracing and visualization initially.
    *   **MLE/SWE Skill:** LangSmith SDK integration, LLM Tracing, debugging LLM applications, visualizing execution flow, latency analysis (basic).
    *   **Hireability Signal (Market-Focused):** High value skill based on LangSmith's rapid adoption (T1, T5). Shows debugging and observability capabilities for complex LLM apps. Keywords: LangSmith, LLM Observability, Tracing, Debugging, LangChain.
    *   **Granularity & Iterative Step:** Set LangSmith env vars. Rerun the LCEL chain from previous step. Log into LangSmith web UI, find your project, and inspect the traces generated. Identify the different steps (prompt formatting, model invocation, parsing). Note the latency for the model call.
    *   **Infra Recommendation:** LangSmith (Managed) - Use free tier (T4).
    *   **Cost Consideration:** LangSmith free tier sufficient (T4).
    *   **Tooling Justification (Market Relevance):** LangSmith is highly relevant for LangChain users, addressing a key need (T1, T5).

3.  **Feature: Basic Frontend for Resume Module (Connect to Backend)**
    *   **Description:** Connect the existing basic React frontend for the resume module to the *deployed* backend Lambda endpoint (via API Gateway). Ensure the UI can send the resume/JD text, trigger the backend workflow (which should be configurable to use the local Ollama model *when run locally via SAM/Flask wrapper* or potentially OpenAI/Bedrock *when deployed*, though local is the focus now), display loading states, handle errors, and render the analysis result. Use basic `useState` for component state.
    *   **Decisions & Reasoning:**
        *   *Choice:* State management?
        *   *Reasoning:* T2 (Incremental): `useState` sufficient for this single module initially.
        *   *Judgment:* Use `useState`.
    *   **MLE/SWE Skill:** React (`useState`, `useEffect`, `axios`), TypeScript, API integration, error handling (frontend), state management (component-level), interacting with serverless backends.
    *   **Hireability Signal (Market-Focused):** Demonstrates full-stack capability (T1, T3), connecting a frontend to an ML backend service. Keywords: React, TypeScript, Full-Stack Development, API Integration, AWS Lambda, API Gateway.
    *   **Granularity & Iterative Step:** Update the `axios` call in the frontend component to hit the deployed API Gateway endpoint URL (use an environment variable `VITE_API_URL`). Implement `useState` hooks for `isLoading`, `error`, `analysisResult`. Trigger the API call on button click. Display results or error messages appropriately. Test against the deployed backend (ensure backend is configured to use a provider, maybe default to OpenAI initially for cloud test, or setup local SAM invoke).
    *   **Infra Recommendation:** Uses existing FE/BE deployment.
    *   **Cost Consideration:** API Gateway/Lambda have free tiers; potential OpenAI costs if testing deployed version with it (T4).
    *   **Tooling Justification (Market Relevance):** Standard full-stack integration practices.

4.  **Feature: Basic CI Pipeline (GitHub Actions - Add Linting)**
    *   **Description:** Enhance the Phase 1 CI pipeline (GitHub Actions). Add steps to run linters (`ruff` or `flake8`+`isort` for Python, `eslint` for TS/React) and formatters (`black`, `prettier`) and fail the build if checks fail.
    *   **MLE/SWE Skill:** CI/CD pipeline enhancement, GitHub Actions, code linting tools (`ruff`/`flake8`, `eslint`), code formatting tools (`black`, `prettier`), maintaining code quality automatically.
    *   **Hireability Signal (Market-Focused):** Demonstrates commitment to code quality and automation (T3), standard practices in professional SWE/MLE teams (T1). Keywords: CI/CD, GitHub Actions, Linting, Code Formatting, Code Quality, Automation.
    *   **Granularity & Iterative Step:** Choose linters/formatters (recommend `ruff` and `black` for Python, `eslint` and `prettier` for TS/React). Add config files for them (`pyproject.toml` section for ruff/black, `.eslintrc.js`, `.prettierrc.js`). Add `run:` steps to the `ci.yml` workflow (after dependency install, before tests) like `ruff check .`, `black --check .`, `npm run lint`, `npm run format:check`. Ensure the workflow fails if checks don't pass.
    *   **Infra Recommendation:** GitHub Actions (Managed) (T4).
    *   **Cost Consideration:** None (uses free Actions tier) (T4).
    *   **Tooling Justification (Market Relevance):** These specific linters/formatters are widely adopted standards in the Python and TS/React ecosystems (T5).

---

### Phase 3: Cloud Model Integration & Modular Frontend Structure

**(Goal: Integrate cloud LLM APIs (OpenAI first, Bedrock conditionally) as alternative providers, compare them with local models, refactor the frontend for modularity, and add basic observability dashboards.)**

1.  **Feature: Integrate OpenAI API as LLM Provider**
    *   **Description:** Integrate the OpenAI API (`gpt-4o-mini` or a similarly cost-effective yet capable model like GPT-3.5-Turbo) as a selectable LLM provider in the backend (`LLMProvider` abstraction). Securely manage the API key using **AWS Secrets Manager**. Update the backend logic and potentially add a simple frontend control to allow choosing between Ollama (local) and OpenAI (cloud) for the resume analysis module. Implement basic cost tracking for OpenAI calls.
    *   **Decisions & Reasoning:**
        *   *Choice:* Which OpenAI model?
        *   *Reasoning:* T4 (Cost): `gpt-4o-mini` or `gpt-3.5-turbo` offer good balance of capability/cost for initial cloud integration. T1 (Market): Experience with any GPT model via API is relevant.
        *   *Judgment:* Start with `gpt-4o-mini` or `gpt-3.5-turbo`.
        *   *Choice:* Secret management?
        *   *Reasoning:* T1 (Market), T3 (Practices), T5 (Justify): Env vars insecure (per README). Secrets Manager is standard AWS practice for secrets.
        *   *Judgment:* Use AWS Secrets Manager.
    *   **MLE/SWE Skill:** Calling external APIs (OpenAI Python client), secure secrets management (AWS Secrets Manager integration with Lambda/CDK), extending abstracted code, error handling for network/API issues, comparing cloud vs. local model performance/cost/quality, basic cost tracking implementation.
    *   **Hireability Signal (Market-Focused):** Research confirms OpenAI API usage is dominant (T1). Demonstrating secure integration using AWS best practices (Secrets Manager) and the ability to compare cloud vs. local models is highly practical and valuable for mid-tier roles (T1, T3, T5). Keywords: OpenAI API, GPT-4o-mini, AWS Secrets Manager, API Integration, Cloud Services, Model Comparison, Secure Development.
    *   **Granularity & Iterative Step:** Create secret in Secrets Manager. Update CDK IAM role for Lambda to allow `secretsmanager:GetSecretValue`. Implement `OpenAIProvider` class using `openai` Python library, fetching the key from Secrets Manager via `boto3`. Add logic to the resume module backend to instantiate/use this provider based on a configuration setting or request parameter. Add basic logic to estimate and log token usage based on OpenAI documentation/response metadata. Test locally (mocking Secrets Manager or using temp env var) and then deploy to test cloud integration. Add a simple dropdown in the FE to select "Ollama (Local)" or "OpenAI".
    *   **Infra Recommendation:** AWS Secrets Manager (Managed) - Low cost, secure (T4, T5).
    *   **Cost Consideration:** OpenAI API calls cost per token. Secrets Manager cost is minimal (T4).
    *   **Tooling Justification (Market Relevance):** OpenAI API essential (T1). Secrets Manager is AWS standard (T1, T5). `openai` Python library is standard.

2.  **Feature: Integrate AWS Bedrock as LLM Provider (Conditional)**
    *   **Description:** *Evaluate based on ongoing market watch - if Bedrock skills seem increasingly valuable for mid-tier roles*: Integrate AWS Bedrock as a third LLM provider option. Select one or two relevant, performant models available via Bedrock (e.g., **Anthropic Claude 3 Sonnet** or **Llama 3 8B/70B** if available via Bedrock). Use `boto3` and LangChain's Bedrock integration (`langchain-aws`). Ensure IAM permissions are correct via CDK. Extend the provider selection mechanism in the backend and frontend. Perform qualitative and basic quantitative (latency, estimated cost) comparisons against Ollama and OpenAI for the resume task.
    *   **Decisions & Reasoning:**
        *   *Choice:* Integrate Bedrock now or later?
        *   *Reasoning:* T1 (Market): Research shows Bedrock adoption is currently low (~2%) but growing, especially in AWS shops. Integrating it adds breadth but OpenAI is higher priority. T2 (Incremental): Can be deferred if phase feels too large.
        *   *Judgment:* Include as *conditional* based on perceived market value increase. If included, prioritize *after* OpenAI is solid.
        *   *Choice:* Which Bedrock model(s)?
        *   *Reasoning:* T1 (Market): Claude models are strong performers and often highlighted with Bedrock. Using Llama 3 on Bedrock leverages OSS familiarity. T5 (Justify): Choose models distinct from OpenAI (like Claude) or popular OSS (Llama 3).
        *   *Judgment:* Start with Claude 3 Sonnet (good balance) or Llama 3 8B if available.
    *   **MLE/SWE Skill:** AWS Bedrock API usage (`boto3`), LangChain AWS integrations (`langchain-aws`), comparing different foundation models (quality, cost, latency across providers), IAM permissions management, extending abstractions further.
    *   **Hireability Signal (Market-Focused):** Demonstrates familiarity with AWS's strategic LLM offering (T1, T5), valuable for AWS-centric companies. Shows ability to work with multiple cloud ML APIs. Keywords: AWS Bedrock, Anthropic Claude, Llama 3 (on Bedrock), Boto3, Cloud ML Services, Multi-Cloud (conceptually), Model Comparison.
    *   **Granularity & Iterative Step:** Update CDK IAM role for Lambda to allow `bedrock:InvokeModel`. Implement `BedrockProvider` class using `boto3` (or `langchain-aws` helpers) to invoke the chosen model ID. Update provider selection logic (BE/FE). Test calls, log results/metrics, compare qualitatively with Ollama/OpenAI outputs for the same inputs.
    *   **Infra Recommendation:** AWS Bedrock (Managed).
    *   **Cost Consideration:** Bedrock incurs per-token costs, varies by model (T4).
    *   **Tooling Justification (Market Relevance):** While adoption is emerging, Bedrock is AWS's main offering, potentially important for AWS shops (T1, T5). `boto3` is the standard AWS SDK.

3.  **Feature: Modular Frontend Refactor (Routing/Sidebar/Tabs)**
    *   **Description:** Implement the planned frontend refactoring using `react-router-dom`. Create a main application layout (e.g., `AppLayout.tsx`) containing a persistent **sidebar navigation** menu. Define routes for existing (`/resume`) and future modules (`/playground`, `/rag`, `/agents`, `/settings`). Move the resume analysis UI into its own dedicated component loaded via the `/resume` route. Ensure navigation between (currently few) routes works smoothly.
    *   **Decisions & Reasoning:**
        *   *Choice:* Sidebar vs. Tabs?
        *   *Reasoning:* T3 (Practices): Sidebar is common for multi-tool platforms, scales better visually than tabs as modules increase.
        *   *Judgment:* Implement a sidebar navigation.
        *   *Choice:* Routing library?
        *   *Reasoning:* T1 (Market), T5 (Justify): `react-router-dom` is the standard.
        *   *Judgment:* Use `react-router-dom`.
    *   **MLE/SWE Skill:** React functional components, `react-router-dom` (routing, layouts, links), state management considerations across routes (may need Context API or Zustand soon), modular frontend architecture, UI/UX structure, TypeScript.
    *   **Hireability Signal (Market-Focused):** Critical for platform vision. Shows ability to structure complex SPAs (T1, T3), vital for full-stack roles or building usable ML tools. Keywords: React Router, Frontend Architecture, Modular UI, SPA, Full-Stack Development, UI/UX Design.
    *   **Granularity & Iterative Step:** `npm install react-router-dom`. Create `AppLayout.tsx` with a basic `Sidebar` component (just links for now). Define routes in `main.tsx` or `App.tsx` using `<BrowserRouter>` and `<Routes>`. Create `ResumePage.tsx` and move the resume UI logic there, rendering it via `<Route path="/resume" element={<ResumePage />} />`. Add links in the sidebar.
    *   **Infra Recommendation:** N/A (Frontend code).
    *   **Cost Consideration:** None.
    *   **Tooling Justification (Market Relevance):** `react-router-dom` is standard for React SPAs (T5). Modular FE design is a universal best practice (T3).

4.  **Feature: Basic Observability Dashboards/Metrics**
    *   **Description:** Create a basic **CloudWatch Dashboard** visualizing key metrics for the deployed Lambda function(s) (invocations, errors, duration, potentially throttles). Also, instrument backend code to calculate and log estimated **token counts and costs** for *each* LLM provider (OpenAI, Bedrock if integrated) using the structured logger (Powertools). Ensure this cost/token info is visible in CloudWatch Logs Insights and potentially surfaceable via LangSmith traces if applicable (e.g., as metadata).
    *   **Decisions & Reasoning:**
        *   *Choice:* Where to view metrics?
        *   *Reasoning:* T1(Market), T4(Cost), T5(Justify): CloudWatch is standard/free tier for basic infra metrics. LangSmith excels at traces/LLM specifics. Custom cost logging needed regardless.
        *   *Judgment:* Use CloudWatch for infra metrics, log custom cost/token metrics there, leverage LangSmith for trace-level latency/metadata.
    *   **MLE/SWE Skill:** AWS CloudWatch Dashboards creation/configuration, cost estimation logic for LLM APIs, structured logging (Powertools), data visualization interpretation, operational monitoring fundamentals.
    *   **Hireability Signal (Market-Focused):** Operational awareness (cost, performance) is key for MLEs in mid-tier companies (T1). Shows practical approach to monitoring crucial non-functional requirements. Keywords: Observability, Monitoring, AWS CloudWatch Dashboards, Cost Management, Performance Monitoring, Serverless Operations.
    *   **Granularity & Iterative Step:** Create dashboard in AWS Console, add widgets for Lambda metrics. Implement functions in `backend-common` to estimate token count (e.g., using `tiktoken` for OpenAI, provider docs for others) and calculate cost based on known pricing. Call these functions after LLM responses and log results using Powertools logger (`logger.info({"provider": "openai", "input_tokens": X, ... "estimated_cost": Y})`). Verify logs in CloudWatch Insights. Check if LangSmith automatically picks up any logged metadata.
    *   **Infra Recommendation:** CloudWatch Dashboards (Managed, free) (T4). Uses existing logging.
    *   **Cost Consideration:** Minimal CloudWatch costs (T4). Focuses on *tracking* API costs.
    *   **Tooling Justification (Market Relevance):** CloudWatch standard for AWS (T1). Cost awareness is vital. `tiktoken` is OpenAI's library for token counting (T5).

---

### Phase 4: Generic Experimentation, RAG/Agents & Advanced Evaluation/Testing

**(Goal: Expand the platform with generic experimentation, basic RAG/Agent capabilities using market-relevant tools, enhance evaluation, and implement more rigorous testing.)**

1.  **Feature: Generic Prompt Experimentation Module (UI + Backend)**
    *   **Description:** Build the "Playground" module (`/playground` route). Implement a flexible React UI allowing selection of installed LLM providers (Ollama, OpenAI, Bedrock), inputting multi-line prompts, adjusting basic parameters (temperature, max tokens - display defaults), viewing formatted responses, and seeing basic metrics (latency, cost/tokens from Phase 3). Implement the corresponding backend endpoint to handle these generic requests via the LLM provider abstraction.
    *   **Decisions & Reasoning:**
        *   *Choice:* Which parameters to expose initially?
        *   *Reasoning:* T2 (Incremental): Temperature and max tokens are most common/impactful.
        *   *Judgment:* Start with temperature, max tokens.
    *   **MLE/SWE Skill:** Full-stack development, React (forms, dynamic UI), API design (flexible endpoint), handling LLM parameters, building developer/experimentation tooling.
    *   **Hireability Signal (Market-Focused):** Directly builds the core platform value (T1). Shows ability to create tools supporting the MLE workflow itself, demonstrating deeper understanding. Keywords: LLM Playground, Prompt Engineering Tools, Experimentation Platform, Full-Stack Development, Developer Tools.
    *   **Granularity & Iterative Step:** Create `PlaygroundPage.tsx` component and route. Build UI form elements (provider dropdown, prompt textarea, parameter inputs, submit button, response display area, metrics display area). Create `POST /playground/run` endpoint in backend, taking provider, prompt, params in request body. Backend logic selects provider, passes params, invokes LLM, returns response + metadata. Connect FE form state and `axios` call.
    *   **Infra Recommendation:** Uses existing serverless stack.
    *   **Cost Consideration:** Cost depends on provider used (T4).
    *   **Tooling Justification (Market Relevance):** Building such internal/external tools is a common MLE/SWE task (T1).

2.  **Feature: Basic RAG Module (Local Vector DB First)**
    *   **Description:** Implement a basic RAG module (`/rag` route). Backend: Allow single `.txt` upload -> chunk text -> generate embeddings using **`sentence-transformers` (local model)** -> store in **ChromaDB (local persistence)** -> perform similarity search -> construct prompt -> call selected LLM provider. Frontend: UI for file upload, query input, display retrieved chunks (optional), display final LLM response.
    *   **Decisions & Reasoning:**
        *   *Choice:* Embedding model?
        *   *Reasoning:* T2 (Incremental), T4 (Cost): Local SentenceTransformer is free, good starting point. T1 (Market): ST is popular.
        *   *Judgment:* Use a standard SentenceTransformer model (e.g., `all-MiniLM-L6-v2`).
        *   *Choice:* Vector Database?
        *   *Reasoning:* T1 (Market), T5 (Justify): Research showed Chroma/FAISS lead open-source popularity. Chroma offers easy persistence. T2 (Incremental): Start local. T4 (Cost): Free.
        *   *Judgment:* Use ChromaDB locally, configured for file system persistence.
    *   **MLE/SWE Skill:** RAG pipeline implementation, text chunking (e.g., `RecursiveCharacterTextSplitter`), embedding generation (`sentence-transformers`), Vector Databases (ChromaDB API), similarity search, prompt engineering for RAG, handling file uploads (backend/frontend), integrating multiple components.
    *   **Hireability Signal (Market-Focused):** RAG is *highly* in demand (T1). Implementing it end-to-end using popular OS tools (Chroma, ST) is a major portfolio highlight (T1, T5). Keywords: RAG, Vector Database, ChromaDB, Sentence Transformers, Embeddings, Information Retrieval, Full-Stack ML.
    *   **Granularity & Iterative Step:** Add `sentence-transformers`, `chromadb`, `pypdf` (optional for PDF later), `python-multipart` (for FE uploads) to backend requirements. Implement backend logic for chunking, embedding, storing in Chroma (point to a local directory for persistence). Implement retrieval logic. Create LangChain chain combining retrieval and LLM call. Create `/rag` endpoint. Build `/rag` page in React with file input (`<input type="file">`), query input, submit button, response display. Test end-to-end locally.
    *   **Infra Recommendation:** ChromaDB (Self-hosted locally via library/persistence, or simple Docker container if preferred).
    *   **Cost Consideration:** Free using local models/DB (T4). Using cloud embedding APIs would add cost.
    *   **Tooling Justification (Market Relevance):** RAG is critical skill (T1). ChromaDB and SentenceTransformers are popular, relevant open-source choices based on research (T1, T5).

3.  **Feature: Explore Basic Agentic Workflow (LangChain Agents)**
    *   **Description:** Implement a *simple* agent module (`/agent` route) using **LangChain Agents** (more mature/documented than `openai-agents-python` for initial exploration, easier integration). Example: an agent that can use the RAG module's retriever as a tool *or* perform a basic calculation using Python REPL tool. Focus on defining the tool, initializing the agent executor, and observing the execution trace in LangSmith. Build a minimal UI to input a task and see the agent's final answer and maybe intermediate steps/thoughts.
    *   **Decisions & Reasoning:**
        *   *Choice:* LangChain Agents vs. `openai-agents-python` SDK?
        *   *Reasoning:* T2 (Incremental): LangChain agents are more integrated, likely easier starting point. T5 (Justify): LangChain is already in use, broader agent framework knowledge useful. `openai-agents-python` is newer, less documented/stable maybe.
        *   *Judgment:* Start with LangChain Agents. Can explore SDK later if desired.
    *   **MLE/SWE Skill:** Agentic LLM concepts, LangChain Agents (`create_openai_tools_agent` or similar), defining tools for LLMs, multi-step reasoning (observing), debugging agent behavior via tracing (LangSmith).
    *   **Hireability Signal (Market-Focused):** Shows awareness of emerging agent tech (T1). LangChain experience itself is valuable. Demonstrates ability to integrate complex LLM patterns. Keywords: LLM Agents, Agentic Systems, LangChain Agents, Tool Use, Multi-Step Reasoning, LangSmith.
    *   **Granularity & Iterative Step:** Define a LangChain `Tool` wrapping the RAG retriever logic (or a simple math function). Choose an agent setup (e.g., OpenAI Tools agent). Create an `AgentExecutor`. Implement `/agent` backend endpoint taking a task string. Build `/agent` page in React with task input and response display. Run a task, observe LangSmith trace.
    *   **Infra Recommendation:** Uses existing LLM providers.
    *   **Cost Consideration:** Agents can be token-intensive (T4).
    *   **Tooling Justification (Market Relevance):** LangChain is relevant (T1, T5). Exploring agents demonstrates engagement with cutting-edge LLM applications.

4.  **Feature: Advanced Backend & Frontend Testing**
    *   **Description:** Increase test coverage significantly. Backend: Write integration tests for module endpoints (e.g., testing the `/resume/analyze` endpoint with mocked providers). Implement more sophisticated LLM evaluation tests (EDD style) for core workflows like resume analysis or RAG based on defined criteria. Frontend: Write integration/interaction tests for the main UI flows using RTL (e.g., test submitting the resume form and displaying results, test the playground interaction). Mock API calls using `msw` (Mock Service Worker) or similar for FE integration tests.
    *   **Decisions & Reasoning:**
        *   *Choice:* FE mocking library?
        *   *Reasoning:* T1 (Market), T5 (Justify): `msw` is becoming a standard for mocking API calls in FE tests.
        *   *Judgment:* Use `msw` for FE API mocking.
    *   **MLE/SWE Skill:** Integration testing (BE/FE), advanced mocking (LLM outputs, API calls), Evaluation Driven Development (EDD) test implementation, frontend interaction testing (RTL `userEvent`), `msw` usage, test coverage analysis (optional).
    *   **Hireability Signal (Market-Focused):** Robust testing across the stack is a major signal of engineering maturity highly valued by mid-tier companies (T1, T3). Experience with testing complex interactions (FE, BE, ML) is key. Keywords: Integration Testing, End-to-End Testing (simulated), LLM Testing, EDD, Mock Service Worker (msw), Test Coverage, Full-Stack Testing.
    *   **Granularity & Iterative Step:** Backend: Write a `pytest` integration test for an API endpoint using a test client (e.g., FastAPI's `TestClient` if wrapping Lambda locally, or direct invoke). Write an EDD-style test asserting specific content in RAG output for a known query/doc. Frontend: Install `msw`. Define mock handlers for backend API endpoints. Write a test using RTL and `userEvent` to simulate filling the playground form, clicking submit, and asserting the (mocked) response is displayed.
    *   **Infra Recommendation:** N/A (Testing code/libraries).
    *   **Cost Consideration:** None (local testing).
    *   **Tooling Justification (Market Relevance):** `pytest` standard (T5). `msw` popular for FE mocking (T5). EDD concepts relevant for ML testing (T1).

---

### Phase 5: MLOps Polish, Documentation & Public Release Prep

**(Goal: Implement robust CI/CD, integrate experiment tracking (MLflow), finalize documentation, polish UI/UX, and prepare the project for public release and demo.)**

1.  **Feature: Integrate Experiment Tracking (MLflow)**
    *   **Description:** Integrate **MLflow** tracking into the experimentation workflows (Generic Playground, potentially RAG/Agent modules). Run the **MLflow Tracking Server locally via Docker**. Modify backend code to log parameters (prompt, model, temp), metrics (latency, cost, potentially evaluation scores later), and possibly input/output examples as artifacts using the `mlflow` client. Make the MLflow Run ID visible or linkable from the UI if possible.
    *   **Decisions & Reasoning:**
        *   *Choice:* Which experiment tracker?
        *   *Reasoning:* T1 (Market), T5 (Justify): Research overwhelmingly showed MLflow is dominant.
        *   *Judgment:* Use MLflow.
        *   *Choice:* Hosted vs. Local MLflow?
        *   *Reasoning:* T2 (Incremental), T4 (Cost): Local Docker setup is free, sufficient for learning/portfolio.
        *   *Judgment:* Run MLflow locally via Docker.
    *   **MLE/SWE Skill:** MLflow usage (client API, tracking server setup via Docker), experiment tracking best practices, MLOps tooling integration, logging artifacts.
    *   **Hireability Signal (Market-Focused):** MLflow experience is a *very* common requirement/desirable skill in MLE postings (T1, T5). Demonstrates understanding of systematic experimentation. Keywords: MLflow, Experiment Tracking, MLOps, Model Comparison, Reproducibility.
    *   **Granularity & Iterative Step:** Run MLflow Docker image (`docker run -p 5000:5000 ...`). Set `MLFLOW_TRACKING_URI` env var. In backend handlers for `/playground/run` (and potentially others), wrap logic with `mlflow.start_run()`. Use `mlflow.log_params()`, `mlflow.log_metrics()`. Maybe save input/output to a file and use `mlflow.log_artifact()`. Explore the MLflow UI at `http://localhost:5000`. Consider adding the `run_id` to the API response to display in FE.
    *   **Infra Recommendation:** MLflow Server (Self-hosted via Docker locally) (T4).
    *   **Cost Consideration:** Free locally (T4).
    *   **Tooling Justification (Market Relevance):** MLflow dominance makes it the most practical choice (T1, T5).

2.  **Feature: Comprehensive Documentation & Repo Polish**
    *   **Description:** Write comprehensive documentation for the public GitHub repo. Thoroughly update/rewrite `README.md` covering motivation, features, architecture (diagrams), detailed local setup (Ollama models, env vars, MLflow), usage guide for *all* modules, tech stack list, and link to live demo. Create clear `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`. Ensure good Python docstrings and TypeScript comments for key modules/functions. Clean up any dead code or commented-out experiments. Standardize project structure and naming conventions.
    *   **MLE/SWE Skill:** Technical writing, documentation structure, Markdown expertise, diagramming (Mermaid/other), writing setup/usage guides, code commenting best practices, open-source project presentation.
    *   **Hireability Signal (Market-Focused):** Polished documentation and a clean repo are crucial for making a strong impression with a public portfolio project (T1, T3). Signals professionalism and strong communication skills. Keywords: Documentation, README, Technical Writing, Open Source, Code Quality, Communication.
    *   **Granularity & Iterative Step:** Iteratively rewrite README sections. Create standard contributing/CoC files. Run a documentation generator for Python/TS code (optional, e.g., Sphinx, TypeDoc) or manually add comprehensive docstrings/comments. Review file structure for clarity.
    *   **Infra Recommendation:** N/A.
    *   **Cost Consideration:** None.
    *   **Tooling Justification (Market Relevance):** High-quality documentation is universally valued (T3, T5).

3.  **Feature: Full CI/CD Pipeline (Incl. Deployment via CDK)**
    *   **Description:** Implement a full CI/CD pipeline using **GitHub Actions**. CI (on PRs): Run linters, formatters, all backend tests (`pytest`), all frontend tests (Jest/RTL). CD (on merge to `main`): Build frontend assets (`npm run build`), run `cdk synth`, and run `cdk deploy --require-approval never` to deploy changes to AWS (Infra via CDK, Lambda code updates, S3 asset sync for frontend). Manage AWS credentials securely via GitHub OIDC connector or secrets. Ensure CloudFront invalidation happens after S3 sync.
    *   **Decisions & Reasoning:**
        *   *Choice:* CI/CD Tool?
        *   *Reasoning:* T1(Market), T4(Cost), T5(Justify): GitHub Actions is common, free for public repos, integrates well.
        *   *Judgment:* Use GitHub Actions.
        *   *Choice:* Credential Management?
        *   *Reasoning:* T3(Practices): OIDC is best practice for GitHub->AWS auth. Secrets are fallback.
        *   *Judgment:* Use GitHub OIDC Connector if possible, otherwise GitHub Secrets.
    *   **MLE/SWE Skill:** End-to-end CI/CD pipeline implementation, GitHub Actions (workflows, triggers, secrets, OIDC), deployment automation (CDK), frontend build process, CloudFront invalidation, secure credential management for CI/CD, MLOps/DevOps automation.
    *   **Hireability Signal (Market-Focused):** Demonstrates ability to fully automate the build, test, deploy cycle for a full-stack application including IaC (T1, T3, T5). Core MLOps/DevOps skill highly valued. Keywords: CI/CD, Continuous Deployment, GitHub Actions, AWS CDK, Infrastructure as Code (IaC), Automation, MLOps, DevOps, Full-Stack Deployment.
    *   **Granularity & Iterative Step:** Configure GitHub OIDC provider with AWS (or create IAM user with keys stored as GH Secrets). Create/update `cd.yml` workflow. Add jobs for: BE tests, FE tests, FE build (`npm run build`), CDK deploy (needs AWS creds, runs `cdk deploy`). Ensure CDK stack correctly handles S3 deployment with CloudFront invalidation (CDK's `s3deploy.BucketDeployment` often does this). Test the full pipeline by merging a small change.
    *   **Infra Recommendation:** GitHub Actions (Managed) (T4). Uses existing AWS deployment stack.
    *   **Cost Consideration:** Free Actions tier likely sufficient (T4). `cdk deploy` interacts with AWS resources.
    *   **Tooling Justification (Market Relevance):** GitHub Actions + CDK is a modern, relevant CI/CD setup for AWS serverless projects (T1, T5).

4.  **Feature: Final Polish, Live Demo & Launch**
    *   **Description:** Conduct final end-to-end testing on the *live deployed demo*. Fix remaining bugs. Polish the UI/UX for clarity and usability. Ensure the live demo link in the README works and points to the functional application. Consider adding basic rate limiting or other safeguards if exposing LLM endpoints directly, or require users to enter their own API keys for cloud providers in the UI (managed via `localStorage` perhaps). Officially "launch" by ensuring the repo is public and well-presented.
    *   **Decisions & Reasoning:**
        *   *Choice:* How to handle API keys for public demo?
        *   *Reasoning:* T4(Cost), T3(Practices): Exposing your keys is insecure/costly. Requiring user keys is safest.
        *   *Judgment:* Add UI fields for users to (optionally) enter their own OpenAI/Bedrock keys, store in `localStorage` only. Default to local Ollama if no keys provided.
    *   **MLE/SWE Skill:** End-to-end testing (deployed), debugging production issues, UI/UX polish, deployment verification, basic security/cost considerations for public apps.
    *   **Hireability Signal (Market-Focused):** Successfully delivering a polished, functional, public full-stack application demonstrates significant capability and follow-through (T1, T3). The live demo is crucial portfolio evidence. Keywords: Live Demo, End-to-End Testing, Public Release, Portfolio Project, Full-Stack Application.
    *   **Granularity & Iterative Step:** Add optional API key input fields to FE settings/playground. Implement logic to use user-provided keys if available. Test all features thoroughly on the deployed version. Fix final bugs/styling issues. Ensure README link points correctly. Make repo public.
    *   **Infra Recommendation:** Uses existing deployed AWS resources.
    *   **Cost Consideration:** Requiring user keys drastically reduces your operational cost risk for the public demo (T4).
    *   **Tooling Justification (Market Relevance):** Shipping a functional application is the ultimate goal (T1).

---
