
.PHONY: setup build publish compile


VERSION := $(shell grep '^version =' pyproject.toml | sed 's/version = "\(.*\)"/\1/')


ver:
	@echo $(VERSION)

compile:
	uv pip compile pyproject.toml -o requirements.txt

publish: build compile
	git commit --allow-empty -a -m "Release version $(VERSION)"
	git push
	git tag v$(VERSION)
	git push --tags
	uv publish --token $$UV_PUBLISH_TOKEN

build:
	uv build

setup:
	uv venv --link-mode symlink

