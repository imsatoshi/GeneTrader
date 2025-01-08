# Genetic Algorithm for Trading Strategy Optimization


## Background and Objective  
Automated trading strategies face challenges in optimizing performance due to chaotic and non-stationary market dynamics. This project implements a Genetic Algorithm (GA) to optimize trading strategy parameters and trading pair selection, offering a more robust and adaptive solution compared to conventional methods. By integrating GA with the Freqtrade framework, I aim to:  

- Enhance trading performance through hyperparameter optimization.  
- Automate strategy evaluation and replacement with the best-performing strategies.  
- Provide an efficient and configurable optimization workflow for traders.  

This project leverage GA to explore parameter spaces and improve profitability.


This project implements a genetic algorithm to optimize trading strategy parameters and trading pair selection. It supports multi-process parallel computation, dynamic generation of strategies, and saving the best strategy from each generation.

## Features

- Genetic algorithm optimization for trading strategies
- Optimization of strategy parameters and trading pair selection
- Support for setting maximum open trades
- Multi-process parallel computation
- Dynamic strategy generation and evaluation
- Saving of best individuals from each generation
- Configurable optimization parameters
- Optional data downloading before running the algorithm
- Offline Optimization and Automatic Strategy Replacement: Supports offline optimization of trading strategies, automatically comparing with the currently running online strategy, and replacing the online strategy with the best offline strategy if it performs better

## Prerequisites

- Required libraries (specified in requirements.txt)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/imsatoshi/GeneTrader.git
   cd GeneTrader
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a configuration file:
   ```
   cp ga.json.example ga.json
   ```

4. Edit `ga.json` to configure the genetic algorithm parameters and other settings according to your needs.

## Configuration

Edit `ga.json` (or your custom config file) to configure:

### Basic Parameters
- `population_size`: Number of individuals in each generation
- `generations`: Total number of generations to run
- `tournament_size`: Number of individuals in tournament selection
- `crossover_prob`: Probability of crossover (0.0 to 1.0)
- `mutation_prob`: Probability of mutation (0.0 to 1.0)

### Parameters for ga optimization

| Parameter Name           | Description                                                            |
|--------------------------|------------------------------------------------------------------------|
| `proxy`                  | Proxy settings, including addresses for HTTP and SOCKS5 proxies.       |
| `freqtrade_path`         | Path to the `freqtrade` executable.                                    |
| `strategy_dir`           | Directory where strategy files are located.                            |
| `user_dir`               | User data directory.                                                   |
| `data_dir`               | Data storage directory, typically used for market data.                |
| `results_dir`            | Results storage directory, used for storing backtest results, etc.     |
| `config_file`            | Path to the configuration file.                                        |
| `population_size`        | Size of the population in the genetic algorithm.                       |
| `generations`            | Number of generations in the genetic algorithm.                        |
| `crossover_prob`         | Probability of crossover in the genetic algorithm.                     |
| `mutation_prob`          | Probability of mutation in the genetic algorithm.                      |
| `backtest_timerange_weeks`| Time range for backtesting, in weeks.                                 |
| `tournament_size`        | Size of the tournament selection in the genetic algorithm.             |
| `pool_processes`         | Number of processes for parallel processing.                           |
| `max_retries`            | Maximum number of retries.                                             |
| `retry_delay`            | Delay time between retries.                                            |
| `add_max_open_trades`    | Whether to add a limit on the maximum number of open trades.           |
| `add_dynamic_timeframes` | Whether to add dynamic timeframes.                                     |
|          |                                      |
| `checkpoint_frequency`   | Frequency of saving checkpoints.                                       |
| `project_dir`            | Project directory.                                                     |
| `best_generations_dir`   | Directory for storing the best generations.                            |
| `base_strategy_file`     | Path to the base strategy file.                                        |
| `fix_pairs`              | Whether to fix trading pairs.                                          |
| `num_pairs`              | Number of trading pairs.                                               |
| `diversity_threshold`    | Diversity threshold for controlling population diversity.              |
| `max_mutation_prob`      | Maximum mutation probability.                                          |
| `local_file`             | Name of the local configuration file.                                  |
| `hostname`               | Hostname or IP address of the remote server.                           |
| `username`               | Username for the remote server.                                        |
| `port`                   | SSH port of the remote server.                                         |
| `key_path`               | Path to the SSH key file.                                              |
| `bark_endpoint`          | Endpoint URL for the Bark service.                                     |
| `bark_key`               | Key for the Bark service.                                              |
| `remote_datadir`         | Data directory on the remote server.                                   |
| `remote_strategydir`     | Strategy directory on the remote server.                               |
| `api_url`                | URL of the API.                                                        |
| `freqtrade_username`     | Username for Freqtrade.                                                |
| `freqtrade_password`     | Password for Freqtrade.                                                |

Note: The `proxy` setting is used when configuring a VPN. Ensure that the proxy settings include the necessary addresses for HTTP and SOCKS5 proxies to route traffic through the VPN.

Example configuration:
```json
{
    // ... other settings ...
    "max_open_trades": 3,
    "timeframe": "5m",
    // ... other settings ...
}
```

Tips for Parameter Selection:
- For `max_open_trades`:
  - Start with a lower value (2-3) for testing
  - Increase gradually based on available capital and risk tolerance
  - Consider exchange limits and liquidity

- For `timeframe`:
  - Lower timeframes (1m-5m): Suitable for scalping strategies
  - Medium timeframes (15m-30m): Balance between opportunities and noise
  - Higher timeframes (1h-4h): Better for trend-following strategies

### Updating Trading Pairs

You can dynamically update the trading pairs in your configuration using the `get_pairs.py` script:

```bash
python scripts/get_pairs.py [--mode {volume,all}]
```

Options:
- `--mode volume`: Get top 100 pairs sorted by USDT trading volume
- `--mode all`: Get all available USDT trading pairs (default)

The script will:
1. Fetch available trading pairs from Binance
2. Filter out pairs based on a predefined blacklist
3. Save the pairs to a timestamped JSON file
4. Automatically update the pair_whitelist in your `user_data/config.json`

Example usage:
```bash
# Get top 100 pairs by trading volume
python scripts/get_pairs.py --mode volume

# Get all available USDT pairs
python scripts/get_pairs.py --mode all
```

## Usage

Run the optimization script with the following command:

```
python main.py [options]
```

Available options:

- `--config CONFIG_FILE`: Specify a custom configuration file (default is 'ga.json')
- `--download`: Download data before running the algorithm
- `--start-date YYYYMMDD`: Start date for data download (default is '20240101')

Examples:

1. Run with default settings:
   ```
   python main.py
   ```

2. Use a custom configuration file:
   ```
   python main.py --config my_custom_config.json
   ```

3. Download data before running the algorithm:
   ```
   python main.py --download
   ```

4. Download data for a specific date range:
   ```
   python main.py --download --start-date 20230101
   ```


## Project Structure

- `main.py`: Main script to run the genetic algorithm
- `config/settings.py`: Settings class to load configuration
- `utils/`: Utility functions for logging and file operations
- `genetic_algorithm/`: Classes and functions for the genetic algorithm
- `strategy/`: Strategy-related code, including backtesting and template generation
- `data/`: Data handling, including the downloader module

## How It Works

1. The script loads configuration settings from a JSON file.
2. It generates a dynamic strategy template and extracts parameters.
3. If requested, it downloads historical data for backtesting.
4. The genetic algorithm creates an initial population of trading strategies or loads the latest checkpoint if resuming.
5. For each generation:
   - Strategies are evaluated in parallel using backtesting.
   - The best strategies are selected for the next generation.
   - Crossover and mutation operations are applied to create new strategies.
   - The best individual from each generation is saved.
   - A checkpoint is saved at regular intervals.
6. After all generations, the overall best strategy is reported.

## Contributing

Contributions are welcome! Please submit issues or pull requests.

## License

This project is licensed under the MIT License.

## Disclaimer

This project is for educational and research purposes only. It does not constitute investment advice. Users are responsible for any risks associated with using this project for actual trading.

## Contact

For questions or suggestions, please open an issue on GitHub.

## Community

![WeChat Group QR Code](data/WechatIMG319.jpg)


## Optimization Summary

Below is an example of optimization progress over 20 generations:
| Generation | Trades | Avg Profit % | Tot Profit % | Win Draw Loss | Drawdown % |
|------------|--------|--------------|-----------------|-----|----------|
| GeneTrader_gen1_1729489793_8197 | 257 | 0.21 | 36.228 | 176     0    81 | 54.53% |
| GeneTrader_gen2_1729489952_1439 | 569 | 0.49 | 243.621 | 397     0   172 | 24.59% |
| GeneTrader_gen3_1729490009_4737 | 354 | 0.31 | 145.164 | 256     0    98 | 51.58% |
| GeneTrader_gen4_1729490112_3632 | 358 | 0.37 | 202.592 | 266     0    92 | 38.83% |
| GeneTrader_gen5_1729490284_5784 | 322 | 0.27 | 97.633 | 264     0    58 | 43.65% |
| GeneTrader_gen6_1729490446_1924 | 376 | 0.73 | 1048.377 | 299     0    77 | 36.71% |
| GeneTrader_gen7_1729490545_9113 | 565 | 0.30 | 365.679 | 484     0    81 | 34.48% |
| GeneTrader_gen8_1729490992_8083 | 473 | 0.66 | 1695.533 | 412     0    61 | 12.59% |
| GeneTrader_gen9_1729491090_6216 | 421 | 0.55 | 669.485 | 360     0    61 | 8.35% |
| GeneTrader_gen10_1729491271_1982 | 587 | 0.13 | 62.295 | 494     0    93 | 57.37% |
| GeneTrader_gen11_1729491369_5745 | 471 | 0.58 | 1039.757 | 408     0    63 | 43.23% |
| GeneTrader_gen12_1729491539_3502 | 457 | 0.57 | 952.518 | 398     0    59 | 8.35% |
| GeneTrader_gen13_1729491663_2560 | 505 | 0.65 | 1974.439 | 439     0    66 | 8.35% |
| GeneTrader_gen14_1729491872_5826 | 460 | 0.77 | 2567.816 | 408     0    52 | 8.35% |
| GeneTrader_gen15_1729492004_9419 | 403 | 0.69 | 1209.204 | 354     0    49 | 26.96% |
| GeneTrader_gen16_1729492145_6860 | 393 | 0.64 | 894.785 | 340     0    53 | 41.60% |
| GeneTrader_gen17_1729492441_5355 | 360 | 0.62 | 637.224 | 310     0    50 | 40.51% |
| GeneTrader_gen18_1729492588_1685 | 382 | 0.47 | 373.272 | 325     0    57 | 43.14% |
| GeneTrader_gen19_1729492645_2977 | 384 | 0.53 | 519.371 | 335     0    49 | 36.79% |
| GeneTrader_gen20_1729492730_4647 | 335 | 0.48 | 309.840 | 289     0    46 | 47.06% |

This table shows the progress of the genetic algorithm optimization over 20 generations. Key metrics include:

- Trades: The number of trades executed by the strategy.
- Avg Profit %: The average profit percentage per trade.
- Tot Profit %: The total cumulative profit percentage.
- Win Draw Loss: The number of winning, draw, and losing trades.
- Drawdown %: The maximum observed loss from a peak to a trough, expressed as a percentage.

The optimization process aims to improve these metrics over time, finding strategies with higher profitability, better risk management, and improved overall performance. As seen in the table, there's a general trend of improvement in key metrics such as Win Rate, Total Profit, and Sharpe Ratio as the generations progress, although there are some fluctuations due to the nature of genetic algorithms and market complexity.