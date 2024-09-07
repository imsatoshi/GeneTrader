import os
import time
import random
from datetime import datetime, timedelta
from typing import Dict
from config.settings import settings
from utils.logging_config import logger
from strategy.evaluation import parse_backtest_results, fitness_function
from strategy.template import strategy_template, strategy_params

def render_strategy(params: Dict[str, any], strategy_name: str) -> str:
    # Ensure strategy_params is a dictionary
    if isinstance(strategy_params, list):
        strategy_params_dict = {str(i): v for i, v in enumerate(strategy_params)}
    else:
        strategy_params_dict = strategy_params

    # Ensure params is a dictionary
    if isinstance(params, list):
        params_dict = {str(i): v for i, v in enumerate(params)}
    else:
        params_dict = params

    # Merge the default strategy_params with the provided params
    merged_params = {**strategy_params_dict, **params_dict}
    
    # Use the provided strategy_name instead of generating a new one
    merged_params['strategy_name'] = strategy_name
    
    # Render the strategy using the template
    return strategy_template.substitute(merged_params)

def run_backtest(params: Dict[str, any], generation: int) -> float:
    strategy_name = f"GeneTrader_gen{generation}_{int(time.time())}_{random.randint(1000, 9999)}"
    strategy_file = f"{settings.strategy_dir}/{strategy_name}.py"
    
    # Render new strategy file
    rendered_strategy = render_strategy(params, strategy_name)
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