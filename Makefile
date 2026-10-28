TOML_FILE := pyproject.toml
MASTER_BRANCH := main
DEV_BRANCH := dev

# The osv-scanner release `make audit` runs, and each platform's binary's sha256, from the
# release's osv-scanner_SHA256SUMS.
OSV_SCANNER_VERSION := 2.7.0
OSV_SCANNER_SHA256_linux_amd64 := 160c6253e2922e9e0a6a9771c5c4c40a4b3c6090b34a3cdd5e80c96cc2e4218b
OSV_SCANNER_SHA256_linux_arm64 := 4061ef4c021ed3c47f203b818f337e351336cc5cd67c0274fc36bd1dfc728dd7
OSV_SCANNER_SHA256_darwin_amd64 := e82c5df7ab0a42dff29a1cd0660711447b56b4c0483ff66ad8634df10fd81a45
OSV_SCANNER_SHA256_darwin_arm64 := d4926ef8da134332543be276dff157e4c170f99ad91fc48e89448a8816bdf70b
OSV_SCANNER := .tools/bin/osv-scanner

VERSION := $(shell sed -n 's/^version *= *"\(.*\)"/\1/p' $(TOML_FILE))

.PHONY: dev-version
dev-version:
	@set -e; \
	git fetch origin $(MASTER_BRANCH); \
	CURRENT_VERSION=$$(sed -n 's/^version *= *"\(.*\)"/\1/p' $(TOML_FILE)); \
	MASTER_VERSION=$$(git show origin/$(MASTER_BRANCH):$(TOML_FILE) \
		| sed -n 's/^version *= *"\(.*\)"/\1/p'); \
	echo "dev version:    $$CURRENT_VERSION"; \
	echo "master version: $$MASTER_VERSION"; \
	if [ "$$CURRENT_VERSION" != "$$MASTER_VERSION" ]; then \
		echo "dev has already been versioned; nothing to do."; \
		exit 0; \
	fi; \
	NEW_VERSION=$$(echo "$$CURRENT_VERSION" \
		| awk -F. '{printf "%d.%d.%d", $$1, $$2, $$3+1}'); \
	echo "Bumping $$CURRENT_VERSION -> $$NEW_VERSION"; \
	sed -i.bak \
		's/^version *= *".*"/version = "'"$$NEW_VERSION"'"/' \
		$(TOML_FILE); \
	rm -f $(TOML_FILE).bak; \
	poetry lock; \
	git add $(TOML_FILE) poetry.lock; \
	git commit -m "Bump version to v$$NEW_VERSION"; \
	git push origin HEAD:$(DEV_BRANCH)

.PHONY: release
release:
	@set -e; \
	VERSION=$$(sed -n 's/^version *= *"\(.*\)"/\1/p' $(TOML_FILE)); \
	echo "Releasing v$$VERSION"; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	git push origin "v$$VERSION"; \
	gh release create "v$$VERSION" \
		--title "v$$VERSION" \
		--notes "Release v$$VERSION"


.PHONY: install
install:
	@echo "📦 Installing dependencies..."
	poetry install
	@$(MAKE) -s hooks
	@echo "✅ Installation complete!"

.PHONY: hooks
hooks:
	@mkdir -p .git/hooks
	@cp scripts/hooks/* .git/hooks/ 2>/dev/null || true
	@chmod +x .git/hooks/*

.PHONY: clean
clean: clean-build clean-pyc clean-test clean-docs

.PHONY: clean-build
clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr deployments/build/
	rm -fr deployments/Dockerfiles/open_aea/packages
	rm -fr pip-wheel-metadata
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +
	find . -name '*.svn' -exec rm -fr {} +
	find . -name '*.db' -exec rm -fr {} +
	rm -fr .idea .history
	rm -fr venv

.PHONY: clean-docs
clean-docs:
	rm -fr site
	rm -fr docs/reference

.PHONY: clean-pyc
clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test:
	rm -fr .tox/
	rm -f .coverage
	find . -name ".coverage*" -not -name ".coveragerc" -exec rm -fr "{}" \;
	rm -fr coverage.xml
	rm -fr htmlcov/
	rm -fr .hypothesis
	rm -fr .pytest_cache
	rm -fr .mypy_cache/
	find . -name 'log.txt' -exec rm -fr {} +
	find . -name 'log.*.txt' -exec rm -fr {} +

# plow through requests when TOO MANY REQUESTS error is returned the brutal way (not bucket)
.PHONY: tests
tests:
	poetry run pytest tests -vv --reruns 2 --reruns-delay 10

.PHONY: fmt
fmt:
	poetry run ruff format tests derive_py examples benchmarks scripts
	poetry run ruff check tests derive_py examples benchmarks scripts --fix

.PHONY: lint
lint:
	poetry run ruff check tests derive_py examples benchmarks scripts


.PHONY: docs
docs: clean-docs
	poetry run python scripts/sync-readme.py
	poetry run python scripts/generate-ref-pages.py
	poetry run mkdocs build --site-dir site


.PHONY: generate-models
generate-models:
	curl https://docs.derive.xyz/openapi.json | poetry run python scripts/pretty-json.py > specs/openapi.json
	curl https://docs.derive.xyz/websocket.asyncapi.json | poetry run python scripts/pretty-json.py > specs/websocket.json
	curl https://docs.derive.xyz/subscriptions.asyncapi.json | poetry run python scripts/pretty-json.py > specs/subscriptions.json
	poetry run python scripts/patch_spec.py specs/openapi.json
	poetry run python scripts/extract-asyncapi-schemas.py
	poetry run python scripts/generate_models.py
	poetry run ruff format derive_py/data_types/generated_models.py derive_py/data_types/channel_models.py
	poetry run ruff check --fix derive_py/data_types/generated_models.py derive_py/data_types/channel_models.py

.PHONY: generate-api
generate-api:
	python scripts/generate-api.py
	poetry run ruff format derive_py/_clients/
	poetry run ruff check --fix derive_py/_clients/

.PHONY: generate-rest-async-http
generate-rest-async-http:
	python scripts/generate-rest-async-http.py
	poetry run ruff format tests/test_clients/test_rest/test_async_http
	poetry run ruff check --fix tests/test_clients/test_rest/test_async_http

.PHONY: sync-ws-tests
sync-ws-tests:
	@echo "Syncing http tests -> websocket tests"
	@rsync -av --no-perms --omit-dir-times \
		--exclude='__init__.py' \
		--exclude='conftest.py' \
		--exclude='test_api.py' \
		--exclude='test_session.py' \
		--exclude='__pycache__/' \
		tests/test_clients/test_rest/test_async_http/ \
		tests/test_clients/test_websocket/
	@echo "Done."

.PHONY: download-abis
download-abis:
	@echo "Downloading ABIs..."
	poetry run python scripts/download-abis.py

.PHONY: codegen-all
codegen-all: generate-models generate-api generate-rest-async-http sync-ws-tests fmt lint

.PHONY: typecheck
typecheck:
	poetry run pyright derive_py tests examples benchmarks

.PHONY: deptry
deptry:
	poetry run deptry derive_py

.PHONY: audit
audit: install-osv-scanner
	$(OSV_SCANNER) scan source --lockfile=poetry.lock

# One pinned release, locally and in CI alike, fetched once and kept only while its sha256 matches.
.PHONY: install-osv-scanner
install-osv-scanner:
	@set -e; \
	case "$$(uname -s)-$$(uname -m)" in \
		Linux-x86_64) want="$(OSV_SCANNER_SHA256_linux_amd64)"; asset=linux_amd64 ;; \
		Linux-aarch64 | Linux-arm64) want="$(OSV_SCANNER_SHA256_linux_arm64)"; asset=linux_arm64 ;; \
		Darwin-x86_64) want="$(OSV_SCANNER_SHA256_darwin_amd64)"; asset=darwin_amd64 ;; \
		Darwin-arm64) want="$(OSV_SCANNER_SHA256_darwin_arm64)"; asset=darwin_arm64 ;; \
		*) echo "install-osv-scanner: no pinned release for $$(uname -s)-$$(uname -m)" >&2; exit 1 ;; \
	esac; \
	sha256() { { sha256sum "$$1" 2> /dev/null || shasum -a 256 "$$1"; } | cut -d' ' -f1; }; \
	if [ -x "$(OSV_SCANNER)" ] && [ "$$(sha256 "$(OSV_SCANNER)")" = "$$want" ]; then exit 0; fi; \
	mkdir -p "$(dir $(OSV_SCANNER))"; \
	tmp="$(OSV_SCANNER).download"; \
	curl -sSfL -o "$$tmp" \
		"https://github.com/google/osv-scanner/releases/download/v$(OSV_SCANNER_VERSION)/osv-scanner_$$asset"; \
	got="$$(sha256 "$$tmp")"; \
	if [ "$$got" != "$$want" ]; then \
		rm -f "$$tmp"; \
		echo "osv-scanner $(OSV_SCANNER_VERSION) $$asset: sha256 $$got, expected $$want" >&2; exit 1; \
	fi; \
	chmod +x "$$tmp"; \
	mv "$$tmp" "$(OSV_SCANNER)"; \
	echo "installed osv-scanner $(OSV_SCANNER_VERSION) $$asset at $(OSV_SCANNER)"

.PHONY: check_diff
check_diff:
	@git diff --exit-code

.PHONY: demo
demo:
	poetry run bash scripts/demos/all.sh

.PHONY: all
all: download-abis codegen-all fmt lint deptry audit typecheck docs tests
