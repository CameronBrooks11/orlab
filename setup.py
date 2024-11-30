import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="orlab",
    version="0.2.5",  
    author="Cameron Brooks",
    author_email="cambrooks3393@gmail.com",
    description="OrLab is a Python module designed for interacting and scripting with OpenRocket, with enhanced capabilities for simulations and computational workflows.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CameronBrooks11/orlab",
    packages=setuptools.find_packages(),
    install_requires=[
        "jpype1>=0.6.3",
        "numpy"
    ],
    python_requires='>=3.6',
)
