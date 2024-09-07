import os
import time
import random
from datetime import datetime, timedelta
from typing import Dict
from config.settings import settings
from utils.logging_config import logger
from strategy.evaluation import parse_backtest_results, fitness_function
from template import strategy_template, strategy_params

def render_strategy(params: Dict[str, any]) -> str:
    # Merge the default strategy_params with the provided params
    merged_params = {**strategy_params, **params}
    
    # Generate a unique strategy name
    merged_params['strategy_name'] = f"GeneTrader_{int(time.time())}_{random.randint(1000, 9999)}"
    
    # Render the strategy using the template
    return strategy_template.substitute(merged_params)

def run_backtest(params: Dict[str, any], generation: int) -> float:
    strategy_name = f"GeneTrader_gen{generation}_{int(time.time())}_{random.randint(1000, 9999)}"
    strategy_file = f"{settings.strategy_dir}/{strategy_name}.py"
    
    # Render new strategy file
    rendered_strategy = render_strategy(params)
    
    with open(strategy_file, 'w') as f:
        f.write(rendered_strategy)
    
    # Calculate the start_date for the timerange
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=18)
    timerange = f"{start_date.strftime('%Y%m%d')}-"

    output_file = f"{settings.results_dir}/backtest_results_gen{generation}_{int(time.time())}_{random.randint(1000, 9999)}.txt"
    
    for attempt in range(settings.max_retries):
        command = (
            f"{settings.freqtrade_path} backtesting "
            f"--strategy {strategy_name} "
            f"-c {settings.config_file} "
            f"--timerange {timerange} "
            f"-d {settings.data_dir} "
            f"--userdir {settings.user_dir} "
            f"> {output_file}"
        )
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