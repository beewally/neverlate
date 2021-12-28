import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="calendar_alert",
    version="0.0.1",
    author="Brian Walters",
    author_email="brianrwalters@gmail.com",
    description="In your face notifications for your google calendar events.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/beewally/calendar_alert",
    install_requires=[
        "PySide6",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
    ],
    packages=[
        "calendar_alert",
        # "google-api-python-client",
        # "google-auth-httplib2",
        # "google-auth-oauthlib",
    ],  # setuptools.find_packages()
    package_data={"": ["credentials.json", "images/*.png"]},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "LICENSE :: OTHER/PROPRIETARY LICENSE",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "calender_alert=calendar_alert.main:run",
        ]
    },
)
