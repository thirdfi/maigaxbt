from __future__ import annotations
import asyncio
from datetime import time
from typing import Optional

from api.config.application import BASE_CHAIN_ID, OPBNB_PROVIDER_RPC_URL, OPBNB_USDT_TOKEN_ADDRESS, XP_TOKEN_CONTRACT_ADDRESS, XP_OWNER_ADDRESS, XP_OWNER_PRIVATE_KEY
from api.wallet.mpc_service import retrieve_private_key
from api.user.models import UserProfile, Wallet
from bot.quries import record_transaction
import logging
from asgiref.sync import sync_to_async
from web3 import Web3
from eth_account import Account
from django.core.exceptions import ObjectDoesNotExist

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

WEB3_PROVIDER = Web3(Web3.HTTPProvider(OPBNB_PROVIDER_RPC_URL))

XP_TOKEN_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

XP_CONTRACT = WEB3_PROVIDER.eth.contract(
    address=Web3.to_checksum_address(XP_TOKEN_CONTRACT_ADDRESS), 
    abi=XP_TOKEN_ABI
)

async def mint_xp_token(wallet_address: str | None, user: UserProfile, amount: float) -> tuple[str, str]:
    try:
        if wallet_address is None:
            wallet = await sync_to_async(Wallet.objects.get)(user=user)
            wallet_address = wallet.wallet_address
        else:
            wallet = await sync_to_async(Wallet.objects.get)(wallet_address=wallet_address)
    except ObjectDoesNotExist:
        logging.error(f"[MINT ERROR] ❌ Wallet not found for user: {user}")
        return None


    try:
        owner_account = Account.from_key(XP_OWNER_PRIVATE_KEY)
        nonce = WEB3_PROVIDER.eth.get_transaction_count(owner_account.address, 'pending')

        tx = XP_CONTRACT.functions.mint(
            wallet_address,
            Web3.to_wei(amount, "ether")
        ).build_transaction({
            "chainId": int(BASE_CHAIN_ID),
            "gas": 200000,
            "gasPrice": WEB3_PROVIDER.eth.gas_price,
            "nonce": nonce,
        })

        signed_tx = owner_account.sign_transaction(tx)

        tx_hash_hex = None
        retry_count = 0
        status = "failed"

        # for attempt in range(1 + 3):
        #     try:
        #         tx_hash = WEB3_PROVIDER.eth.send_raw_transaction(signed_tx.rawTransaction)
        #         tx_hash_hex = tx_hash.hex()
        #         status = "pending"
        #         break
        #     except Exception as e:
        #         logging.warning(f"[MINT RETRY-{attempt}] Failed to send tx: {e}")
        #         retry_count += 1
        #         await asyncio.sleep(1)

        try:
            tx_hash = WEB3_PROVIDER.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            status = "pending"
        except Exception as e:
            logging.error(f"[MINT ERROR] Failed to send tx: {e}")
            tx_hash_hex = None
            status = "failed"
        
        try:
            receipt = WEB3_PROVIDER.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            status = "success" if receipt.status == 1 else "failed"
            logging.info(f"[MINT CONFIRMED] TX Receipt Status: {receipt.status} | TX: {tx_hash_hex}")
        except Exception as e:
            logging.error(f"[MINT ERROR] Failed to get transaction receipt: {e}")
            status = "unknown"

        await record_transaction(
            wallet=wallet,
            tx_hash=tx_hash_hex,
            user=user,
            amount=amount,
            token="XP",
            chain_id=int(BASE_CHAIN_ID),
            retry_count=retry_count,
            status=status
        )

        logging.info(f"[MINT SUCCESS] {amount} XP to {user} | TX: {tx_hash_hex}")
        return tx_hash_hex

    except Exception as e:
        logging.error(f"[MINT FAILED] Unexpected error while minting for {user}: {e}")
        return None
    