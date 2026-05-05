.PHONY: fetch dev build

fetch:
	mkdir -p data
	python3 scripts/fetch_medium.py --username adhungel2 --devto-username ajaydhungel23 --out data/medium.json
	python3 scripts/fetch_credly.py --user ajay-dhungel.7261bfe6 --out data/credly.json
	python3 scripts/fetch_github.py --user ajaydhungel7 --out data/github.json \
		--pin flask-azure-k8s aws-cdk-chatbot railsflow-ci rubyrana

dev: fetch
	hugo server --buildFuture

build: fetch
	hugo --environment production --buildFuture
