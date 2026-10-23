from eth_abi import encode

from bot.chain import CURVE_BUY_TOPIC, CURVE_SELL_TOPIC, SWAP_TOPIC
from bot.decode import decode_target_trades, topic_matches


class FakeLaunches:
    def __init__(self, launch):
        self.launch = launch

    def resolve_pool(self, _addr):
        return self.launch if self.launch.get("version") == 1 else None

    def resolve_curve(self, _addr):
        return self.launch if self.launch.get("version") == 2 else None


V1 = {
    "version": 1,
    "token": "0x39dBED3a2bd333467115dE45665cC57F813C4571",
    "pool": "0x10CC6BD38112cAc182db90B6a71d8Bb5939526bA",
    "pairToken": "0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73",
    "factory": "0xA5aAb3F0c6EeadF30Ef1D3Eb997108E976351feB",
    "deployer": "0xB9F5f4Ea1AF1F5d3678470eb98e8FBdcadEb24b0",
    "isToken0": True,
    "poolFee": 10000,
    "symbol": "PONS",
    "name": "pons",
}

V2 = {
    "version": 2,
    "token": "0x1111111111111111111111111111111111111111",
    "curve": "0x2222222222222222222222222222222222222222",
    "pairToken": "0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73",
    "factory": "0x7eD598BcEf8bd9Edd8C97A195C6d13f40801EC7e",
    "deployer": "0xB9F5f4Ea1AF1F5d3678470eb98e8FBdcadEb24b0",
    "poolFee": 0,
    "symbol": "MEME",
    "name": "meme",
}


def _tx():
    return {
        "hash": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "from": "0xB9F5f4Ea1AF1F5d3678470eb98e8FBdcadEb24b0",
    }


def test_topic_matching_accepts_with_or_without_prefix() -> None:
    raw = SWAP_TOPIC.hex()
    assert topic_matches(raw, SWAP_TOPIC)
    assert topic_matches("0x" + raw.replace("0x", ""), SWAP_TOPIC)


def test_v1_swap_buy_when_pool_receives_weth() -> None:
    data = encode(["int256", "int256", "uint160", "uint128", "int24"], [-(10**18), 2 * 10**17, 0, 0, 0])
    receipt = {
        "blockNumber": 99,
        "logs": [
            {
                "address": V1["pool"],
                "topics": [SWAP_TOPIC],
                "data": data,
            }
        ],
    }
    found = decode_target_trades(tx=_tx(), receipt=receipt, launches=FakeLaunches(V1))
    assert len(found) == 1
    trade, launch = found[0]
    assert trade["side"] == "buy"
    assert trade["venue"] == "v1-pool"
    assert trade["quoteAmountWei"] == str(2 * 10**17)
    assert launch["symbol"] == "PONS"


def test_curve_buy_and_sell() -> None:
    buy_data = encode(["uint256", "uint256", "uint256", "uint256"], [10**17, 5000, 1, 0])
    sell_data = encode(["uint256", "uint256", "uint256", "uint256"], [4000, 8 * 10**16, 1, 0])
    receipt = {
        "blockNumber": 101,
        "logs": [
            {"address": V2["curve"], "topics": [CURVE_BUY_TOPIC], "data": buy_data},
            {"address": V2["curve"], "topics": [CURVE_SELL_TOPIC], "data": sell_data},
        ],
    }
    found = decode_target_trades(tx=_tx(), receipt=receipt, launches=FakeLaunches(V2))
    assert [row[0]["side"] for row in found] == ["buy", "sell"]
    assert found[0][0]["quoteAmountWei"] == str(10**17)
    assert found[1][0]["tokenAmount"] == "4000"


# Logs copied verbatim from Robinhood Chain mainnet (curve 0x060f0bbc98aee98f9b94c01b47d603f2ee98763f):
# CurveBuy in tx 0x3d9be7fd920dd4dbfdaebe97a3f19f683ae8699dbcf6151d5cbea7b3d421fd41 (block 95782246),
# CurveSell in tx 0x4d5750f93d30e7c5f8d94c134fd9bbbe805c3efb8d7dcfab537d951991a28fad (block 95764225).
ONCHAIN_CURVE_BUY = {
    "address": "0x060f0bbc98aee98f9b94c01b47d603f2ee98763f",
    "topics": [
        "0xec36bf571f136799e8dc0b0b8bea4b04d8bd3d43de838aab0d5fc21d4cbfc455",
        "0x000000000000000000000000510b7873e8a19fffcb194eeb212760bb03cf4e53",
        "0x000000000000000000000000510b7873e8a19fffcb194eeb212760bb03cf4e53",
    ],
    "data": "0x00000000000000000000000000000000000000000000000000056c801ea91302"
    "00000000000000000000000000000000000000000000b5cb3cc1fb086e44af46"
    "00000000000000000000000000000000000000000000000000000de28faaa697"
    "00000000000000000000000000000000000000000000000000001bc51f554d2e",
}
ONCHAIN_CURVE_SELL = {
    "address": "0x060f0bbc98aee98f9b94c01b47d603f2ee98763f",
    "topics": [
        "0x8113d738abdcb6b38357e9d53a54a7157861a09031b453651f0fe7fe151f59df",
        "0x000000000000000000000000b3ea566ce79eaf79b3448c3d5ec1c9449cb82832",
        "0x000000000000000000000000b3ea566ce79eaf79b3448c3d5ec1c9449cb82832",
    ],
    "data": "0x00000000000000000000000000000000000000000001d75e8131fe0533ce9a2d"
    "000000000000000000000000000000000000000000000000000d4023f61ab65d"
    "000000000000000000000000000000000000000000000000000022f874058dc1"
    "000000000000000000000000000000000000000000000000000045f0e80b1b83",
}


def test_decodes_real_v2_curve_logs() -> None:
    buy = decode_target_trades(
        tx=_tx(), receipt={"blockNumber": 95782246, "logs": [ONCHAIN_CURVE_BUY]}, launches=FakeLaunches(V2)
    )
    sell = decode_target_trades(
        tx=_tx(), receipt={"blockNumber": 95764225, "logs": [ONCHAIN_CURVE_SELL]}, launches=FakeLaunches(V2)
    )
    assert [row[0]["side"] for row in buy] == ["buy"]
    assert buy[0][0]["quoteAmountWei"] == str(0x56C801EA91302)
    assert buy[0][0]["tokenAmount"] == str(0xB5CB3CC1FB086E44AF46)
    assert [row[0]["side"] for row in sell] == ["sell"]
    assert sell[0][0]["tokenAmount"] == str(0x1D75E8131FE0533CE9A2D)
    assert sell[0][0]["quoteAmountWei"] == str(0xD4023F61AB65D)
