from setuptools import setup, find_packages

setup(
    name="casys-token",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "py-algorand-sdk>=2.5.0",
        "pyteal>=0.26.0",
        "pydantic>=2.5.0",
        "pytest>=7.4.0",
        "python-dotenv>=1.0.0",
        "wheel>=0.42.0",
        "requests>=2.31.0"
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A decentralized finance platform built on Algorand",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/casys-token",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
