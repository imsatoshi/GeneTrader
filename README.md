# Genetic Algorithm Optimization for Trading Strategies

This project uses genetic algorithms to optimize trading strategy parameters.

## Features

- Optimize trading strategy parameters using genetic algorithms
- Multi-process parallel computation support
- Dynamic generation and evaluation of strategies
- Save the best strategy from each generation
- Configurable optimization parameters

## Prerequisites

- Python 3.7+
- Required libraries (specified in requirements.txt)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

Edit `ga.json` (or your custom config file) to configure:

- Genetic algorithm parameters (population size, generations, tournament size)
- Mutation and crossover probabilities
- Parallel processing options
- File paths and directories

Ensure all necessary directories specified in the configuration file exist before running the script.

## Usage

Run the optimization script:

```
python main.py [--config CONFIG_FILE]
```

Use `--config` to specify a custom configuration file (default is 'ga.json').

## Project Structure

- `main.py`: Main script to run the genetic algorithm
- `config/settings.py`: Settings class to load configuration
- `utils/`: Utility functions for logging and file operations
- `genetic_algorithm/`: Classes and functions for the genetic algorithm
- `strategy/`: Strategy-related code, including backtesting

## Backtesting Results

Here are the results from our latest backtesting:

### Summary Metrics

| Metric | Value |
|--------|-------|
| Backtesting from | 2024-01-01 00:00:00 |
| Backtesting to | 2024-09-07 02:30:00 |
| Max open trades | 2 |
| Total/Daily Avg Trades | 372 / 1.49 |
| Starting balance | 60 USDT |
| Final balance | 615.421 USDT |
| Absolute profit | 555.421 USDT |
| Total profit % | 925.70% |
| CAGR % | 2892.89% |
| Sharpe | 24.29 |
| Profit factor | 1608.62 |
| Avg. daily profit % | 3.70% |
| Best Pair | OM/USDT 60.48% |
| Worst Pair | ENA/USDT 0.00% |
| Best trade | PEOPLE/USDT 5.00% |
| Worst trade | RUNE/USDT -0.11% |
| Win / Draw / Loss | 371 / 0 / 1 |
| Win% | 99.7% |

### Strategy Performance

| Strategy | Trades | Avg Profit % | Tot Profit USDT | Tot Profit % | Avg Duration | Win / Draw / Loss | Win% | Drawdown |
|----------|--------|--------------|-----------------|--------------|--------------|-------------------|------|----------|
| GeneTrader_gen2_20240907_174909_7870 | 372 | 1.28 | 555.421 | 925.7 | 1 day, 8:08:00 | 371 / 0 / 1 | 99.7 | 0.345 USDT (0.06%) |

These results demonstrate the effectiveness of our genetic algorithm in optimizing trading strategies.

## Contributing

Contributions are welcome! Please submit issues or pull requests.

## License

This project is licensed under the MIT License.

## Disclaimer

This project is for educational and research purposes only. It does not constitute investment advice. Users are responsible for any risks associated with using this project for actual trading.

## Contact

For questions or suggestions, please open an issue on GitHub.
