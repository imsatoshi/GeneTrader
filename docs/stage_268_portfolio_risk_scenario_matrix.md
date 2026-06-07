# STAGE-268 Portfolio Risk Scenario Matrix

## Verdict

PASS / portfolio risk scenarios defined for mock-first review.

This matrix is for local simulation and owner review. It does not connect to an
exchange, real market data, real Freqtrade, deployment, rollback, or live
trading.

## Scenario Matrix

| Scenario | Pairs | Leverage | Risk Per Trade | Exposure | Expected Outcome | Owner Review Needed |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Single pair low risk | `BTC/USDT` | 1.0 | 0.005 | <= 0.10 | PASS, low warning level | no |
| Single pair high leverage | `BTC/USDT` | 3.0 | 0.02 | <= 0.30 | WARN, leverage/risk review required | yes |
| Multi pair balanced | `BTC/USDT`, `ETH/USDT`, `SOL/USDT` | 1.0-2.0 | <= 0.01 | <= 0.30 | PASS if pair exposure caps hold | yes |
| Multi pair correlated drawdown | `BTC/USDT`, `ETH/USDT`, `SOL/USDT` | 2.0-3.0 | <= 0.02 | 0.30-0.60 | WARN/FAIL depending drawdown and exposure | yes |
| Loss streak across multiple pairs | multiple | variable | variable | variable | Reduce risk, apply cooldown, consider pause | yes |
| Portfolio exposure breach | multiple | variable | variable | > configured cap | FAIL, reject or reduce exposure | yes |

## Metrics To Capture

- portfolio profit
- portfolio drawdown
- pair-level drawdown
- pair-level exposure
- total exposure
- leverage usage
- correlation penalty
- loss streak across pairs
- circuit breaker status
- recommended risk reduction

## Mock Acceptance Criteria

- Scenario outputs are JSON-safe.
- No real market data is required.
- No real account data is required.
- Portfolio exposure breach produces a clear violation.
- Correlated drawdown produces visible warning/failure status.
- Loss streak scenario produces risk reduction and cooldown recommendation.

## Safety Boundary

Real backtest remains BLOCKED. These scenarios are mock-first and local-only.
