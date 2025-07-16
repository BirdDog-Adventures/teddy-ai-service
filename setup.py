"""
Setup configuration for Teddy AI Service
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="teddy-ai-service",
    version="1.0.0",
    author="BirdDog, Inc.",
    author_email="engineering@birddog.com",
    description="AI-powered land intelligence platform for BirdDog",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BirdDog-Adventures/birddog-teddy",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "scripts"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-asyncio>=0.23.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.12.1",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
            "pre-commit>=3.6.0",
        ],
        "docs": [
            "mkdocs>=1.5.3",
            "mkdocs-material>=9.5.3",
        ],
    },
    entry_points={
        "console_scripts": [
            "teddy-api=api.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.sql"],
    },
)
