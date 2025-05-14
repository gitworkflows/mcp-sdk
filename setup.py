from setuptools import setup, find_packages

setup(
    name="mcp-sdk",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.1",
        "pydantic>=1.8.2",
        "rich>=10.0.0",
        "pyyaml>=5.4.1",
    ],
    entry_points={
        "console_scripts": [
            "mcp=mcp_sdk.cli:main",
        ],
    },
    author="Khulnasoft",
    author_email="support@khulnasoft.com",
    description="MCP SDK with dynamic CLI support",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/khulnasoft-lab/mcp-sdk",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 