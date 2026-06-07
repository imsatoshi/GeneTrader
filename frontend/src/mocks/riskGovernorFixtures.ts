export type RiskGovernorAdjustment = {
  fixture_id: string;
  original_leverage: number;
  adjusted_leverage: number;
  original_risk_per_trade: number;
  adjusted_risk_per_trade: number;
  cooldown_candles: number;
  actions: string[];
  warnings: string[];
};

export const riskGovernorAdjustments: RiskGovernorAdjustment[] = [
  {
    fixture_id: 'safe-default',
    original_leverage: 2.0,
    adjusted_leverage: 2.0,
    original_risk_per_trade: 0.012,
    adjusted_risk_per_trade: 0.012,
    cooldown_candles: 0,
    actions: ['no_adjustment'],
    warnings: [],
  },
  {
    fixture_id: 'high-leverage-review',
    original_leverage: 5.0,
    adjusted_leverage: 3.0,
    original_risk_per_trade: 0.018,
    adjusted_risk_per_trade: 0.016,
    cooldown_candles: 12,
    actions: ['leverage_clamped', 'risk_reduced'],
    warnings: ['leverage above owner review default'],
  },
  {
    fixture_id: 'loss-streak-cooldown',
    original_leverage: 3.0,
    adjusted_leverage: 2.0,
    original_risk_per_trade: 0.02,
    adjusted_risk_per_trade: 0.01,
    cooldown_candles: 36,
    actions: ['loss_streak_detected', 'risk_reduced', 'cooldown_applied'],
    warnings: ['loss streak exceeded cutoff'],
  },
];
