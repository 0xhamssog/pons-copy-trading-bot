from __future__ import annotations

from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider

from bot.config import env
from bot.rpc import FailoverHTTPProvider, mask_rpc, resolve_rpc

ROBINHOOD_CHAIN_ID = 4663
EXPLORER = "https://robinhoodchain.blockscout.com"
PONS_SITE = "https://www.ponsfamily.com"
ZERO = "0x0000000000000000000000000000000000000000"

ADDR = {
    "weth": Web3.to_checksum_address("0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73"),
    "v1Factory": Web3.to_checksum_address("0xA5aAb3F0c6EeadF30Ef1D3Eb997108E976351feB"),
    "v1FactoryLegacy": Web3.to_checksum_address("0x0c37a24F5D23A486FA692d1500881d698B1F77a4"),
    "v1Locker": Web3.to_checksum_address("0x736D76699C26D0d966744cAe304C000d471f7F35"),
    "v3Factory": Web3.to_checksum_address("0x1f7d7550B1b028f7571E69A784071F0205FD2EfA"),
    "swapRouter02": Web3.to_checksum_address("0xCaf681a66D020601342297493863E78C959E5cb2"),
    "quoterV2": Web3.to_checksum_address("0x33e885eD0Ec9bF04EcfB19341582aADCb4c8A9E7"),
    "v2Factory": Web3.to_checksum_address("0x7eD598BcEf8bd9Edd8C97A195C6d13f40801EC7e"),
    "ponsToken": Web3.to_checksum_address("0x39dBED3a2bd333467115dE45665cC57F813C4571"),
    "ponsPool": Web3.to_checksum_address("0x10CC6BD38112cAc182db90B6a71d8Bb5939526bA"),
}

FACTORY_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "getLaunchedToken",
        "stateMutability": "view",
        "inputs": [{"name": "token", "type": "address"}],
        "outputs": [
            {
                "name": "launched",
                "type": "tuple",
                "components": [
                    {"name": "token", "type": "address"},
                    {"name": "deployer", "type": "address"},
                    {"name": "pairedToken", "type": "address"},
                    {"name": "positionManager", "type": "address"},
                    {"name": "positionId", "type": "uint256"},
                    {"name": "dexId", "type": "uint256"},
                    {"name": "launchConfigId", "type": "uint256"},
                    {"name": "restrictionsEndBlock", "type": "uint256"},
                    {"name": "supply", "type": "uint256"},
                    {"name": "isToken0", "type": "bool"},
                    {"name": "poolFee", "type": "uint24"},
                    {"name": "exists", "type": "bool"},
                    {"name": "initialBuyAmount", "type": "uint256"},
                ],
            }
        ],
    }
]

V2_FACTORY_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "getLaunchedToken",
        "stateMutability": "view",
        "inputs": [{"name": "token", "type": "address"}],
        "outputs": [
            {
                "name": "",
                "type": "tuple",
                "components": [
                    {"name": "token", "type": "address"},
                    {"name": "curve", "type": "address"},
                    {"name": "deployer", "type": "address"},
                    {"name": "creatorFeeRecipient", "type": "address"},
                    {"name": "pairToken", "type": "address"},
                    {"name": "graduationThreshold", "type": "uint256"},
                    {"name": "poolFee", "type": "uint24"},
                    {"name": "tickSpacing", "type": "int24"},
                    {"name": "creatorTaxBps", "type": "uint16"},
                    {"name": "buybackEnabled", "type": "bool"},
                    {"name": "phase", "type": "uint8"},
                    {"name": "sweptQuote", "type": "uint256"},
                    {"name": "sweptTokens", "type": "uint256"},
                    {"name": "sweptAt", "type": "uint256"},
                    {"name": "exists", "type": "bool"},
                ],
            }
        ],
    }
]

TOKEN_ABI: list[dict[str, Any]] = [
    {"type": "function", "name": "name", "stateMutability": "view", "inputs": [], "outputs": [{"type": "string"}]},
    {"type": "function", "name": "symbol", "stateMutability": "view", "inputs": [], "outputs": [{"type": "string"}]},
    {"type": "function", "name": "decimals", "stateMutability": "view", "inputs": [], "outputs": [{"type": "uint8"}]},
    {
        "type": "function",
        "name": "balanceOf",
        "stateMutability": "view",
        "inputs": [{"type": "address"}],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "allowance",
        "stateMutability": "view",
        "inputs": [{"type": "address"}, {"type": "address"}],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "approve",
        "stateMutability": "nonpayable",
        "inputs": [{"type": "address"}, {"type": "uint256"}],
        "outputs": [{"type": "bool"}],
    },
    {
        "type": "function",
        "name": "liquidityPool",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "address"}],
    },
]

POOL_ABI: list[dict[str, Any]] = [
    {"type": "function", "name": "token0", "stateMutability": "view", "inputs": [], "outputs": [{"type": "address"}]},
    {"type": "function", "name": "token1", "stateMutability": "view", "inputs": [], "outputs": [{"type": "address"}]},
    {"type": "function", "name": "fee", "stateMutability": "view", "inputs": [], "outputs": [{"type": "uint24"}]},
    {
        "type": "function",
        "name": "slot0",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [
            {"name": "sqrtPriceX96", "type": "uint160"},
            {"name": "tick", "type": "int24"},
            {"name": "observationIndex", "type": "uint16"},
            {"name": "observationCardinality", "type": "uint16"},
            {"name": "observationCardinalityNext", "type": "uint16"},
            {"name": "feeProtocol", "type": "uint8"},
            {"name": "unlocked", "type": "bool"},
        ],
    },
    {
        "type": "function",
        "name": "liquidity",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "uint128"}],
    },
    {
        "type": "event",
        "name": "Swap",
        "anonymous": False,
        "inputs": [
            {"name": "sender", "type": "address", "indexed": True},
            {"name": "recipient", "type": "address", "indexed": True},
            {"name": "amount0", "type": "int256", "indexed": False},
            {"name": "amount1", "type": "int256", "indexed": False},
            {"name": "sqrtPriceX96", "type": "uint160", "indexed": False},
            {"name": "liquidity", "type": "uint128", "indexed": False},
            {"name": "tick", "type": "int24", "indexed": False},
        ],
    },
]

WETH_ABI: list[dict[str, Any]] = [
    {"type": "function", "name": "deposit", "stateMutability": "payable", "inputs": [], "outputs": []},
    {
        "type": "function",
        "name": "withdraw",
        "stateMutability": "nonpayable",
        "inputs": [{"type": "uint256"}],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "balanceOf",
        "stateMutability": "view",
        "inputs": [{"type": "address"}],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "approve",
        "stateMutability": "nonpayable",
        "inputs": [{"type": "address"}, {"type": "uint256"}],
        "outputs": [{"type": "bool"}],
    },
    {
        "type": "function",
        "name": "allowance",
        "stateMutability": "view",
        "inputs": [{"type": "address"}, {"type": "address"}],
        "outputs": [{"type": "uint256"}],
    },
]

ROUTER_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "exactInputSingle",
        "stateMutability": "payable",
        "inputs": [
            {
                "name": "params",
                "type": "tuple",
                "components": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "recipient", "type": "address"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMinimum", "type": "uint256"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
            }
        ],
        "outputs": [{"name": "amountOut", "type": "uint256"}],
    }
]

QUOTER_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "quoteExactInputSingle",
        "stateMutability": "nonpayable",
        "inputs": [
            {
                "name": "params",
                "type": "tuple",
                "components": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
            }
        ],
        "outputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "sqrtPriceX96After", "type": "uint160"},
            {"name": "initializedTicksCrossed", "type": "uint32"},
            {"name": "gasEstimate", "type": "uint256"},
        ],
    }
]

CURVE_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "buy",
        "stateMutability": "payable",
        "inputs": [
            {"name": "quoteIn", "type": "uint256"},
            {"name": "minTokensOut", "type": "uint256"},
            {"name": "recipient", "type": "address"},
        ],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "sell",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "tokensIn", "type": "uint256"},
            {"name": "minQuoteOut", "type": "uint256"},
            {"name": "recipient", "type": "address"},
        ],
        "outputs": [{"type": "uint256"}],
    },
    {"type": "function", "name": "token", "stateMutability": "view", "inputs": [], "outputs": [{"type": "address"}]},
    {
        "type": "function",
        "name": "isNativeQuote",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "bool"}],
    },
    {
        "type": "function",
        "name": "pairToken",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "address"}],
    },
    {"type": "function", "name": "feeBps", "stateMutability": "view", "inputs": [], "outputs": [{"type": "uint256"}]},
    {
        "type": "function",
        "name": "creatorTaxBps",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "uint256"}],
    },
    {
        "type": "function",
        "name": "getReserves",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [
            {"name": "quoteReserve", "type": "uint256"},
            {"name": "tokenReserve", "type": "uint256"},
        ],
    },
    {
        "type": "function",
        "name": "graduated",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "bool"}],
    },
    {
        "type": "event",
        "name": "CurveBuy",
        "anonymous": False,
        "inputs": [
            {"name": "buyer", "type": "address", "indexed": True},
            {"name": "recipient", "type": "address", "indexed": True},
            {"name": "quoteIn", "type": "uint256", "indexed": False},
            {"name": "tokensOut", "type": "uint256", "indexed": False},
            {"name": "fee", "type": "uint256", "indexed": False},
            {"name": "tax", "type": "uint256", "indexed": False},
        ],
    },
    {
        "type": "event",
        "name": "CurveSell",
        "anonymous": False,
        "inputs": [
            {"name": "seller", "type": "address", "indexed": True},
            {"name": "recipient", "type": "address", "indexed": True},
            {"name": "tokensIn", "type": "uint256", "indexed": False},
            {"name": "quoteOut", "type": "uint256", "indexed": False},
            {"name": "fee", "type": "uint256", "indexed": False},
            {"name": "tax", "type": "uint256", "indexed": False},
        ],
    },
]

V1_LAUNCH_ABI: list[dict[str, Any]] = [
    {
        "type": "event",
        "name": "TokenLaunched",
        "anonymous": False,
        "inputs": [
            {"name": "token", "type": "address", "indexed": True},
            {"name": "deployer", "type": "address", "indexed": True},
            {"name": "dexFactory", "type": "address", "indexed": True},
            {"name": "pairToken", "type": "address", "indexed": False},
            {"name": "pool", "type": "address", "indexed": False},
            {"name": "dexId", "type": "uint256", "indexed": False},
            {"name": "launchConfigId", "type": "uint256", "indexed": False},
            {"name": "positionId", "type": "uint256", "indexed": False},
            {"name": "restrictionsEndBlock", "type": "uint256", "indexed": False},
            {"name": "initialBuyAmount", "type": "uint256", "indexed": False},
        ],
    }
]

V2_LAUNCH_ABI: list[dict[str, Any]] = [
    {
        "type": "event",
        "name": "TokenLaunched",
        "anonymous": False,
        "inputs": [
            {"name": "token", "type": "address", "indexed": True},
            {"name": "curve", "type": "address", "indexed": True},
            {"name": "deployer", "type": "address", "indexed": True},
            {"name": "pairToken", "type": "address", "indexed": False},
            {"name": "launchConfigId", "type": "uint256", "indexed": False},
            {"name": "graduationThreshold", "type": "uint256", "indexed": False},
        ],
    }
]

SWAP_TOPIC = Web3.keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)")
CURVE_BUY_TOPIC = Web3.keccak(text="CurveBuy(address,address,uint256,uint256,uint256,uint256)")
CURVE_SELL_TOPIC = Web3.keccak(text="CurveSell(address,address,uint256,uint256,uint256,uint256)")
V1_LAUNCH_TOPIC = Web3.keccak(
    text="TokenLaunched(address,address,address,address,address,uint256,uint256,uint256,uint256,uint256)"
)
V2_LAUNCH_TOPIC = Web3.keccak(text="TokenLaunched(address,address,address,address,uint256,uint256)")


def checksum(value: str) -> str:
    return Web3.to_checksum_address(value)


def is_address(value: str) -> bool:
    return Web3.is_address(value)


def explorer_tx(tx_hash: str) -> str:
    return f"{EXPLORER}/tx/{tx_hash}"


def explorer_address(address: str) -> str:
    return f"{EXPLORER}/address/{address}"


def pons_token_url(token: str) -> str:
    return f"{PONS_SITE}/token/{token}"


RPC = resolve_rpc(
    rpc_url=env.rpc_url,
    paid_rpc_url=env.paid_rpc_url,
    alchemy_api_key=env.alchemy_api_key,
    ws_url=env.ws_url,
    send_rpc_url=env.send_rpc_url,
)


def _attach(w3: Web3) -> Web3:
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def create_web3() -> Web3:
    provider = FailoverHTTPProvider(RPC["read_urls"], timeout=env.rpc_timeout_s)
    return _attach(Web3(provider))


def create_send_web3() -> Web3 | None:
    write_url = str(RPC.get("write_url") or "")
    if not write_url:
        return None
    return _attach(Web3(HTTPProvider(write_url, request_kwargs={"timeout": env.rpc_timeout_s})))


def require_paid_rpc_for_live() -> None:
    if RPC["paid"]:
        return
    raise RuntimeError(
        "live trading needs a paid RPC. set ALCHEMY_API_KEY or PAID_RPC_URL "
        "(public rpc.mainnet.chain.robinhood.com is rate-limited)"
    )


def load_account() -> LocalAccount | None:
    if not env.private_key:
        return None
    return Account.from_key(env.private_key)
