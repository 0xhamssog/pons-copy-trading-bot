from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from eth_abi import decode as abi_decode
from web3 import Web3

from bot.chain import CURVE_BUY_TOPIC, CURVE_SELL_TOPIC, SWAP_TOPIC, checksum
from bot.launches import LaunchIndex
from bot.types import DetectedTrade, LaunchRecord


def decode_target_trades(
    *,
    tx: dict[str, Any],
    receipt: dict[str, Any],
    launches: LaunchIndex,
) -> list[tuple[DetectedTrade, LaunchRecord]]:
    found: list[tuple[DetectedTrade, LaunchRecord]] = []
    seen: set[str] = set()
    tx_hash = _hex(tx.get("hash"))
    wallet = checksum(tx["from"])
    block_number = int(receipt["blockNumber"])

    for log_item in receipt.get("logs") or []:
        topics = [_hex(t) for t in (log_item.get("topics") or [])]
        if not topics:
            continue
        topic0 = topics[0]
        data = log_item.get("data") or b""
        address = checksum(log_item["address"])

        if topic_matches(topic0, SWAP_TOPIC):
            decoded = _decode_swap(data)
            if decoded is None:
                continue
            launch = launches.resolve_pool(address)
            if not launch or launch.get("version") != 1 or not launch.get("pool"):
                continue
            trade = _from_v1_swap(
                tx=tx_hash,
                wallet=wallet,
                block_number=block_number,
                launch=launch,
                amount0=decoded[0],
                amount1=decoded[1],
            )
            if not trade:
                continue
            key = f"{trade['sourceTx']}:{trade['token']}:{trade['side']}"
            if key in seen:
                continue
            seen.add(key)
            found.append((trade, launch))
            continue

        if topic_matches(topic0, CURVE_BUY_TOPIC):
            decoded = _decode_curve(data)
            if decoded is None:
                continue
            launch = launches.resolve_curve(address)
            if not launch:
                continue
            trade = _base_trade(
                tx=tx_hash,
                wallet=wallet,
                block_number=block_number,
                launch=launch,
                side="buy",
                quote_amount_wei=decoded[0],
                token_amount=decoded[1],
            )
            key = f"{trade['sourceTx']}:{trade['token']}:buy"
            if key in seen:
                continue
            seen.add(key)
            found.append((trade, launch))
            continue

        if topic_matches(topic0, CURVE_SELL_TOPIC):
            decoded = _decode_curve(data)
            if decoded is None:
                continue
            launch = launches.resolve_curve(address)
            if not launch:
                continue
            trade = _base_trade(
                tx=tx_hash,
                wallet=wallet,
                block_number=block_number,
                launch=launch,
                side="sell",
                quote_amount_wei=decoded[1],
                token_amount=decoded[0],
            )
            key = f"{trade['sourceTx']}:{trade['token']}:sell"
            if key in seen:
                continue
            seen.add(key)
            found.append((trade, launch))

    return found


def _hex(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return "0x" + value.hex()
    text = str(value)
    return text if text.startswith("0x") else "0x" + text


def _to_bytes(data: Any) -> bytes:
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    text = str(data)
    if text.startswith("0x"):
        text = text[2:]
    return bytes.fromhex(text or "00")


def _normalize_topic(value: bytes) -> str:
    hexed = value.hex()
    return hexed.lower() if hexed.startswith("0x") else f"0x{hexed}".lower()


def topic_matches(topic: str, expected: bytes) -> bool:
    return _hex(topic).lower() == _normalize_topic(expected)


def _decode_swap(data: Any) -> tuple[int, int] | None:
    try:
        amount0, amount1, *_ = abi_decode(
            ["int256", "int256", "uint160", "uint128", "int24"],
            _to_bytes(data),
        )
        return int(amount0), int(amount1)
    except Exception:
        return None


def _decode_curve(data: Any) -> tuple[int, int] | None:
    try:
        first, second, *_ = abi_decode(["uint256", "uint256", "uint256", "uint256"], _to_bytes(data))
        return int(first), int(second)
    except Exception:
        return None


def _from_v1_swap(
    *,
    tx: str,
    wallet: str,
    block_number: int,
    launch: LaunchRecord,
    amount0: int,
    amount1: int,
) -> DetectedTrade | None:
    token_is_0 = launch.get("isToken0")
    if token_is_0 is None:
        token_is_0 = launch["token"].lower() < launch["pairToken"].lower()
    pair_signed = amount1 if token_is_0 else amount0
    token_signed = amount0 if token_is_0 else amount1
    if pair_signed == 0:
        return None
    side = "buy" if pair_signed > 0 else "sell"
    return _base_trade(
        tx=tx,
        wallet=wallet,
        block_number=block_number,
        launch=launch,
        side=side,
        quote_amount_wei=abs(pair_signed),
        token_amount=abs(token_signed),
    )


def _base_trade(
    *,
    tx: str,
    wallet: str,
    block_number: int,
    launch: LaunchRecord,
    side: str,
    quote_amount_wei: int,
    token_amount: int,
) -> DetectedTrade:
    token = checksum(launch["token"])
    return {
        "id": f"{tx}:{token}:{side}",
        "sourceTx": tx,
        "sourceWallet": wallet,
        "blockNumber": str(block_number),
        "venue": "v1-pool" if launch.get("version") == 1 else "v2-curve",
        "side": side,  # type: ignore[typeddict-item]
        "token": token,
        "symbol": launch.get("symbol") or "???",
        "name": launch.get("name") or "unknown",
        "quoteAmountWei": str(quote_amount_wei),
        "tokenAmount": str(token_amount),
        "pool": launch.get("pool"),
        "curve": launch.get("curve"),
        "pairToken": launch.get("pairToken") or "",
        "isToken0": launch.get("isToken0"),
        "poolFee": int(launch.get("poolFee") or 10_000),
        "detectedAt": datetime.now(timezone.utc).isoformat(),
    }


def is_weth_pair(pair: str) -> bool:
    from bot.chain import ADDR

    return pair.lower() == ADDR["weth"].lower()
