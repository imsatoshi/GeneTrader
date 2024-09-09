import os
import time
import random
from datetime import datetime, timedelta
from typing import Dict
from config.settings import settings
from utils.logging_config import logger
from strategy.evaluation import parse_backtest_results, fitness_function
from strategy.template import strategy_template, strategy_params

def render_strategy(params: list, strategy_name: str) -> str:
    print(f"Input params: {params}")
    print(f"Input strategy_name: {strategy_name}")

    # Create a copy of strategy_params
    strategy_params_copy = strategy_params.copy()
    
    # Convert the params list to a dictionary using predefined keys
    param_keys = [
        'initial_entry_ratio', 'new_sl_coef', 'lookback_length', 'upper_trigger_level',
        'lower_trigger_level', 'buy_rsi', 'sell_rsi', 'atr_multiplier', 'swing_window',
        'swing_min_periods', 'swing_buffer', 'buy_macd', 'buy_ema_short', 'buy_ema_long',
        'sell_macd', 'sell_ema_short', 'sell_ema_long', 'volume_dca_int', 'a_vol_coef',
        'dca_candles_modulo', 'dca_threshold', 'dca_multiplier', 'max_dca_orders',
        'dca_profit_threshold'
    ]
    
    if len(params) != len(param_keys):
        raise ValueError(f"Expected {len(param_keys)} parameters, but got {len(params)}")
    
    params_dict = {}
    for key, value in zip(param_keys, params):
        if key == 'initial_entry_ratio':
            params_dict[key] = min(float(value), 0.99)  # Ensure it's always less than 1
        elif key in ['new_sl_coef', 'atr_multiplier', 'swing_buffer', 
                   'buy_macd', 'sell_macd', 'a_vol_coef', 'dca_threshold', 'dca_multiplier', 
                   'dca_profit_threshold']:
            params_dict[key] = float(value)  # Convert to float for Decimal values
        elif key in ['lookback_length', 'upper_trigger_level', 'lower_trigger_level', 'buy_rsi', 
                     'sell_rsi', 'swing_window', 'swing_min_periods', 'buy_ema_short', 'buy_ema_long', 
                     'sell_ema_short', 'sell_ema_long', 'volume_dca_int', 'dca_candles_modulo', 
                     'max_dca_orders']:
            params_dict[key] = int(value)  # Convert to int for Integer values
        else:
            params_dict[key] = value  # Keep as is for any other types
    
    print(f"Converted params_dict: {params_dict}")
    
    # Update the copy of strategy_params with the provided params
    strategy_params_copy.update(params_dict)
    
    # Add the strategy_name
    strategy_params_copy['strategy_name'] = strategy_name
    
    print(f"Final strategy_params: {strategy_params_copy}")
    
    # Render the strategy using the template
    rendered_strategy = strategy_template.substitute(strategy_params_copy)
    print(f"Rendered strategy (first 100 characters): {rendered_strategy[:100]}...")
    
    return rendered_strategy

def run_backtest(params: Dict[str, any], generation: int) -> float:
    timestamp = int(time.time())
    random_id = random.randint(1000, 9999)
    strategy_name = f"GeneTrader_gen{generation}_{timestamp}_{random_id}"
    strategy_file = f"{settings.strategy_dir}/{strategy_name}.py"
    
    # Render new strategy file
    rendered_strategy = render_strategy(params, strategy_name)
    with open(strategy_file, 'w') as f:
        f.write(rendered_strategy)
    
    # Calculate the start_date for the timerange
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=9)
    timerange = f"{start_date.strftime('%Y%m%d')}-"

    output_file = f"{settings.results_dir}/backtest_results_gen{generation}_{timestamp}_{random_id}.txt"
    
    for attempt in range(settings.max_retries):
        command = (
            f"{settings.freqtrade_path} backtesting "
            f"--strategy {strategy_name} "
            f"-c {os.path.abspath(settings.config_file)} "
            f"--timerange {timerange} "
            f"-d {os.path.abspath(settings.data_dir)} "
            f"--userdir {os.path.abspath(settings.user_dir)} "
            f"> {output_file}"
        )
        logger.info(f"Running command: {command}")
        out = os.system(command)
        
        if out == 0:
            logger.info(f"Backtesting successful for generation {generation}")
            break
        else:
            if attempt < settings.max_retries - 1:
                logger.warning(f"Backtesting failed for generation {generation}. Retrying in {settings.retry_delay} seconds...")
                time.sleep(settings.retry_delay)
    
    parsed_result = parse_backtest_results(output_file)
    
    if parsed_result['total_trades'] == 0:
        return float('-inf')  # Heavily penalize strategies that don't trade
    
    return fitness_function(parsed_result)