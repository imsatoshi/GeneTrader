# Genetic Algorithm Optimization for Trading Strategies

This project uses a genetic algorithm to optimize trading strategy parameters, specifically designed for the Freqtrade trading bot.

## Configuration

Main configuration options are in the `ga.json` file:

- `proxy`: Proxy settings
- `freqtrade_path`: Path to Freqtrade executable
- `strategy_dir`: Directory for strategy files
- `results_dir`: Directory for backtesting results
- `config_file`: Path to Freqtrade configuration file
- `population_size`: Genetic algorithm population size
- `generations`: Number of genetic algorithm iterations
- `crossover_prob`: Crossover probability
- `mutation_prob`: Mutation probability
- `tournament_size`: Tournament selection size
- `pool_processes`: Number of parallel processes
- `max_retries`: Maximum number of retries
- `retry_delay`: Delay between retries
- `project_dir`: Project directory
- `best_generations_dir`: Directory to save best strategies

## Dependencies

- Python 3.7+
- deap
- numpy
- Freqtrade

## Usage

1. Ensure all dependencies are installed.
2. Configure the `ga.json` file.
3. Run the optimization script:
   ```
   python ga_opt.py [--download-data]
   ```
   Use the `--download-data` argument to download data before optimization.

## Main Features

- Optimize trading strategy parameters using genetic algorithms
- Support for multi-process parallel computation
- Dynamic generation and evaluation of strategies
- Save the best strategy from each generation

## Contributing

Contributions are welcome! Please submit issues or pull requests.

## License

This project is licensed under the MIT License.

## Contact

For questions or suggestions, please open an issue.

## Disclaimer

This project is for educational and research purposes only and does not constitute investment advice. Users bear all risks associated with using this project for actual trading.
