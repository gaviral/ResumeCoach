SHELL := /bin/bash

.PHONY: setup dev-backend dev-frontend clean prepare-deploy deploy

# Setup both backend and frontend environments
setup: dev-backend dev-frontend

# Create virtualenv and install backend dependencies
dev-backend:
	uv venv .venv
	source .venv/bin/activate
	uv pip install -r backend/requirements.txt

# Install frontend dependencies
dev-frontend:
	cd frontend && npm install

# Clean local environments
clean:
	# Remove backend virtualenv and frontend node modules
	rm -rf .venv
	cd frontend && rm -rf node_modules

# Prepare frontend for deployment: clean, reinstall deps, and build assets
prepare-deploy: clean dev-backend dev-frontend
	# Remove cached frontend artifacts
	rm -rf frontend/node_modules frontend/package-lock.json
	# Install dependencies and run build
	cd frontend && npm install && npm run build

# Full deploy: build assets and deploy infrastructure via CDK
deploy: prepare-deploy
	# Install infrastructure dependencies and deploy
	cd infrastructure && npm install
	cd infrastructure && npx cdk deploy

# End of Makefile 