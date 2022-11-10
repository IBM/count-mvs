DEV_DOCKER_IMAGE=count-mvs-dev-image:latest
DEV_DIRECTORY=/count-mvs
UNIT_TESTS='src/tests/'

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

test: unit_tests

unit_tests: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make unit_test_local UNIT_TESTS=$(UNIT_TESTS)

unit_tests_py2: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make unit_test_local_py2 UNIT_TESTS=$(UNIT_TESTS)

unit_tests_py3: docker
	docker run                           \
		--rm                             \
		-v $(shell pwd):$(DEV_DIRECTORY) \
		-w $(DEV_DIRECTORY)              \
		$(DEV_DOCKER_IMAGE)              \
		make unit_test_local_py3 UNIT_TESTS=$(UNIT_TESTS)

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

unit_test_local: unit_test_local_py2 unit_test_local_py3

unit_test_local_py2:
	python2 -m pytest python2/$(UNIT_TESTS)

unit_test_local_py3:
	python3 -m pytest python3/$(UNIT_TESTS)
