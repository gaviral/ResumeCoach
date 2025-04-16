SHELL := /bin/bash

.PHONY: setup dev-backend dev-frontend clean prepare-deploy deploy

setup: dev-backend dev-frontend

dev-backend:
	uv venv .venv
	source .venv/bin/activate
	uv pip install -r backend/requirements.txt

dev-frontend:
	cd frontend && npm install

clean:
	# Remove backend virtualenv and frontend node modules
	rm -rf .venv
	cd frontend && rm -rf node_modules

prepare-deploy: clean dev-backend dev-frontend
	# Remove cached frontend artifacts
	rm -rf frontend/node_modules frontend/package-lock.json
	# Install dependencies and run build
	cd frontend && npm install && npm run build

deploy: prepare-deploy
	# Install infrastructure dependencies and deploy
	cd infrastructure && npm install
	cd infrastructure && npx cdk deploy

