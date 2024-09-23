
awk -F', ' '
{
    profit = 0
    winrate = 0
    for (i=1; i<=NF; i++) {
        if ($i ~ /total_profit_percent:/) {
            split($i, a, ": ")
            profit = a[2] + 0
        }
        if ($i ~ /win_rate:/) {
            split($i, b, ": ")
            winrate = b[2] + 0
        }
    }
    # if (profit > 0.8 && winrate > 0.84)
    if (winrate > 0.83)
        print profit, $0
}' ./fitness_log.txt | sort -rn | awk -F ', ' '{print $1, $3, $4, $5, $6}'

