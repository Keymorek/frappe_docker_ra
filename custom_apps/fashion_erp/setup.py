from pathlib import Path

from setuptools import find_packages, setup


ROOT = Path(__file__).parent
version = {}
with open(ROOT / "fashion_erp" / "__init__.py", encoding="utf-8") as handle:
    exec(handle.read(), version)

install_requires = [
    line.strip()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
]


setup(
    name="fashion_erp",
    version=version["__version__"],
    description="Industry extensions for women's apparel ecommerce and garment manufacturing.",
    author="Keymorek",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    zip_safe=False,
)
