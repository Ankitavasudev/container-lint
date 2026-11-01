from setuptools import setup, find_packages

setup(
    name="container-lint",
    version="2.0.0",
    description="Lint Dockerfiles and docker-compose files without a Docker daemon",
    author="Ankita Salaria",
    author_email="ankitasalaria21@gmail.com",
    url="https://github.com/Ankitavasudev/container-lint",
    packages=find_packages(include=["container_lint", "container_lint.*"]),
    install_requires=["pyyaml>=6.0"],
    entry_points={"console_scripts": ["container-lint=container_lint.cli:main"]},
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Quality Assurance",
    ],
)
