import asyncio
from hashlib import sha256
import os
from pathlib import Path
import urllib.request

from aries_askar.key import Key
from aries_askar.types import KeyAlg
import base58
from httpx import AsyncClient
from indy_vdr import open_pool
import pytest

def get_script_dir():
    return Path(os.path.dirname(os.path.realpath(__file__)))


@pytest.fixture(scope="session")
def downloaded_genesis():
    target_local_path = get_script_dir() / "genesis.txn"
    if target_local_path.exists():
        return target_local_path

    genesis_file_url = (
        "http://localhost:9000/genesis"
    )
    urllib.request.urlretrieve(genesis_file_url, target_local_path)
    return target_local_path


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()


@pytest.fixture(scope="session")
async def pool(downloaded_genesis: Path):
    yield await open_pool(transactions_path=str(downloaded_genesis))


@pytest.fixture(scope="session")
def did_gen():
    def _did_get():
        key = Key.generate(KeyAlg.ED25519)
        did = base58.b58encode(sha256(key.get_public_bytes()).digest()[:16]).decode()
        verkey = base58.b58encode(key.get_public_bytes()).decode()
        sigkey = base58.b58encode(key.get_secret_bytes()).decode()

        return key, did, verkey, sigkey

    yield _did_get


@pytest.fixture(scope="session")
async def endorser(did_gen):
    key, did, verkey, sigkey = did_gen()
    async with AsyncClient() as client:
        response = await client.post(
            "http://localhost:9000/register",
            json={
                "did": did,
                "role": "ENDORSER",
                "verkey": verkey,
            }
        )
        assert response.status_code == 200

    yield key, did, verkey, sigkey


@pytest.fixture(scope="session")
async def steward(did_gen):
    key, did, verkey, sigkey = did_gen()
    async with AsyncClient() as client:
        response = await client.post(
            "http://localhost:9000/register",
            json={
                "did": did,
                "role": "STEWARD",
                "verkey": verkey,
            }
        )
        assert response.status_code == 200

    yield key, did, verkey, sigkey
