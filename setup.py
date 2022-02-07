import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="neverlate",
    version="0.0.2",
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
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "neverlate=neverlate.main:run",
        ]
    },
)
