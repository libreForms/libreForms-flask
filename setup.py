from setuptools import find_packages, setup

setup(
    name='libreforms',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'flask',
        'gunicorn',
        'pandas',
        'plotly',
        'pymongo',
        'pytest',
        'coverage',
        'webargs',
    ],
)