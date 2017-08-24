#!/usr/bin/env python

import setuptools

setuptools.setup(
    name="invent",
    version="0.1",
    packages=["invent"],
    author="Fritz Grimpen",
    author_email="fritz@grimpen.net",
    url="https://github.com/fritz0705/invent",
    license="http://opensource.org/licenses/MIT",
    description="...",
    classifiers=[
            "Development Status :: 4 - Beta",
            "Programming Language :: Python :: 3.6",
    ],
    install_requires=[
    ],
    entry_points={
        "console_scripts": [
            "invent = invent.cli:main",
        ]
    },
    package_data={}
)
