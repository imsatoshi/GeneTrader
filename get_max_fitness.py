import re
import os
import glob
import shutil
import paramiko
from pathlib import Path
from datetime import datetime
import json

def extract_fitness(line):
    match = re.search(r'Final Fitness: ([-\d.]+)$', line)
    return float(match.group(1)) if match else None

def extract_generation(line):
    match = re.search(r'Generation: (\d+)', line)
    return int(match.group(1)) if match else None

def extract_strategy_name(line):
    match = re.search(r'Strategy: (\S+)', line)
    return match.group(1) if match else None

def get_config_file(strategy_name):
    last_four_digits = strategy_name[-4:]
    config_files = glob.glob(f"user_data/temp_*_{last_four_digits}.json")
    return config_files[0] if config_files else None

def upload_to_server(local_file, remote_path, hostname, username, key_path):
    """
    Upload file to remote server using SSH key authentication
    """
    try:
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 连接到服务器
        private_key = paramiko.RSAKey(filename=key_path)
        ssh.connect(hostname=hostname, username=username, pkey=private_key)
        
        # 创建SFTP客户端
        sftp = ssh.open_sftp()
        
        # 上传文件
        sftp.put(local_file, remote_path)
        
        # 关闭连接
        sftp.close()
        ssh.close()
        
        print(f"Successfully uploaded {local_file} to {remote_path}")
        return True
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return False

def create_daily_directory():
    """
    创建每日结果目录
    """
    today = datetime.now().strftime('%Y%m%d')
    daily_dir = os.path.join('daily_results', today)
    os.makedirs(daily_dir, exist_ok=True)
    return daily_dir

def save_results(daily_dir, strategy_name, config_file, fitness_info, generation):
    """
    保存当天的所有相关结果
    """
    # 创建结果子目录
    results_dir = os.path.join(daily_dir, f'generation_{generation}')
    os.makedirs(results_dir, exist_ok=True)
    
    # 复制策略文件
    strategy_file = f"user_data/strategies/{strategy_name}.py"
    if os.path.exists(strategy_file):
        shutil.copy2(strategy_file, os.path.join(results_dir, f"{strategy_name}.py"))
    
    split_strategy_name = strategy_name.split("_")
    generation = split_strategy_name[-3]
    last_two = split_strategy_name[-2]
    last_one = split_strategy_name[-1]

    best_config = "user_data/temp_config_{}_{}.json".format(last_two, last_one)
    best_result = "results/backtest_results_{}_{}_{}.txt".format(generation, last_two, last_one)
    # results/backtest_results_gen19_1733132687_3911.txt

    
    # 保存fitness信息
    with open(os.path.join(results_dir, "fitness_info.txt"), "w") as f:
        f.write(fitness_info)
    
    # 复制results
    result_backup = os.path.join(results_dir, "results.txt")
    shutil.copy2(best_result, result_backup)
    
    # 复制配置文件
    config_backup = os.path.join(results_dir, "config.json")
    shutil.copy2(best_config, config_backup)
    
    # 创建运行摘要
    summary = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'strategy_name': strategy_name,
        'generation': generation,
        'fitness_info': fitness_info,
        'config_file': os.path.basename(best_config),
        'result_file': best_result
    }
    
    with open(os.path.join(results_dir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=4)
    
    return results_dir

generations = {}
current_gen = None

with open('logs/fitness_log.txt', 'r') as file:
    for line in file:
        gen = extract_generation(line)
        if gen is not None:
            current_gen = gen
            if current_gen not in generations:
                generations[current_gen] = {'max_fitness': None, 'max_fitness_line': '', 'strategy_name': ''}
        
        fitness = extract_fitness(line)
        if fitness is not None and current_gen is not None:
            if generations[current_gen]['max_fitness'] is None or fitness > generations[current_gen]['max_fitness']:
                generations[current_gen]['max_fitness'] = fitness
                generations[current_gen]['max_fitness_line'] = line.strip()
                generations[current_gen]['strategy_name'] = extract_strategy_name(line)


# 创建一个文件来存储所有的回测命令
with open('backtesting_commands.sh', 'w') as command_file:
    command_file.write("#!/bin/bash\n\n")  

    if generations:
        overall_max_fitness = float('-inf')
        overall_best_gen = None

        for gen, data in sorted(generations.items()):
            if data['max_fitness'] is not None:
                print(f"Generation {gen} max fitness:")
                print(data['max_fitness_line'])
                print(f"Maximum fitness: {data['max_fitness']}")
                
                strategy_name = data['strategy_name'][:-1]
                config_file = get_config_file(strategy_name)
                # print(config_file)
                if config_file:
                    backtesting_command = f"/Users/zhangjiawei/Projects/freqtrade/.venv/bin/freqtrade backtesting --strategy {strategy_name} -c {config_file} --timerange 20240101- --timeframe-detail 1m > generation_{gen}.txt"
                    # print(f"Backtesting command:")
                    # print(backtesting_command)
                    command_file.write(backtesting_command + "\n\n")
                else:
                    print(f"Warning: No matching config file found for strategy {strategy_name}")
                print()

                if data['max_fitness'] > overall_max_fitness:
                    overall_max_fitness = data['max_fitness']
                    overall_best_gen = gen
            else:
                print(f"Generation {gen}: No valid fitness values found\n")

        if overall_best_gen is not None:
            print("Overall best fitness:")
            print(generations[overall_best_gen]['max_fitness_line'])
            print(f"Maximum fitness: {overall_max_fitness}")

            best_strategy_name = generations[overall_best_gen]['strategy_name'][:-1]
            best_config_file = get_config_file(best_strategy_name)
            
            print(best_config_file)
            print(best_strategy_name)
            
            if best_config_file:
                # 创建每日结果目录
                daily_dir = create_daily_directory()
                
                # 保存所有相关结果
                results_dir = save_results(
                    daily_dir,
                    best_strategy_name,
                    best_config_file,
                    generations[overall_best_gen]['max_fitness_line'],
                    overall_best_gen
                )
                
                # 创建一个临时目录来存储最佳策略相关文件用于上传
                best_strategy_dir = "best_strategy"
                os.makedirs(best_strategy_dir, exist_ok=True)
                
                # 复制整个结果目录到临时目录
                shutil.copytree(results_dir, os.path.join(best_strategy_dir, 'results'), dirs_exist_ok=True)
                
                # 复制最佳策略文件
                strategy_file = f"strategy/{best_strategy_name}.py"
                if os.path.exists(strategy_file):
                    shutil.copy2(strategy_file, os.path.join(best_strategy_dir, f"{best_strategy_name}.py"))
                
                # 复制配置文件
                shutil.copy2(best_config_file, os.path.join(best_strategy_dir, "config.json"))
                
                # 创建一个包含fitness信息的文件
                with open(os.path.join(best_strategy_dir, "fitness_info.txt"), "w") as f:
                    f.write(generations[overall_best_gen]['max_fitness_line'])
                
                # 压缩文件夹
                shutil.make_archive(best_strategy_dir, 'zip', best_strategy_dir)
                
                # 上传到服务器
                # 注意：需要根据实际情况修改这些参数
                hostname = "8.221.141.150"
                username = "root"
                key_path = os.path.expanduser("~/.ssh/id_rsa")  # SSH密钥路径
                remote_path = f"/root/opt_path/best_strategy_{overall_best_gen}.zip"
                
                if upload_to_server(f"{best_strategy_dir}.zip", remote_path, hostname, username, key_path):
                    print(f"Successfully uploaded best strategy (Generation {overall_best_gen}) to server")
                else:
                    print("Failed to upload strategy to server")
                
                # 清理临时文件
                shutil.rmtree(best_strategy_dir)
                os.remove(f"{best_strategy_dir}.zip")
                
                best_backtesting_command = f"/Users/zhangjiawei/Projects/freqtrade/.venv/bin/freqtrade backtesting --strategy {best_strategy_name} -c {best_config_file} --timerange 20240401- --timeframe-detail 1m > best_generation_{overall_best_gen}.txt"
                print("Best strategy backtesting command:")
                print(best_backtesting_command)
                command_file.write("# Best strategy backtesting command\n")
                command_file.write(best_backtesting_command + "\n")
            else:
                print(f"Warning: No matching config file found for best strategy {best_strategy_name}")
    else:
        print("No valid generations or fitness values found in the file.")

print("\nDebug information:")
print(f"Total generations processed: {len(generations)}")
print(f"Found any fitness values: {'Yes' if any(gen['max_fitness'] is not None for gen in generations.values()) else 'No'}")
print(f"\nAll backtesting commands have been written to 'backtesting_commands.sh'")
