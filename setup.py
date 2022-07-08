import setuptools

# Copyright © 2022 Relay Inc.

# for tests: (venv)$ pip install -e '.[testing]'

setuptools.setup(
    name='relay-py',
    version='0.0.1',
    packages=setuptools.find_packages(),
    install_requires=[
        'requests',
        'websockets',
        'pyyaml'
    ],
    extras_require={
        'testing': [
            'pytest',
            'pytest-asyncio'
        ]
    },
    python_requires='>=3.6.1',
)
