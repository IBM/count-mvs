DEV_DOCKER_IMAGE=count-mvs-dev-image:latest
DEV_DIRECTORY=/count-mvs
INTEGRATION_TESTS='integration/test/'
UNIT_TESTS='test/'

docker:
	docker build -t $(DEV_DOCKER_IMAGE) .

lint: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make lint_local

format: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make format_local

test: unit_tests integration_tests

integration_tests: py3_integration_tests py2_integration_tests

py3_integration_tests:
	docker-compose down -v
	docker-compose build
	export INTEGRATION_TESTS=$(INTEGRATION_TESTS) && docker-compose up --abort-on-container-exit py3_integration
	docker-compose down -v

py2_integration_tests:
	docker-compose down -v
	docker-compose build
	export INTEGRATION_TESTS=$(INTEGRATION_TESTS) && docker-compose up --abort-on-container-exit py2_integration
	docker-compose down -v

unit_tests: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make unit_test_local UNIT_TESTS=$(UNIT_TESTS)

lint_local:
	python -m pylint -r n --rcfile=.pylintrc countMVS.py \
	test/*.py \
	integration/api/*.py \
	integration/test/*.py \
	integration/test/util/*.py

format_local:
	python -m yapf -i -p -r .

unit_test_local:
	python -m pytest $(UNIT_TESTS)
