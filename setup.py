"""Setup configuration for Loxone FTP Client"""

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='loxone-ftp-client',
    version='1.0.0',
    description='FTP client for Loxone MiniServer temperature log retrieval',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Development Team',
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=[
        'python-dateutil>=2.8.0',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0.0',
            'pytest-cov>=2.10.0',
            'pytest-mock>=3.3.0',
            'black>=20.8b1',
            'flake8>=3.8.0',
            'mypy>=0.900',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
