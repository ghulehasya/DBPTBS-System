"""
DBPTBS - Local Blockchain Simulator
-------------------------------------
A minimal, educational blockchain: each block hashes the previous block's
hash plus its own transaction, and a tiny proof-of-work puzzle is solved
before a block is accepted. This is a pedagogical demonstration of
"pre-transaction security" (a transaction only ever enters the chain AFTER
DBPTBS approves it) - it is NOT a real distributed ledger, has no peer
network, and must never be presented as production blockchain
infrastructure.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from app.config import BLOCKCHAIN_DIFFICULTY_PREFIX


@dataclass
class Block:
    index: int
    timestamp: float
    previous_hash: str
    transaction: dict
    transaction_hash: str
    nonce: int = 0
    block_hash: str = ""

    def compute_hash(self) -> str:
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "transaction_hash": self.transaction_hash,
            "nonce": self.nonce,
        }
        encoded = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


def hash_transaction(transaction: dict) -> str:
    encoded = json.dumps(transaction, sort_keys=True, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


class Blockchain:
    def __init__(self, difficulty_prefix: str = BLOCKCHAIN_DIFFICULTY_PREFIX):
        self.difficulty_prefix = difficulty_prefix
        self.chain: List[Block] = [self._create_genesis_block()]

    def _create_genesis_block(self) -> Block:
        genesis_tx = {"type": "genesis", "note": "DBPTBS simulated chain genesis block"}
        block = Block(
            index=0,
            timestamp=time.time(),
            previous_hash="0" * 64,
            transaction=genesis_tx,
            transaction_hash=hash_transaction(genesis_tx),
        )
        block.block_hash = self._mine(block)
        return block

    def _mine(self, block: Block) -> str:
        block.nonce = 0
        h = block.compute_hash()
        while not h.startswith(self.difficulty_prefix):
            block.nonce += 1
            h = block.compute_hash()
        return h

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, transaction: dict, approved_by: str = "DBPTBS") -> Block:
        """Add a new block for an APPROVED transaction. Callers must never
        invoke this for a transaction that has not already cleared the risk
        engine (+ verification, if required) - DBPTBS enforces this at the
        API layer, not here, but every stored transaction is tagged with
        who approved it for auditability."""
        tx = dict(transaction)
        tx["approved_by"] = approved_by
        tx_hash = hash_transaction(tx)
        block = Block(
            index=self.last_block.index + 1,
            timestamp=time.time(),
            previous_hash=self.last_block.block_hash,
            transaction=tx,
            transaction_hash=tx_hash,
        )
        block.block_hash = self._mine(block)
        self.chain.append(block)
        return block

    def is_valid(self) -> tuple[bool, Optional[str]]:
        for i in range(1, len(self.chain)):
            current, previous = self.chain[i], self.chain[i - 1]
            if current.previous_hash != previous.block_hash:
                return False, f"Block {current.index} previous_hash does not match block {previous.index}'s hash."
            if current.block_hash != current.compute_hash():
                return False, f"Block {current.index} hash does not match its recomputed contents (tampering?)."
            if current.transaction_hash != hash_transaction(
                {k: v for k, v in current.transaction.items()}
            ):
                return False, f"Block {current.index} transaction hash mismatch."
            if not current.block_hash.startswith(self.difficulty_prefix):
                return False, f"Block {current.index} does not satisfy proof-of-work difficulty."
        return True, None

    def to_list(self) -> List[dict]:
        return [b.to_dict() for b in self.chain]
