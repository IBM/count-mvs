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
	export INTEGRATION_TESTS=$(INTEGRATION_TESTS) && docker-compose up py3_integration --abort-on-container-exit
	docker-compose down -v

py2_integration_tests:
	docker-compose down -v
	docker-compose build
	export INTEGRATION_TESTS=$(INTEGRATION_TESTS) && docker-compose up py2_integration --abort-on-container-exit
	docker-compose down -v

unit_tests: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make unit_test_local UNIT_TESTS=$(UNIT_TESTS)

lint_local:
	python -m pylint -r n --rcfile=.pylintrc countMVS.py

format_local:
	python -m yapf -i -p -r .

unit_test_local:
	python -m pytest $(UNIT_TESTS)
