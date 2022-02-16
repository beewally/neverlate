import ast
import re

import setuptools

_version_re = re.compile(r"__version__\s+=\s+(.*)")
with open("neverlate/__init__.py", "rb") as f:
    _match = _version_re.search(f.read().decode("utf-8"))
    if _match is None:
        raise SystemExit("No version found")
    version = str(ast.literal_eval(_match.group(1)))

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="neverlate",
    version=version,
    author="Brian Walters",
    author_email="brianrwalters@gmail.com",
    description="In your face notifications you can't miss for Google Calendar Events.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/beewally/neverlate",
    project_urls={
        "Bug Tracker": "https://github.com/beewally/neverlate/issues",
    },
    install_requires=[
        "PySide6",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
    ],
    packages=[
        "neverlate",
        # "google-api-python-client",
        # "google-auth-httplib2",
        # "google-auth-oauthlib",
    ],  # setuptools.find_packages()
    # package_dir={"": "src"},
    package_data={"": ["credentials.json", "images/*.png"]},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: POSIX",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business",
        "Topic :: Office/Business :: Scheduling",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "neverlate=neverlate.main:run",
        ]
    },
)
