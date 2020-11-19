import setuptools

setuptools.setup(
    name='relay-py',
    version='0.0.1',
    packages=setuptools.find_packages(),
    install_requires=[
        'websockets',
        'pyyaml'
    ],
    python_requires='>=3.6.1',
)
