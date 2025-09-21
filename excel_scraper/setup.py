#!/usr/bin/env python3
"""
Setup script for Excel Scraper.
"""

from setuptools import setup, find_packages
import os
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text() if (this_directory / "README.md").exists() else ""

# Read requirements
requirements_path = this_directory / "requirements.txt"
with open(requirements_path) as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="excel-scraper",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Fast async web scraper optimized for Excel export",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Moses-Omondi/japan-carparts-scraper",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Office Suites",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "excel-scraper=excel_scraper.scripts.scrape:main",
        ],
    },
    include_package_data=True,
    package_data={
        "excel_scraper": ["config/*.json"],
    },
    keywords="web scraping, excel, async, e-commerce, data extraction",
    project_urls={
        "Bug Reports": "https://github.com/Moses-Omondi/japan-carparts-scraper/issues",
        "Source": "https://github.com/Moses-Omondi/japan-carparts-scraper",
        "Documentation": "https://github.com/Moses-Omondi/japan-carparts-scraper/blob/main/README.md",
    },
)