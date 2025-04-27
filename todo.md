# ResumeCoach TODO List

## Recent Commits Checklist

- [ ] Infrastructure and CI/CD
  - [ ] 8099581 - Avi (2025-04-27): refactor(ci): consolidate workflow into single job
    - Combines build/test and deploy steps into a single job
    - Eliminates environment dependency issues
    - Improves workflow efficiency
  - [ ] f601e9c - Avi (2025-04-27): fix(ci): replace OIDC authentication with AWS access keys
    - Switches from OIDC to direct AWS access keys
    - Resolves role assumption errors
  - [ ] ad0f5e3 - Avi (2025-04-27): fix(ci): update GitHub Actions workflow to use OIDC authentication with AWS
    - Implemented OIDC authentication (later replaced with access keys)
  - [ ] 217aa55 - Avi (2025-04-27): chore(ci): update GitHub Actions workflow for improved dependency management
    - Enhanced dependency management in CI pipeline
    - Improved task execution
  - [ ] 32f5e6c - Avi (2025-04-27): chore(dependencies): update package-lock.json
    - Updated workspace configuration
    - Adjusted devDependencies

## Upcoming Tasks

- [ ] Frontend Development

  - [ ] Implement responsive design
  - [ ] Add user authentication
  - [ ] Create resume editor interface

- [ ] Backend Development

  - [ ] Set up database models
  - [ ] Implement API endpoints
  - [ ] Add authentication middleware

- [ ] Infrastructure
  - [ ] Configure CDK deployment for multiple environments
  - [ ] Set up monitoring and logging
  - [ ] Implement backup strategy
