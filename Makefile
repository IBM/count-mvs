DEV_DOCKER_IMAGE=count-mvs-dev-image:latest
DEV_DIRECTORY=/count-mvs

docker:
	docker build -t $(DEV_DOCKER_IMAGE) .

lint: docker
	docker run -v $(shell pwd):$(DEV_DIRECTORY) -w $(DEV_DIRECTORY) $(DEV_DOCKER_IMAGE) make lint_local

format: docker
	docker run -v $(shell pwd):$(DEV_DIRECTORY) -w $(DEV_DIRECTORY) $(DEV_DOCKER_IMAGE) make format_local

test: unit_tests integration_tests

integration_tests:
	docker-compose down -v
	docker-compose build
	docker-compose run qradar

unit_tests: docker
	docker run -v $(shell pwd):$(DEV_DIRECTORY) -w $(DEV_DIRECTORY) $(DEV_DOCKER_IMAGE) make unit_test_local

lint_local:
	python -m pylint -r n --rcfile=.pylintrc countMVS.py

format_local:
	python -m yapf -i -p -r .

unit_test_local:
	python -m pytest test/
