DEV_DOCKER_IMAGE=count-mvs-dev-image:latest
DEV_DIRECTORY=/count-mvs
UNIT_TESTS='src/tests/'
INTEGRATION_TESTS='integration/test/'

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

unit_tests: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make unit_tests_local UNIT_TESTS=$(UNIT_TESTS)

unit_tests_py2: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make unit_tests_local_py2 UNIT_TESTS=$(UNIT_TESTS)

unit_tests_py3: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make unit_tests_local_py3 UNIT_TESTS=$(UNIT_TESTS)

integration_tests: integration_tests_py3 integration_tests_py2

integration_tests_py3:
	docker-compose down -v
	docker-compose build
	export INTEGRATION_TESTS=$(INTEGRATION_TESTS) && docker-compose up --abort-on-container-exit py3_integration
	docker-compose down -v

integration_tests_py2:
	docker-compose down -v
	docker-compose build
	export INTEGRATION_TESTS=$(INTEGRATION_TESTS) && docker-compose up --abort-on-container-exit py2_integration
	docker-compose down -v

lint_local: lint_local_py2 lint_local_py3

lint_local_py2:
	python2 -m pylint -r n --rcfile=python2/.pylintrc python2/src/*.py

lint_local_py3:
	python3 -m pylint -r n --rcfile=python3/.pylintrc python3/src/*.py

format_local: format_local_py2 format_local_py3

format_local_py2:
	python2 -m yapf -i -p --style python2/.style.yapf -r python2/src/

format_local_py3:
	python3 -m yapf -i -p --style python3/.style.yapf -r python3/src/

unit_tests_local: unit_tests_local_py2 unit_tests_local_py3

unit_tests_local_py2:
	cd python2 && python2 -m pytest --cov-report xml:coverage.xml --cov-report term --cov=countMVS $(UNIT_TESTS)

unit_tests_local_py3:
	cd python3 && python3 -m pytest --cov-report xml:coverage.xml --cov-report term --cov=countMVS $(UNIT_TESTS)
