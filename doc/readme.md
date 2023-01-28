# como instalar local y subir a pypi

pip install [carpeta del proyecto donde esta setup.py]

# how tu upload to  pypi

**verify last version**
sudo python3 -m pip install --user --upgrade setuptools wheel twine

**Create distribution files**
sudo python3 setup.py sdist bdist_wheel

**Upload the distribution archives**
twine upload dist/*

review the package in https://pypi.org/
