import setuptools

# Copyright © 2022 Relay Inc.

# for tests: (venv)$ pip install -e '.[testing]'

setuptools.setup(
    name='relay-py',
    version='2.0.0-alpha',
    packages=setuptools.find_packages(),
    install_requires=[
        'requests',
        'websockets',
        'pyyaml',
    ],
    extras_require={
        'testing': [
            'pytest',
            'pytest-asyncio',
        ],
        'docs': [
            'mkdocs',
            'mkdocs-material',
            'mkdocstrings[python]',
        ],
    },
    python_requires='>=3.6.1',
)
