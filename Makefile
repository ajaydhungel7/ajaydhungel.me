.PHONY: fetch dev build test test-unit test-integration

fetch:
	mkdir -p data
	python3 scripts/fetch_medium.py --username adhungel2 --out data/medium.json
	python3 scripts/fetch_devto.py --username ajaydhungel23 --out data/devto.json
	python3 scripts/fetch_credly.py --user ajay-dhungel.7261bfe6 --out data/credly.json
	python3 scripts/fetch_github.py --user ajaydhungel7 --out data/github.json \
		--pin flask-azure-k8s aws-cdk-chatbot railsflow-ci rubyrana

test-unit:
	.venv/bin/pytest tests/unit/ tests/test_infrastructure.py -v

test-integration: fetch
	.venv/bin/pytest tests/integration/ -v

test: test-unit test-integration

dev: fetch
	hugo server --buildFuture

build: fetch test
	hugo --environment production --buildFuture
