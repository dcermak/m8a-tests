"""This module is not really intended to test anything, it mostly is just
present to pull the containers down in one step and not all of them
concurrently. If the environment variable ``BCI_DEVEL_REPO`` has been specified,
then repository will be replaced in the containers and whether this was
successful will be double checked here.

"""
import xml.etree.ElementTree as ET
from typing import List

import pytest
from bci_tester.data import ALL_CONTAINERS
from bci_tester.data import BCI_DEVEL_REPO
from bci_tester.data import MICRO_CONTAINER
from bci_tester.data import MINIMAL_CONTAINER


@pytest.mark.parametrize(
    "container_per_test",
    [
        cont
        for cont in ALL_CONTAINERS
        if cont not in (MINIMAL_CONTAINER, MICRO_CONTAINER)
    ],
    indirect=True,
)
def test_container_build_and_repo(container_per_test, host):
    """Test all containers with zypper in them whether at least the ``SLE_BCI``
    repository is present (if the host is unregistered). If a custom value for
    the repository url has been supplied, then check that it is correct.

    If the host is registered, then we check that there are more than one
    repository present.

    """

    def get_repos() -> List[ET.Element]:
        container_per_test.connection.run_expect([0], "zypper -n ref")
        repos = ET.fromstring(
            container_per_test.connection.run_expect(
                [0], "zypper -x repos -u"
            ).stdout
        )
        repo_list = [child for child in repos if child.tag == "repo-list"]
        assert len(repo_list) == 1
        return list(repo_list[0])

    # container-suseconnect will inject the correct repositories on registered
    # SLES hosts
    # => if the host is registered, we will have multiple repositories in the
    # container, otherwise we will just have the SLE_BCI repository
    suseconnect_injects_repos: bool = (
        host.system_info.type == "linux"
        and host.system_info.distribution == "sles"
        and host.file("/etc/zypp/credentials.d/SCCcredentials").exists
    )

    repos = get_repos()

    if suseconnect_injects_repos:
        for _ in range(5):
            if len(repos) > 1:
                break

            repos = get_repos()

        assert (
            len(repos) > 1
        ), "On a registered host, we must have more than one repository on the host"
    else:
        assert len(repos) == 1

    sle_bci_repo_candidates = [
        repo for repo in repos if repo.get("name") == "SLE_BCI"
    ]
    assert len(sle_bci_repo_candidates) == 1
    sle_bci_repo = sle_bci_repo_candidates[0]

    assert sle_bci_repo.get("name") == "SLE_BCI"
    assert len(list(sle_bci_repo)) == 1

    repo_url = list(sle_bci_repo)[0]
    assert repo_url.text == BCI_DEVEL_REPO

    container_per_test.connection.run_expect([0], "zypper -n ref")


@pytest.mark.parametrize(
    "container", [MINIMAL_CONTAINER, MICRO_CONTAINER], indirect=["container"]
)
def test_container_build(container):
    """Just pull down the minimal and micro containers and ensure that they
    launch.

    """
    container.connection.run_expect([0], "true")