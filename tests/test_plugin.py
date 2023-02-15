from pathlib import Path
import subprocess


def test_vendor_fixture_cases(testdir):
    # testdir is a pytest fixture
    vendor_test = (Path(__file__).parent / Path("./vendor.py")).resolve()
    result = testdir.runpytest(vendor_test, "--k8s-cluster-name", "kubernetes-plugin")
    result.assert_outcomes(passed=9)
    # assert no cluster is running
    process = subprocess.run(
        ["docker", "ps", "--format", '\'{"Names":"{{ .Names }}"}\''],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    assert "pytest-kubernetes-plugin" not in process.stdout
