# 区块链持仓功能使用指南 / Blockchain Position Guide

## 概述 / Overview

该功能允许从区块链钱包直接获取实际持仓，而不是从本地 `position.jsonl` 文件读取。这对于实时交易和链上资产管理非常有用。

This feature allows fetching actual positions directly from a blockchain wallet instead of reading from the local `position.jsonl` file. This is useful for real-time trading and on-chain asset management.

## 环境变量配置 / Environment Variables

### 必需的环境变量 / Required Variables

1. **启用区块链模式 / Enable Blockchain Mode:**
   ```bash
   export USE_BLOCKCHAIN_POSITION=true
   ```

2. **Arbitrum 钱包地址 / Arbitrum Wallet Address:**
   ```bash
   export ARB_WALLET_ADDRESS=0x1234567890abcdef1234567890abcdef12345678
   ```

3. **Arbitrum 私钥 / Arbitrum Private Key (用于交易 / for trading):**
   ```bash
   export ARB_PRIVATE_KEY=0xYourPrivateKeyHere
   ```

4. **Alchemy Arbitrum API 密钥 / Alchemy Arbitrum API Key:**
   ```bash
   export ALCHEMY_ARB_API_KEY=your_arbitrum_api_key
   ```

> **注意 / Note:** 此功能仅支持 Arbitrum 网络，因为大部分 dShare 股票代币都部署在 Arbitrum 上。
> This feature only supports Arbitrum network as most dShare stock tokens are deployed on Arbitrum.

> **安全提示 / Security Warning:** 私钥非常敏感，请妥善保管！切勿提交到版本控制系统。
> Private keys are highly sensitive, keep them secure! Never commit them to version control.

## 工作原理 / How It Works

1. **检查区块链模式 / Check Blockchain Mode:**
   - 检查 `USE_BLOCKCHAIN_POSITION` 环境变量
   - Checks `USE_BLOCKCHAIN_POSITION` environment variable
   - 如果未启用，直接使用文件模式
   - Falls back to file mode if not enabled

2. **设置区块链模式标识 / Set Blockchain Mode Indicator:**
   - 返回 `max_id = -1` 表示区块链模式
   - Returns `max_id = -1` to indicate blockchain mode
   - 不读取或维护 `position.jsonl` 文件
   - Does not read or maintain `position.jsonl` file
   - 交易操作（buy/sell）将检测此标识并跳过文件写入
   - Trade operations (buy/sell) will detect this and skip file writes

3. **获取代币余额 / Fetch Token Balances:**
   - 使用 Alchemy Portfolio API 获取 Arbitrum 钱包中所有代币
   - Uses Alchemy Portfolio API to fetch all tokens in Arbitrum wallet
   - 持仓数据完全来自链上，不使用文件中的持仓数据
   - Position data comes entirely from on-chain, file position data not used

4. **筛选股票代币和 USDC / Filter Stock Tokens and USDC:**
   - 扫描所有代币并检查是否在 `STOCK_ADDRESS` 中定义
   - Scans all tokens and checks if they are defined in `STOCK_ADDRESS`
   - 识别 USDC 代币 (0xaf88d065e77c8cC2239327C5EDb3A432268e5831) 作为 CASH 余额
   - Identifies USDC token (0xaf88d065e77c8cC2239327C5EDb3A432268e5831) as CASH balance
   - `STOCK_ADDRESS` 位于 `agent_tools/blockchain/constants.py`

5. **计算持仓 / Calculate Positions:**
   - 返回每个股票代币的实际持有数量
   - Returns the actual holding quantity for each stock token
   - CASH = USDC 代币余额（Native USDC on Arbitrum）
   - CASH = USDC token balance (Native USDC on Arbitrum)
   - 返回 `max_id = -1` (区块链模式标识)
   - Returns `max_id = -1` (blockchain mode indicator)

6. **交易操作适配 / Trade Operation Adaptation:**
   - `buy()` 和 `sell()` 函数检测区块链模式
   - `buy()` and `sell()` functions detect blockchain mode
   - 区块链模式下，使用 `send_token_with_memo()` 发送链上限价单
   - In blockchain mode, use `send_token_with_memo()` to send on-chain limit orders
   - 买入订单：发送 USDC 到订单簿合约，memo 包含请求的股票代币数量
   - Buy order: Send USDC to order book contract, memo contains requested stock token amount
   - 卖出订单：发送股票代币到订单簿合约，memo 包含请求的 USDC 数量
   - Sell order: Send stock tokens to order book contract, memo contains requested USDC amount
   - 跳过写入 `position.jsonl`，交易记录仅存在于链上
   - Skip writing to `position.jsonl`, trade records only exist on-chain
   - 交易仅在链上执行，无本地文件记录
   - Trades are executed on-chain only, no local file records

7. **回退机制 / Fallback Mechanism:**
   - 如果区块链获取失败，自动回退到文件模式
   - Automatically falls back to file-based mode if blockchain fetch fails
   - 文件模式会读取 `position.jsonl` 并返回实际的 max_id
   - File mode reads `position.jsonl` and returns actual max_id

## 支持的网络 / Supported Networks

- **Arbitrum** - 大多数 dShare 代币在此链上 / Most dShare tokens are on this chain

> 当前版本仅支持 Arbitrum 网络。如需其他网络支持，请提交 Issue。
> Current version only supports Arbitrum network. For other network support, please submit an Issue.

## 使用示例 / Usage Example

```python
from tools.price_tools import get_latest_position

# 获取最新持仓 / Get latest position
positions, max_id = get_latest_position("2025-11-11", "my_agent")

# 区块链模式输出示例 / Blockchain mode example output:
# positions = {
#     "AAPL": 10.5,      # 持有 10.5 个 AAPL 代币 (从链上获取)
#     "TSLA": 5.2,       # 持有 5.2 个 TSLA 代币 (从链上获取)
#     "CASH": 1000.50    # USDC 代币余额 (Native USDC on Arbitrum, 从链上获取)
# }
# max_id = -1          # 区块链模式标识，不维护 position.jsonl
```

## 配置文件设置 / Configuration File Setup

在 `.env` 文件中添加以下配置 / Add the following to your `.env` file:

```bash
# 启用区块链持仓模式 / Enable blockchain position mode
USE_BLOCKCHAIN_POSITION=true

# Arbitrum 配置 / Arbitrum configuration
ARB_WALLET_ADDRESS=0xYourWalletAddress
ARB_PRIVATE_KEY=0xYourPrivateKeyHere
ALCHEMY_ARB_API_KEY=your_alchemy_api_key
```

## 区块链交易 / Blockchain Trading

### 限价单机制 / Limit Order Mechanism

在区块链模式下，所有买入和卖出操作都通过发送代币到订单簿合约来执行，附带包含订单详情的 memo。

In blockchain mode, all buy and sell operations are executed by sending tokens to the order book contract with a memo containing order details.

**订单簿合约地址 / Order Book Contract Address:**
```
0x74a548ecdCa848654314402D9f8Fb19214A5008c
```

### Memo 格式 / Memo Format

```json
{
  "did_id": "<wallet_address>",
  "request": "<request_amount_wei>",
  "offer": "<offer_amount_wei>",
  "type": "LIMIT",
  "token_address": "<stock_token_address>",
  "customer_id": "SVIM",
  "expiry_days": 2
}
```

**字段说明 / Field Descriptions:**
- `did_id`: 钱包地址 / Wallet address
- `request`: 请求的代币数量（wei 单位）/ Requested token amount (in wei)
- `offer`: 提供的代币数量（wei 单位）/ Offered token amount (in wei)
- `type`: 订单类型（固定为 "LIMIT"）/ Order type (fixed as "LIMIT")
- `token_address`: 股票代币合约地址 / Stock token contract address
- `customer_id`: 客户标识（固定为 "SVIM"）/ Customer ID (fixed as "SVIM")
- `expiry_days`: 订单有效期（天数，默认 2 天）/ Order expiry (in days, default 2 days)

### 买入订单 / Buy Order

买入时，发送 USDC 到订单簿合约：

When buying, send USDC to the order book contract:

```python
# Example: Buy 10 shares of AAPL at $150 per share
# Total cost: 10 * 150 = 1500 USDC
# Order expires in 2 days (default)

memo = {
    "did_id": "0xYourWalletAddress",
    "request": "10000000000000000000",  # 10 tokens in wei (18 decimals)
    "offer": "1500000000",               # 1500 USDC in wei (6 decimals)
    "type": "LIMIT",
    "token_address": "0xAAPL_token_address",
    "customer_id": "SVIM",
    "expiry_days": 2
}

# Send 1500 USDC with this memo to order book contract
# To use a different expiry: buy("AAPL", 10, expiry_days=3)
```

### 卖出订单 / Sell Order

卖出时，发送股票代币到订单簿合约：

When selling, send stock tokens to the order book contract:

```python
# Example: Sell 10 shares of AAPL at $150 per share
# Expected return: 10 * 150 = 1500 USDC
# Order expires in 2 days (default)

memo = {
    "did_id": "0xYourWalletAddress",
    "request": "1500000000",              # 1500 USDC in wei (6 decimals)
    "offer": "10000000000000000000",      # 10 tokens in wei (18 decimals)
    "type": "LIMIT",
    "token_address": "0xAAPL_token_address",
    "customer_id": "SVIM",
    "expiry_days": 2
}

# Send 10 AAPL tokens with this memo to order book contract
# To use a different expiry: sell("AAPL", 10, expiry_days=3)
```

## 注意事项 / Notes

1. **CASH 余额 / CASH Balance:**
   - CASH 余额从 USDC (Native USDC on Arbitrum) 代币余额获取
   - CASH balance is fetched from USDC (Native USDC on Arbitrum) token balance
   - USDC 合约地址: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
   - USDC contract address: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
   - 如钱包中没有 USDC，CASH 将为 0
   - If no USDC in wallet, CASH will be 0

2. **私钥安全 / Private Key Security:**
   - 私钥用于签名区块链交易，请务必妥善保管
   - Private keys are used to sign blockchain transactions, keep them secure
   - 切勿将私钥提交到版本控制系统（如 Git）
   - Never commit private keys to version control systems (like Git)
   - 建议使用 `.env` 文件存储私钥，并添加 `.env` 到 `.gitignore`
   - Recommended to store private keys in `.env` file and add `.env` to `.gitignore`
   - 私钥泄露可能导致资金损失
   - Leaked private keys can lead to fund loss

3. **position.jsonl 不维护 / position.jsonl Not Maintained:**
   - 区块链模式下不创建或更新 `position.jsonl` 文件
   - `position.jsonl` file is not created or updated in blockchain mode
   - 所有持仓数据来自链上，无本地文件记录
   - All position data comes from on-chain, no local file records
   - 交易操作（buy/sell）自动检测并跳过文件写入
   - Trade operations (buy/sell) automatically detect and skip file writes
   - `max_id = -1` 作为区块链模式的标识
   - `max_id = -1` serves as blockchain mode indicator

3. **性能考虑 / Performance Considerations:**
   - Alchemy API 有速率限制，建议适当缓存
   - Alchemy API has rate limits, caching is recommended
   - 对于高频交易，考虑使用文件模式
   - For high-frequency trading, consider using file mode

4. **网络固定 / Fixed Network:**
   - 仅支持 Arbitrum 网络
   - Only Arbitrum network is supported
   - 大多数 dShare 股票代币都在 Arbitrum 上部署
   - Most dShare stock tokens are deployed on Arbitrum

## 故障排除 / Troubleshooting

### 问题：无法获取代币余额 / Issue: Cannot fetch token balances

**解决方案 / Solution:**
1. 检查 Alchemy Arbitrum API 密钥是否正确 / Check if Alchemy Arbitrum API key is correct
2. 确认钱包地址格式正确（0x开头） / Confirm wallet address format is correct (starts with 0x)
3. 确认代币在 Arbitrum 网络上 / Confirm tokens are on Arbitrum network
4. 查看控制台输出的调试信息 / Check debug output in console

### 问题：找不到股票代币 / Issue: Stock tokens not found

**解决方案 / Solution:**
1. 确认代币在 `constants.py` 的 `STOCK_ADDRESS` 中定义 / Confirm tokens are defined in `STOCK_ADDRESS` in `constants.py`
2. 检查代币地址是否匹配（大小写不敏感） / Check if token addresses match (case-insensitive)
3. 确认钱包中确实有这些代币余额 / Confirm wallet actually has these token balances

### 问题：自动回退到文件模式 / Issue: Automatically falls back to file mode

**可能原因 / Possible Reasons:**
1. `USE_BLOCKCHAIN_POSITION` 未设置为 true
2. `ARB_WALLET_ADDRESS` 环境变量未设置 / ARB_WALLET_ADDRESS environment variable not set
3. Alchemy Arbitrum API 调用失败 / Alchemy Arbitrum API call failed
4. 网络连接问题 / Network connection issues

## 开发和测试 / Development and Testing

### 测试区块链模式 / Test Blockchain Mode

```bash
# 设置测试环境变量 / Set test environment variables
export USE_BLOCKCHAIN_POSITION=true
export ARB_WALLET_ADDRESS=0xYourTestWalletAddress
export ALCHEMY_ARB_API_KEY=your_test_api_key

# 运行测试 / Run test
python -c "from tools.price_tools import get_latest_position; print(get_latest_position('2025-11-11', 'test'))"
```

### 日志和调试 / Logging and Debugging

代码使用 Python logging 模块记录详细信息：
The code uses Python logging module to record detailed information:

- **DEBUG 级别 / DEBUG Level**: 代币扫描详情、USDC 余额、每个股票代币的详细信息
- **DEBUG Level**: Token scanning details, USDC balance, detailed info for each stock token

- **INFO 级别 / INFO Level**: 持仓加载完成、股票代币数量、总价值、CASH 余额
- **INFO Level**: Position loading completed, stock token count, total value, CASH balance

- **WARNING 级别 / WARNING Level**: 配置缺失、API 调用失败等警告信息
- **WARNING Level**: Missing configuration, API call failures and other warnings

- **ERROR 级别 / ERROR Level**: 区块链获取失败等错误信息
- **ERROR Level**: Blockchain fetch failures and other errors

示例日志输出 / Example log output:
```
DEBUG - Blockchain mode: position.jsonl not used, max_id set to -1
DEBUG - Found 15 tokens in wallet
DEBUG - Found USDC token (0xaf88d065...), balance: 1000.500000 USDC (CASH)
DEBUG - Found stock token AAPL (0xCe38e140...), balance: 10.500000, price: $150.25, value: $1577.63
DEBUG - Found stock token TSLA (0x36d37B6c...), balance: 5.200000, price: $245.80, value: $1278.16
INFO - Loaded 3 positions from blockchain wallet 0x1234567890... on arbitrum
INFO -   Stock tokens: 2 positions, total value: $2855.79
INFO -   CASH (USDC): $1000.50
```

交易操作日志 / Trade Operation Logs:
```
# Buy operation in blockchain mode
Blockchain mode: Buy 5 shares of AAPL at $150.25
  New CASH: $249.25, New AAPL position: 15.5

# Sell operation in blockchain mode  
Blockchain mode: Sell 3 shares of TSLA at $245.80
  New CASH: $986.65, New TSLA position: 2.2
```

说明 / Explanation:
- max_id = -1 表示区块链模式，不维护 position.jsonl
- max_id = -1 indicates blockchain mode, position.jsonl not maintained
- 持仓数据完全来自链上（AAPL, TSLA, USDC）
- Position data comes entirely from on-chain (AAPL, TSLA, USDC)
- 交易操作不写入本地文件
- Trade operations don't write to local files

注意 / Note: 调试消息（DEBUG 级别）默认可能不会显示，需要配置 logging 级别为 DEBUG。
Debug messages (DEBUG level) may not be displayed by default, need to configure logging level to DEBUG.

## 相关文件 / Related Files

- `tools/price_tools.py` - 主要实现 / Main implementation
  - `get_latest_position()` - 从区块链获取持仓
  - `_get_latest_position_from_file()` - 文件模式回退

- `prompts/agent_prompt.py` - AI Agent 提示系统 / AI Agent prompt system
  - `get_agent_system_prompt()` - 自动检测区块链模式并获取持仓数据
  - Automatically detects blockchain mode and fetches position data
  - 在提示中显示数据来源（区块链钱包或本地文件）
  - Displays data source in prompt (blockchain wallet or local file)

- `agent_tools/tool_trade.py` - 交易操作实现 / Trade operation implementation
  - `buy(symbol, amount, expiry_days=2)` - 买入操作，区块链模式下发送链上限价单
  - `sell(symbol, amount, expiry_days=2)` - 卖出操作，区块链模式下发送链上限价单
  - 区块链模式下跳过 position.jsonl 文件写入
  - Skip position.jsonl file writes in blockchain mode

- `agent_tools/blockchain/alchemy.py` - Alchemy API 集成 / Alchemy API integration
  - `get_tokens_balance()` - 获取钱包代币余额

- `agent_tools/blockchain/constants.py` - 常量定义 / Constants definition
  - `STOCK_ADDRESS` - 所有支持的股票代币合约地址
  - `TRADING_ADDRESS` - 订单簿合约地址
  - `USDC_ADDRESSES` - USDC 代币地址（各链）

- `agent_tools/blockchain/evm.py` - EVM 客户端 / EVM client
  - `TOKEN_ADDRESSES` - 代币地址配置
  - `send_token_with_memo()` - 发送带 memo 的代币交易（用于限价单）
  - `ARBITRUM_CLIENT` - Arbitrum 网络客户端实例

## 贡献 / Contributing

如有问题或改进建议，请提交 Issue 或 Pull Request。
For issues or improvements, please submit an Issue or Pull Request.

