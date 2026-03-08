# Public.com API Reference - AI-Friendly Format

Base URL: https://api.public.com

## Authentication

### Generate Access Token
Method: POST
Endpoint: /userapiauthservice/personal/access-tokens
Headers: Content-Type: application/json
Request Body:
{
  "validityInMinutes": 123,
  "secret": "string"
}
Response:
{
  "accessToken": "string"
}

## Account Management

### List Accounts
Method: GET
Endpoint: /userapigateway/trading/account
Headers: Authorization: Bearer YOUR_API_KEY
Response:
{
  "accounts": [
    {
      "accountId": "string",
      "accountType": "BROKERAGE",
      "optionsLevel": "NONE",
      "brokerageAccountType": "CASH",
      "tradePermissions": "BUY_AND_SELL"
    }
  ]
}

### Get Account Portfolio
Method: GET
Endpoint: /userapigateway/trading/{accountId}/portfolio/v2
Headers: Authorization: Bearer YOUR_API_KEY
Response:
{
  "accountId": "string",
  "accountType": "BROKERAGE",
  "buyingPower": {
    "cashOnlyBuyingPower": "string",
    "buyingPower": "string",
    "optionsBuyingPower": "string"
  },
  "equity": [
    {
      "type": "CASH",
      "value": "string",
      "percentageOfPortfolio": "string"
    }
  ],
  "positions": [
    {
      "instrument": {
        "symbol": "string",
        "name": "string",
        "type": "EQUITY"
      },
      "quantity": "string",
      "openedAt": "2023-11-07T05:31:56Z",
      "currentValue": "string",
      "percentOfPortfolio": "string",
      "lastPrice": {
        "lastPrice": "string",
        "timestamp": "2023-11-07T05:31:56Z"
      },
      "instrumentGain": {
        "gainValue": "string",
        "gainPercentage": "string",
        "timestamp": "2023-11-07T05:31:56Z"
      },
      "positionDailyGain": {
        "gainValue": "string",
        "gainPercentage": "string",
        "timestamp": "2023-11-07T05:31:56Z"
      },
      "costBasis": {
        "totalCost": "string",
        "unitCost": "string",
        "gainValue": "string",
        "gainPercentage": "string",
        "lastUpdate": "2023-11-07T05:31:56Z"
      }
    }
  ],
  "orders": [
    {
      "orderId": "972989e5-6297-4b12-be87-fb850a3692c3",
      "instrument": {
        "symbol": "string",
        "type": "EQUITY"
      },
      "createdAt": "2023-11-07T05:31:56Z",
      "type": "MARKET",
      "side": "BUY",
      "status": "NEW",
      "quantity": "string",
      "notionalValue": "string",
      "expiration": {
        "timeInForce": "DAY",
        "expirationTime": "2023-11-07T05:31:56Z"
      },
      "limitPrice": "string",
      "stopPrice": "string",
      "closedAt": "2023-11-07T05:31:56Z",
      "openCloseIndicator": "OPEN",
      "filledQuantity": "string",
      "averagePrice": "string",
      "legs": [
        {
          "instrument": {
            "symbol": "string",
            "type": "EQUITY"
          },
          "side": "BUY",
          "openCloseIndicator": "OPEN",
          "ratioQuantity": 123
        }
      ]
    }
  ]
}

### Get Account History
Method: GET
Endpoint: /userapigateway/trading/{accountId}/history
Headers: Authorization: Bearer YOUR_API_KEY
Response:
{
  "transactions": [
    {
      "timestamp": "2023-11-07T05:31:56Z",
      "id": "string",
      "type": "TRADE",
      "subType": "DEPOSIT",
      "accountNumber": "string",
      "symbol": "string",
      "securityType": "EQUITY",
      "side": "BUY",
      "description": "string",
      "netAmount": "string",
      "principalAmount": "string",
      "quantity": "string",
      "direction": "INCOMING",
      "fees": "string"
    }
  ],
  "nextToken": "string",
  "start": "2023-11-07T05:31:56Z",
  "end": "2023-11-07T05:31:56Z",
  "pageSize": 123
}

## Instruments

### Get All Instruments
Method: GET
Endpoint: /userapigateway/trading/instruments
Headers: Authorization: Bearer YOUR_API_KEY
Response:
{
  "instruments": [
    {
      "instrument": {
        "symbol": "string",
        "type": "EQUITY"
      },
      "trading": "BUY_AND_SELL",
      "fractionalTrading": "BUY_AND_SELL",
      "optionTrading": "BUY_AND_SELL",
      "optionSpreadTrading": "BUY_AND_SELL"
    }
  ]
}

### Get Single Instrument
Method: GET
Endpoint: /userapigateway/trading/instruments/{symbol}/{type}
Headers: Authorization: Bearer YOUR_API_KEY
Response:
{
  "instrument": {
    "symbol": "string",
    "type": "EQUITY"
  },
  "trading": "BUY_AND_SELL",
  "fractionalTrading": "BUY_AND_SELL",
  "optionTrading": "BUY_AND_SELL",
  "optionSpreadTrading": "BUY_AND_SELL"
}

## Market Data

### Get Quotes
Method: POST
Endpoint: /userapigateway/marketdata/{accountId}/quotes
Headers: Authorization: Bearer YOUR_API_KEY, Content-Type: application/json
Request Body:
{
  "instruments": [
    {
      "symbol": "string",
      "type": "EQUITY"
    }
  ]
}
Response:
{
  "quotes": [
    {
      "instrument": {
        "symbol": "string",
        "type": "EQUITY"
      },
      "outcome": "SUCCESS",
      "last": "string",
      "lastTimestamp": "2023-11-07T05:31:56Z",
      "bid": "string",
      "bidSize": 123,
      "bidTimestamp": "2023-11-07T05:31:56Z",
      "ask": "string",
      "askSize": 123,
      "askTimestamp": "2023-11-07T05:31:56Z",
      "volume": 1234567890,
      "openInterest": 1234567890
    }
  ]
}

## Trading

### Get Preflight (Order Preview)
Method: POST
Endpoint: /userapigateway/trading/{accountId}/preflight/single-leg
Headers: Authorization: Bearer YOUR_API_KEY, Content-Type: application/json
Request Body:
{
  "instrument": {
    "symbol": "string",
    "type": "EQUITY"
  },
  "orderSide": "BUY",
  "orderType": "MARKET",
  "expiration": {
    "timeInForce": "DAY",
    "expirationTime": "2023-11-07T05:31:56Z"
  },
  "quantity": "string",
  "amount": "string",
  "limitPrice": "string",
  "stopPrice": "string",
  "openCloseIndicator": "OPEN"
}
Response:
{
  "instrument": {
    "symbol": "string",
    "type": "EQUITY"
  },
  "cusip": "string",
  "rootSymbol": "string",
  "rootOptionSymbol": "string",
  "estimatedCommission": "string",
  "regulatoryFees": {
    "secFee": "string",
    "tafFee": "string",
    "orfFee": "string",
    "exchangeFee": "string",
    "occFee": "string",
    "catFee": "string"
  },
  "estimatedIndexOptionFee": "string",
  "orderValue": "string",
  "estimatedQuantity": "string",
  "estimatedCost": "string",
  "buyingPowerRequirement": "string",
  "estimatedProceeds": "string",
  "optionDetails": {
    "baseSymbol": "string",
    "type": "CALL",
    "strikePrice": "string",
    "optionExpireDate": "2023-11-07"
  },
  "estimatedOrderRebate": {
    "estimatedOptionRebate": "string",
    "optionRebatePercent": 123,
    "perContractRebate": "string"
  },
  "marginRequirement": {
    "longMaintenanceRequirement": "string",
    "longInitialRequirement": "string"
  },
  "marginImpact": {
    "marginUsageImpact": "string",
    "initialMarginRequirement": "string"
  },
  "priceIncrement": {
    "incrementBelow3": "string",
    "incrementAbove3": "string",
    "currentIncrement": "string"
  }
}

### Place Order
Method: POST
Endpoint: /userapigateway/trading/{accountId}/order
Headers: Authorization: Bearer YOUR_API_KEY, Content-Type: application/json
Request Body:
{
  "orderId": "45b0ed05-840a-4bb0-a521-17251dc34931",
  "instrument": {
    "symbol": "string",
    "type": "EQUITY"
  },
  "orderSide": "BUY",
  "orderType": "LIMIT",
  "expiration": {
    "timeInForce": "GTD",
    "expirationTime": "2025-11-04T19:19:31.626Z"
  },
  "quantity": "string",
  "amount": "string",
  "limitPrice": "string",
  "stopPrice": "string",
  "openCloseIndicator": "OPEN"
}
Response:
{
  "orderId": "ed01ed25-2836-475e-bd45-a1abdbb73655"
}

### Get Order
Method: GET
Endpoint: /userapigateway/trading/{accountId}/order/{orderId}
Headers: Authorization: Bearer YOUR_API_KEY
Response:
{
  "orderId": "7af71ab6-1bc6-430f-9839-8968a7841e28",
  "instrument": {
    "symbol": "string",
    "type": "EQUITY"
  },
  "createdAt": "2023-11-07T05:31:56Z",
  "type": "MARKET",
  "side": "BUY",
  "status": "NEW",
  "quantity": "string",
  "notionalValue": "string",
  "expiration": {
    "timeInForce": "DAY",
    "expirationTime": "2023-11-07T05:31:56Z"
  },
  "limitPrice": "string",
  "stopPrice": "string",
  "closedAt": "2023-11-07T05:31:56Z",
  "openCloseIndicator": "OPEN",
  "filledQuantity": "string",
  "averagePrice": "string",
  "legs": [
    {
      "instrument": {
        "symbol": "string",
        "type": "EQUITY"
      },
      "side": "BUY",
      "openCloseIndicator": "OPEN",
      "ratioQuantity": 123
    }
  ]
}

### Cancel Order
Method: DELETE
Endpoint: /userapigateway/trading/{accountId}/order/{orderId}
Headers: Authorization: Bearer YOUR_API_KEY
Response: 200 - Empty Body

## Common Enums and Values

### Account Types
- BROKERAGE

### Options Levels
- NONE

### Brokerage Account Types
- CASH

### Trade Permissions
- BUY_AND_SELL

### Instrument Types
- EQUITY

### Order Types
- MARKET
- LIMIT

### Order Sides
- BUY
- SELL

### Order Status
- NEW
- FILLED
- CANCELLED
- REJECTED

### Time In Force
- DAY
- GTD (Good Till Date)
- GTC (Good Till Cancelled)

### Open/Close Indicators
- OPEN
- CLOSE

### Transaction Types
- TRADE
- DEPOSIT
- WITHDRAWAL

### Security Types
- EQUITY
- OPTION

### Direction
- INCOMING
- OUTGOING