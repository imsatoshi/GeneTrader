import matplotlib.pyplot as plt
import re
from collections import defaultdict
import csv

# 读取数据文件
with open('fitness_log.txt', 'r') as file:
    data = file.read()

# 解析数据
generation_data = defaultdict(lambda: {'fitnesses': [], 'profits': [], 'win_rates': []})

for line in data.split('\n'):
    match = re.search(r'Generation: (\d+).+fitness: ([-\d.]+)', line)
    if match:
        gen = int(match.group(1))
        fit = float(match.group(2))
        generation_data[gen]['fitnesses'].append(fit)
        
        profit_match = re.search(r'total_profit_percent: ([-\d.]+)', line)
        if profit_match:
            profit = float(profit_match.group(1))
            generation_data[gen]['profits'].append(profit)
        
        win_rate_match = re.search(r'win_rate: ([-\d.]+)', line)
        if win_rate_match:
            win_rate = float(win_rate_match.group(1))
            if win_rate < 1.0:  # 过滤掉 win_rate 为 1.0 的数据
                generation_data[gen]['win_rates'].append(win_rate)

# 提取每代的最大值
generations = sorted(generation_data.keys())
max_fitnesses = [max(generation_data[gen]['fitnesses']) for gen in generations]
max_profits = [max(generation_data[gen]['profits']) for gen in generations]
max_win_rates = [max(generation_data[gen]['win_rates']) for gen in generations]

# 保存数据到CSV文件
with open('genetic_algorithm_results.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(['Generation', 'Max Fitness', 'Max Profit (%)', 'Max Win Rate'])
    for gen, fit, profit, win_rate in zip(generations, max_fitnesses, max_profits, max_win_rates):
        csvwriter.writerow([gen, fit, profit, win_rate])

# 创建三个子图
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 18))

# 绘制 Fitness vs Generation 散点图和连线
for gen in generations:
    ax1.scatter([gen] * len(generation_data[gen]['fitnesses']), generation_data[gen]['fitnesses'], alpha=0.5)
ax1.plot(generations, max_fitnesses, color='red', linewidth=2, label='Max Fitness')
ax1.set_xlabel('Generation')
ax1.set_ylabel('Fitness')
ax1.set_title('Fitness vs Generation')
ax1.legend()

# 绘制 Total Profit vs Generation 散点图和连线
for gen in generations:
    ax2.scatter([gen] * len(generation_data[gen]['profits']), generation_data[gen]['profits'], alpha=0.5)
ax2.plot(generations, max_profits, color='red', linewidth=2, label='Max Profit (%)')
ax2.set_xlabel('Generation')
ax2.set_ylabel('Total Profit (%)')
ax2.set_title('Total Profit (%) vs Generation')
ax2.legend()

# 绘制 Win Rate vs Generation 散点图和连线
for gen in generations:
    win_rates = [wr for wr in generation_data[gen]['win_rates'] if wr != 1.0]  # 再次过滤，以防万一
    ax3.scatter([gen] * len(win_rates), win_rates, alpha=0.5)
ax3.plot(generations, [max(wr for wr in generation_data[gen]['win_rates'] if wr != 1.0) for gen in generations], color='red', linewidth=2, label='Max Win Rate')
ax3.set_xlabel('Generation')
ax3.set_ylabel('Win Rate')
ax3.set_title('Win Rate vs Generation (excluding 1.0)')
ax3.legend()

plt.tight_layout()

# 保存图像到本地
plt.savefig('genetic_algorithm_results.png', dpi=300, bbox_inches='tight')

print("数据已保存到 genetic_algorithm_results.csv")
print("图像已保存到 genetic_algorithm_results.png")