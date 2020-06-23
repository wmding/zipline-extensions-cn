from setuptools import setup, find_packages
setup(
    name = 'zipline_extensions_cn',
    version = '0.0.1',
    packages = find_packages(),
    python_requires='>=3.5.*',
    install_requires=[
        'zipline',
        'alphalens',
    ],
    entry_points={
        'console_scripts': [
            'zipline_cn = zipline_extensions_cn.__main__:main',
        ],
    },
)
