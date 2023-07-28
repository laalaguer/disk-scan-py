export cmd=scan.py

# Create user environment.
install:
	python3 --version
	pip3 install --user -r requirements.txt
	chmod +x ${cmd}

# Create developer environment.
dep:
	python3 --version
	python3 -m venv .env && . .env/bin/activate && pip3 install -r requirements.txt
	chmod +x ${cmd}
