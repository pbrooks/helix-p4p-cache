from setuptools import setup

setup(
    name="helix-p4p-cache",
    version="0.0.1",
    author="Peter Brooks",
    author_email="",
    description=("Helix P4P caching extensions"),
    license="MIT",
    keywords="perforce proxy cache",
    url="https://packages.python.org/helix-p4p-cache",
    packages=["cache"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        'console_scripts': ['p4p-flush=cache.flush:__main__',
                            'p4p-sync=cache.sync:__main__']
    }
)
