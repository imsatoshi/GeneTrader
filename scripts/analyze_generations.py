import re
import os

def extract_metrics(content):
    metrics = {}
    metrics['Total Trades'] = int(re.search(r'Total/Daily Avg Trades\s+│\s+(\d+)', content).group(1))
    metrics['Win Rate'] = float(re.search(r'TOTAL\s+│\s+\d+\s+│\s+[\d.-]+\s+│\s+[\d.-]+\s+│\s+[\d.-]+\s+│\s+[\d:]+\s+│\s+\d+\s+\d+\s+\d+\s+([\d.]+)', content).group(1))
    metrics['Total Profit %'] = float(re.search(r'Total profit %\s+│\s+([\d.]+)%', content).group(1))
    metrics['Profit Factor'] = float(re.search(r'Profit factor\s+│\s+([\d.]+)', content).group(1))
    metrics['Sharpe Ratio'] = float(re.search(r'Sharpe\s+│\s+([\d.]+)', content).group(1))
    metrics['Calmar Ratio'] = float(re.search(r'Calmar\s+│\s+([\d.]+)', content).group(1))
    metrics['Avg Duration'] = re.search(r'TOTAL\s+│\s+\d+\s+│\s+[\d.-]+\s+│\s+[\d.-]+\s+│\s+[\d.-]+\s+│\s+([\d:]+)', content).group(1)
    return metrics

def compare_generations(generations):
    metrics = ['Total Trades', 'Win Rate', 'Total Profit %', 'Profit Factor', 'Sharpe Ratio', 'Calmar Ratio', 'Avg Duration']
    
    print("Generation | " + " | ".join(f"{metric:<15}" for metric in metrics))
    print("-----------|-" + "-|-".join("-" * 15 for _ in metrics))

    for gen, data in generations.items():
        print(f"{gen:<10} | " + " | ".join(f"{data[metric]:<15}" if isinstance(data[metric], str) else f"{data[metric]:<15.2f}" for metric in metrics))

    # Calculate and print improvements
    print("\nImprovements (compared to Generation 1):")
    gen1_data = generations['Gen 1']
    for gen, data in generations.items():
        if gen != 'Gen 1':
            improvements = []
            for metric in metrics:
                if metric != 'Avg Duration':
                    improvement = ((data[metric] - gen1_data[metric]) / gen1_data[metric]) * 100
                    improvements.append(f"{improvement:+.2f}%")
                else:
                    improvements.append("N/A")
            print(f"{gen:<10} | " + " | ".join(f"{imp:<15}" for imp in improvements))

# Read all generation files
generations = {}
for i in range(1, 21):
    filename = f'generation_{i}.txt'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            content = f.read()
            generations[f'Gen {i}'] = extract_metrics(content)

# Compare all generations
compare_generations(generations)