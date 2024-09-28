import sys
import os
import time
import random
from datetime import datetime, timedelta
from typing import Dict
from config.settings import settings
from utils.logging_config import logger
from strategy.evaluation import parse_backtest_results, fitness_function
from strategy.gen_template import generate_dynamic_template
from string import Template

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def render_strategy(params: list, strategy_name: str) -> str:
    # Generate the dynamic template
    template_content, template_params = generate_dynamic_template(settings.base_strategy_file)
    
    # Create a Template object
    strategy_template = Template(template_content)

    # Create a dictionary for the strategy parameters
    strategy_params = {'strategy_name': strategy_name}
    # print(params)
    # print(template_params)
    
    # Map the input params to the template params
    for i, param_info in enumerate(template_params[:-1]):
        param_name = param_info['name']
        if param_info['optimize']:
            if i < len(params):
                if param_info['type'] == 'Decimal':
                    strategy_params[param_name] = round(float(params[i]), param_info['decimal_places'])
                elif param_info['type'] == 'Int':
                    strategy_params[param_name] = int(params[i])
                else:
                    strategy_params[param_name] = params[i]
            else:
                logger.warning(f"Not enough parameters provided. Skipping {param_name}")

    # Render the strategy using the template
    rendered_strategy = strategy_template.substitute(strategy_params)
    
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
    
    max_open_trades = int(params[-1])

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
            f"--max-open-trades {max_open_trades} "
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
    
    return fitness_function(parsed_result, generation, strategy_name)  # 添加 strategy_name 参数

if __name__ == "__main__":
    # 测试 render_strategy 函数
    test_params = [30.5, 70, 0.05]
    test_strategy_name = "TestStrategy"
    
    rendered_strategy = render_strategy(test_params, test_strategy_name)
    
    print("Rendered Strategy:")
    print(rendered_strategy)
    
    # 可以添加一些简单的断言来检查结果
    assert test_strategy_name in rendered_strategy, "Strategy name not found in rendered strategy"
    assert "30.5" in rendered_strategy, "First parameter not found in rendered strategy"
    assert "70" in rendered_strategy, "Second parameter not found in rendered strategy"
    assert "0.05" in rendered_strategy, "Third parameter not found in rendered strategy"
    
    print("All assertions passed. Test successful!")
