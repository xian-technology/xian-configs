"""xian-configs ships only the networks and node templates that are used."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_only_the_local_and_mainnet_networks_are_shipped():
    networks = sorted(path.name for path in (ROOT / "networks").iterdir() if path.is_dir())
    bundles = sorted(path.name for path in (ROOT / "contracts").glob("contracts_*.json"))
    assert networks == ["local", "mainnet"]
    assert bundles == ["contracts_local.json", "contracts_mainnet.json"]


def test_only_the_dev_and_validator_templates_are_shipped():
    templates = sorted(path.stem for path in (ROOT / "templates").glob("*.json"))
    assert templates == ["single-node-dev", "validator"]


def test_the_validator_template_exposes_nothing_beyond_the_node():
    template = json.loads((ROOT / "templates" / "validator.json").read_text())
    assert template["operator_profile"] == "shared_network"
    services = template["services"]
    assert services["bds"] == {"enabled": False}
    assert services["dashboard"] == {"enabled": False}
    assert services["monitoring"] == {"enabled": True}
    assert "host" not in json.dumps(services)
