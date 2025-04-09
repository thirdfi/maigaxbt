from __future__ import annotations

from api.config.application import MPC_SERVER_URL_1, MPC_SERVER_URL_2, MPC_SERVER_URL_3
from api.wallet.shamirs_secret_sharing_python import combine, split
from eth_account import Account
import httpx
import logging


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def create_wallet() -> str:
    acct = Account.create()
    private_key = acct.key  
    address = acct.address

    private_key_bytes = bytes(str(private_key), encoding="utf-8")  
    shares = split(private_key_bytes, {
        "shares": 3,
        "threshold": 2
    })

    urls = [MPC_SERVER_URL_1, MPC_SERVER_URL_2, MPC_SERVER_URL_3]
    async with httpx.AsyncClient() as client:
        for i, url in enumerate(urls):
            try:
                await client.post(
                    f"{url}/storeShare",
                    json={"walletAddress": address, "share": shares[i].hex()}
                )
            except Exception as e:
                print(f"[create_wallet] Error posting share to {url}: {e}")
                raise e

    return address


async def retrieve_private_key(wallet_address: str) -> str:
    urls = [MPC_SERVER_URL_1, MPC_SERVER_URL_2, MPC_SERVER_URL_3]
    shares = []

    async with httpx.AsyncClient() as client:
        for url in urls:
            try:
                res = await client.get(f"{url}/getShare", params={"walletAddress": wallet_address})
                data = res.json()
                share = data.get("share")
                if share and share != "not found":
                    shares.append(bytes.fromhex(share))  
            except Exception as e:
                print(f"[retrieve_private_key] Error fetching share from {url}: {e}")
                continue

    if len(shares) < 2:
        raise Exception("Not enough shares to recover private key")
    
    private_key_bytes = combine(shares)
    # private_key = private_key_bytes.decode("utf-8")  
    private_key = "0x" + private_key_bytes.hex()  
    return private_key


async def replace_wallet_shares(wallet_address: str):
    private_key = await retrieve_private_key(wallet_address)
    secret_bytes = bytes(private_key, encoding="utf-8")  

    shares = split(secret_bytes, {
        "shares": 3,
        "threshold": 2
    })

    urls = [MPC_SERVER_URL_1, MPC_SERVER_URL_2, MPC_SERVER_URL_3]
    async with httpx.AsyncClient() as client:
        for i, url in enumerate(urls):
            try:
                await client.post(
                    f"{url}/replaceShare",
                    json={
                        "walletAddress": wallet_address,
                        "share": shares[i].hex()  
                    }
                )
                logging.info(f"[replaceShares] Sent share to {url}: {shares[i].hex()}")
            except Exception as e:
                print(f"[replace_wallet_shares] Error replacing share on {url}: {e}")