from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-caselaws",
    version="0.2.0",
    description="GST Case Law Research CLI designed to easily integrate with appeal drafting workflows and plugins.",
    author="Antigravity",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
        "rich>=12.0.0",
        "beautifulsoup4>=4.10.0",
        "requests>=2.26.0",
        "pypdf>=3.0.0",
        "notebooklm-py>=0.5.0",
    ],
    entry_points={
        "console_scripts": [
            "caselaws-cli=cli_anything.caselaws.main:main",
        ],
    },
    python_requires=">=3.8",
)
