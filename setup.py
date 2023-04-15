import setuptools

with open("README.md") as fh:
    long_description = fh.read()

from tools import __version__

setuptools.setup(
    name="gen-odoo-readme",
    version=__version__,
    author="Jorge E. Obiols",
    description="Tool to create README.rst files for Odoo",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jobiols/gen-readme",
    author_email="jorge.obiols@gmail.com",
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "gen-readme=tools.gen_readme:gen_readme",
        ],
    },
    include_package_data=True,
    data_files=[("mypackage", ["tools/gen_addon_readme.template"])],
    install_requires=["click==8.1.3", "jinja2==3.1.2", "docutils==0.19"],
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Documentation",
    ],
    keywords="odoo documentation readme rst",
)
