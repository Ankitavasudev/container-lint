from setuptools import setup, find_packages

setup(
    name="container-lint",
    version="1.0.0",
    description="Dockerfile & docker-compose.yml linter with security best practices",
    author="Ankit",
    author_email="ankitasalaria21@gmail.com",
    url="https://github.com/Ankitavasudev/container-lint",
    packages=find_packages(),
    install_requires=["pyyaml>=6.0"],
    entry_points={"console_scripts": ["container-lint=container_lint.linter:main"]},
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Quality Assurance",
    ],
)