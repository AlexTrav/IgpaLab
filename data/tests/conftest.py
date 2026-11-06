import pytest

from generator.common import load_config
from generator.pipeline import generate


@pytest.fixture(scope="session")
def cfg():
    return load_config(students=600)


@pytest.fixture(scope="session")
def data(cfg):
    return generate(cfg)
