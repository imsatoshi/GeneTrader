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

## Contributing

Contributions are welcome! Please submit issues or pull requests.

## License

This project is licensed under the MIT License.

## Disclaimer

This project is for educational and research purposes only. It does not constitute investment advice. Users are responsible for any risks associated with using this project for actual trading.

## Contact

For questions or suggestions, please open an issue on GitHub.
