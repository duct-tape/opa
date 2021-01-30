import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="opa",
    version="0.0.1",
    author="Nick Garanko",
    author_email="nick@itdude.eu",
    description="Human friendly command line 1Password client.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/duct-tape/opa",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: BSD 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "click",
        "keyring",
        "pyperclip",
    ],
    entry_points="""
    [console_scripts]
    opa=opa:opa
    """
)
