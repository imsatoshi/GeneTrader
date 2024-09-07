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

## Performance

Here's an example of the performance metrics for an optimized strategy:

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                      ┃ Value               ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ Backtesting from            │ 2024-05-04 00:00:00 │
│ Backtesting to              │ 2024-09-07 09:10:00 │
│ Max open trades             │ 2                   │
│ Total/Daily Avg Trades      │ 342 / 2.71          │
│ Starting balance            │ 60 USDT             │
│ Final balance               │ 411.695 USDT        │
│ Absolute profit             │ 351.695 USDT        │
│ Total profit %              │ 586.16%             │
│ CAGR %                      │ 26383.41%           │
│ Sortino                     │ -100.00             │
│ Sharpe                      │ 49.83               │
│ Calmar                      │ 89788.94            │
│ Profit factor               │ 863.17              │
│ Expectancy (Ratio)          │ 1.03 (2.52)         │
│ Avg. daily profit %         │ 4.65%               │
│ Best Pair                   │ NOT/USDT 49.15%     │
│ Worst Pair                  │ CAKE/USDT 0.00%     │
│ Max Consecutive Wins / Loss │ 341 / 1             │
│ Absolute Drawdown (Account) │ 0.10%               │
│ Market change               │ -31.74%             │
└─────────────────────────────┴─────────────────────┘

Strategy Summary:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃                             Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃          Drawdown ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ GeneTrader_gen2_20240907_174909_7870 │    342 │         1.15 │         351.695 │       586.16 │     17:35:00 │  341     0     1  99.7 │ 0.408 USDT  0.10% │
└──────────────────────────────────────┴────────┴──────────────┴─────────────────┴──────────────┴──────────────┴────────────────────────┴───────────────────┘

Note: These results are from a specific backtesting period and may not represent future performance.

## Contributing

Contributions are welcome! Please submit issues or pull requests.

## License

This project is licensed under the MIT License.

## Contact

For questions or suggestions, please open an issue.

## Disclaimer

This project is for educational and research purposes only and does not constitute investment advice. Users bear all risks associated with using this project for actual trading.
