# Define the strategies as a variable

STRATEGIES=`cat fitness_log.txt| grep "win_rate: 0.9" | awk -F ': ' '{print $2}' | awk -F ',' '{print $1}'`

# Set default timerange if not provided
TIMERANGE=${1:-"20240101-"}

# Remove any hyphens from TIMERANGE for filename
FILENAME_TIMERANGE=$(echo $TIMERANGE | tr -d '-')


/Users/zhangjiawei/Projects/freqtrade/.venv/bin/freqtrade backtesting -c user_data/config_large.json --timerange $TIMERANGE --strategy-list $STRATEGIES > backtesting_results_${FILENAME_TIMERANGE}.txt --logfile backtesting_results_${FILENAME_TIMERANGE}.log
