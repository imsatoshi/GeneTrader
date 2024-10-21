# Genetic Algorithm for Trading Strategy Optimization

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
- Checkpointing and ability to resume from the latest checkpoint

## Prerequisites

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

3. Create a configuration file:
   ```
   cp ga.json.example ga.json
   ```

4. Edit `ga.json` to configure the genetic algorithm parameters and other settings according to your needs.

## Configuration

Edit `ga.json` (or your custom config file) to configure:

- Genetic algorithm parameters (population size, generations, tournament size)
- Mutation and crossover probabilities
- Number of trading pairs to optimize
- Maximum open trades
- Parallel processing options
- File paths and directories
- Checkpoint frequency

## Usage

Run the optimization script with the following command:

```
python main.py [options]
```

Available options:

- `--config CONFIG_FILE`: Specify a custom configuration file (default is 'ga.json')
- `--download`: Download data before running the algorithm
- `--start-date YYYYMMDD`: Start date for data download (default is '20240101')
- `--end-date YYYYMMDD`: End date for data download (default is today's date)
- `--resume`: Resume from the latest checkpoint

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
   python main.py --download --start-date 20230101 --end-date 20231231
   ```

5. Resume from the latest checkpoint:
   ```
   python main.py --resume
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

## Checkpointing

The algorithm saves checkpoints at regular intervals (configurable in the settings). These checkpoints allow you to resume the optimization process from where it left off in case of interruption. Use the `--resume` option to start from the latest checkpoint.

## Contributing

Contributions are welcome! Please submit issues or pull requests.

## License

This project is licensed under the MIT License.

## Disclaimer

This project is for educational and research purposes only. It does not constitute investment advice. Users are responsible for any risks associated with using this project for actual trading.

## Contact

For questions or suggestions, please open an issue on GitHub.

## Community

Stay updated and engage with our community:

- [GeneTrader Telegram Channel](https://t.me/gene_trader) - For updates and announcements
- [GeneTrader Algorithm Group](https://t.me/gaalgo_trader) - For discussions and support

## Disclaimer

This project is for educational and research purposes only. It does not constitute investment advice. Users are responsible for any risks associated with using this project for actual trading.

## Optimization Summary

Below is an example of optimization progress over 20 generations:

| Generation | Total Trades | Win Rate (%) | Total Profit (%) | Profit Factor | Sharpe Ratio | Max Drawdown (%) | Duration (HH:MM) |
|------------|--------------|--------------|------------------|---------------|--------------|------------------|-------------------|
| Gen 1      | 257.00       | 68.50        | 36.23            | 1.13          | 0.97         | 6.28             | 1:38              |
| Gen 2      | 569.00       | 69.80        | 243.62           | 1.43          | 6.85         | 93.70            | 2:10              |
| Gen 3      | 354.00       | 72.30        | 145.16           | 1.36          | 3.45         | 26.62            | 0:57              |
| Gen 4      | 358.00       | 74.30        | 202.59           | 1.45          | 4.27         | 49.34            | 0:56              |
| Gen 5      | 322.00       | 82.00        | 97.63            | 1.23          | 2.01         | 21.16            | 1:22              |
| Gen 6      | 376.00       | 79.50        | 1048.38          | 1.75          | 6.77         | 270.10           | 1:30              |
| Gen 7      | 565.00       | 85.70        | 365.68           | 1.56          | 6.66         | 100.31           | 0:51              |
| Gen 8      | 473.00       | 87.10        | 1695.53          | 2.39          | 9.24         | 1273.81          | 0:57              |
| Gen 9      | 421.00       | 85.50        | 669.49           | 2.00          | 8.25         | 758.28           | 0:54              |
| Gen 10     | 587.00       | 84.20        | 62.30            | 1.17          | 2.28         | 10.27            | 1:01              |
| Gen 11     | 471.00       | 86.60        | 1039.76          | 2.07          | 9.10         | 227.49           | 0:54              |
| Gen 12     | 457.00       | 87.10        | 952.52           | 2.16          | 8.75         | 1078.84          | 0:54              |
| Gen 13     | 505.00       | 86.90        | 1974.44          | 2.23          | 9.38         | 2236.29          | 0:57              |
| Gen 14     | 460.00       | 88.70        | 2567.82          | 2.99          | 11.25        | 2908.36          | 0:51              |
| Gen 15     | 403.00       | 87.80        | 1209.20          | 2.60          | 10.91        | 424.23           | 0:54              |
| Gen 16     | 393.00       | 86.50        | 894.79           | 2.10          | 8.30         | 203.45           | 0:57              |
| Gen 17     | 360.00       | 86.10        | 637.22           | 2.02          | 7.30         | 148.79           | 1:01              |
| Gen 18     | 382.00       | 85.10        | 373.27           | 1.68          | 5.73         | 81.84            | 1:09              |
| Gen 19     | 384.00       | 87.20        | 519.37           | 1.74          | 5.89         | 133.51           | 1:03              |
| Gen 20     | 335.00       | 86.30        | 309.84           | 1.91          | 5.97         | 62.27            | 1:06              |

This table shows the progress of the genetic algorithm optimization over 20 generations. Key metrics include:

- Total Trades: The number of trades executed by the strategy.
- Win Rate: The percentage of profitable trades.
- Total Profit: The cumulative profit percentage.
- Profit Factor: The ratio of gross profit to gross loss.
- Sharpe Ratio: A measure of risk-adjusted return.
- Max Drawdown: The maximum observed loss from a peak to a trough.
- Duration: The time taken for each generation's optimization.

The optimization
