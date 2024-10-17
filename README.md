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

## Configuration

Edit `ga.json` (or your custom config file) to configure:

- Genetic algorithm parameters (population size, generations, tournament size)
- Mutation and crossover probabilities
- Number of trading pairs to optimize
- Maximum open trades
- Parallel processing options
- File paths and directories

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
4. The genetic algorithm creates an initial population of trading strategies.
5. For each generation:
   - Strategies are evaluated in parallel using backtesting.
   - The best strategies are selected for the next generation.
   - Crossover and mutation operations are applied to create new strategies.
   - The best individual from each generation is saved.
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

Stay updated and engage with our community:

- [GeneTrader Telegram Channel](https://t.me/gene_trader) - For updates and announcements
- [GeneTrader Algorithm Group](https://t.me/gaalgo_trader) - For discussions and support

## Disclaimer

This project is for educational and research purposes only. It does not constitute investment advice. Users are responsible for any risks associated with using this project for actual trading.
