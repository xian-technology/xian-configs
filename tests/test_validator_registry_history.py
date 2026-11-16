"""Validator turnover must not impose a lifetime registration-size ceiling."""

import hashlib

import pytest
from test_validator_unbond_indexes import DELEGATOR, NODE, OTHER
from test_validator_unbond_indexes import chain as chain


def test_registration_still_works_after_two_thousand_retired_validators(chain):
    _, currency, validators = chain
    for index in range(2000):
        account = f"{index:064x}"
        currency.transfer(amount=1000, to=account, signer="founder")
        currency.approve(amount=1000, to="validators", signer=account)
        registered = validators.register(
            reward_key="founder",
            signer=account,
            metering=True,
            chi=200_000,
            return_full_output=True,
        )
        assert registered["status_code"] == 0, (index, registered["result"])
        validators.unregister(signer=account)
    assert validators.get_validator_count() == 2002
    assert validators.get_members() == [NODE, OTHER]


def test_historical_consensus_identity_lookup_survives_withdrawal(chain):
    client, currency, validators = chain
    currency.transfer(amount=1000, to=DELEGATOR, signer="founder")
    currency.approve(amount=1000, to="validators", signer=DELEGATOR)
    validators.register(signer=DELEGATOR)
    validators.unregister(signer=DELEGATOR)
    address = hashlib.sha256(bytes.fromhex(DELEGATOR)).hexdigest()[:40]
    assert client.raw_driver.get(f"validators.consensus_keys:{address}") == DELEGATOR


def test_history_pages_are_bounded_and_in_creation_order(chain):
    _, _, validators = chain
    first = validators.get_validators_page(limit=1)
    assert [record["account"] for record in first["validators"]] == [NODE]
    assert first["next_cursor"] == 1
    last = validators.get_validators_page(cursor=1, limit=1)
    assert [record["account"] for record in last["validators"]] == [OTHER]
    assert last["next_cursor"] is None
    with pytest.raises(AssertionError, match="page size"):
        validators.get_validators_page(limit=26)
    with pytest.raises(AssertionError, match="cursor"):
        validators.get_validators_page(cursor=3)
