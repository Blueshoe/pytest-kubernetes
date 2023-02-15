from pathlib import Path
import subprocess
import pytest


pytest_plugins = ["pytester"]


@pytest.fixture(scope="session")
def a_unique_image(request):
    name = "a-unique-image:latest"
    subprocess.run(
        f"docker build -t {name} -f {(Path(__file__).parent / Path('./fixtures/Dockerfile')).resolve()}"
        f" {(Path(__file__).parent / Path('./fixtures/')).resolve()}",
        shell=True,
    )
    request.addfinalizer(lambda: subprocess.run(f"docker rmi {name}", shell=True))
    return name
