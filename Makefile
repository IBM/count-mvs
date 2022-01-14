lint:
	pylint -r n --rcfile=.pylintrc countMVS.py

format:
	yapf -i -p -r .
