#!/usr/bin/env python3
import os
import sys
import json
import time
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from datetime import datetime, timedelta
import requests
import re

# 将项目根目录添加到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from utils.logging_config import logger
from config.config import REMOTE_SERVER, BARK_KEY, BARK_ENDPOINT

class TradeWorkflow:
    def __init__(self):
        self.project_root = project_root
        self.best_strategy_dir = os.path.join(project_root, 'bestgenerations')
        self.results_dir = os.path.join(project_root, 'results')
        self.remote_server = REMOTE_SERVER
        self.bark_key = BARK_KEY
        self.bark_endpoint = BARK_ENDPOINT

    def run_optimization(self):
        """运行主优化程序"""
        logger.info("开始运行策略优化...")
        result = subprocess.run(['python', 'main.py', '--config', './ga.json', '--start-date', '20241001', '--download'], 
                              cwd=self.project_root,
                              capture_output=True,
                              text=True)
        if result.returncode != 0:
            self.send_notification(f"策略优化失败:\n{result.stderr}")
            raise Exception("策略优化失败")
        logger.info("策略优化完成")
        return True


    def get_current_best(self):
        """获取当前最佳策略的fitness值"""
        generations = {}
        current_gen = None
        max_fitness = float('-inf')
        best_strategy = None
        best_results = None

        # 从 fitness_log.txt 读取所有代的 fitness
        try:
            with open(os.path.join(self.project_root, 'logs/fitness_log.txt'), 'r') as file:
                for line in file:
                    gen = self.extract_generation(line)
                    if gen is not None:
                        current_gen = gen
                        if current_gen not in generations:
                            generations[current_gen] = {'max_fitness': None, 'max_fitness_line': '', 'strategy_name': ''}
                    
                    fitness = self.extract_fitness(line)
                    if fitness is not None and current_gen is not None:
                        if generations[current_gen]['max_fitness'] is None or fitness > generations[current_gen]['max_fitness']:
                            generations[current_gen]['max_fitness'] = fitness
                            generations[current_gen]['max_fitness_line'] = line.strip()
                            strategy_name = self.extract_strategy_name(line)
                            if strategy_name:
                                generations[current_gen]['strategy_name'] = strategy_name

            # 找出所有代中的最佳策略
            for gen, data in generations.items():
                if data['max_fitness'] is not None and data['max_fitness'] > max_fitness:
                    max_fitness = data['max_fitness']
                    best_strategy = data['strategy_name']
                    
            if best_strategy:
                # 获取对应的回测结果文件
                strategy_parts = best_strategy.split('_')
                if len(strategy_parts) >= 4:  # 确保有足够的部分
                    generation = strategy_parts[-3]
                    timestamp = strategy_parts[-2]
                    number = strategy_parts[-1].rstrip(',')  # 移除可能的逗号
                    results_file = os.path.join(self.results_dir, 
                                              f'backtest_results_{generation}_{timestamp}_{number}.txt')
                    if os.path.exists(results_file):
                        best_results = results_file
                    else:
                        logger.warning(f"找不到回测结果文件: {results_file}")

            return max_fitness, best_results

        except Exception as e:
            logger.error(f"读取fitness日志出错: {str(e)}")
            return None, None

    def extract_fitness(self, line):
        """从日志行提取fitness值"""
        match = re.search(r'Final Fitness: ([-\d.]+)$', line)
        return float(match.group(1)) if match else None

    def extract_generation(self, line):
        """从日志行提取代数"""
        match = re.search(r'Generation: (\d+)', line)
        return int(match.group(1)) if match else None

    def extract_strategy_name(self, line):
        """从日志行提取策略名称"""
        match = re.search(r'Strategy: (\S+)', line)
        return match.group(1) if match else None

    def create_daily_directory(self):
        """
        创建每日结果目录
        """
        today = datetime.now().strftime('%Y%m%d')
        daily_dir = os.path.join('daily_results', today)
        os.makedirs(daily_dir, exist_ok=True)
        return daily_dir


    def save_best_to_daily(self, generation, results_file, config_file, strategy_file):
        daily_dir = self.create_daily_directory()
        # 创建结果子目录
        results_dir = os.path.join(daily_dir, f'{generation}')
        os.makedirs(results_dir, exist_ok=True)

        # 复制策略文件
        if os.path.exists(strategy_file):
            strategy_name = os.path.basename(strategy_file)
            shutil.copy2(strategy_file, os.path.join(results_dir, strategy_name))
        else:
            logger.warning(f"策略文件不存在：{strategy_file}")
            return False

        # 复制配置文件
        if os.path.exists(config_file):
            shutil.copy2(config_file, os.path.join(results_dir, "config.json"))
        else:
            logger.warning(f"配置文件不存在：{config_file}")
            return False

        # 复制result
        if os.path.exists(results_file):
            shutil.copy2(results_file, os.path.join(results_dir, "results.txt"))
        else:
            logger.warning(f"回测结果文件不存在：{results_file}")
            return False

        # 保存fitness信息
        shutil.copy2("logs/fitness_log.txt", os.path.join(results_dir, "fitness_info.txt"))
        return True


    def upload_to_server(self):
        """
            上传策略到服务器, config file
        """
        if not self.remote_server:
            logger.warning("未配置远程服务器，跳过上传步骤")
            return True
            
        try:
            # 使用 -i 参数指定 SSH 私钥
            subprocess.run(['scp', '-i', self.remote_server['key_path'], 'strategies/config.json', f'{self.remote_server["username"]}@{self.remote_server["hostname"]}:/root/trade/user_data/'])
            subprocess.run(['scp', '-i', self.remote_server['key_path'], 'strategies/GeneStrategy.py', f'{self.remote_server["username"]}@{self.remote_server["hostname"]}:/root/trade/user_data/strategies/'])
            return True
        except Exception as e:
            logger.error(f"上传策略到服务器失败: {str(e)}")
            return False

    def restart_trading(self):
        """重启交易程序"""
        if not self.remote_server:
            logger.warning("未配置远程服务器，跳过重启步骤")
            return True
        try:
            # 这里需要根据实际情况实现重启逻辑
            # 例如通过 SSH 执行重启命令
            subprocess.run(['ssh', "-i", self.remote_server['key_path'], self.remote_server['username'] + '@' + self.remote_server['hostname'], 'systemctl restart freqtrade'])
            return True
        except Exception as e:
            logger.error(f"重启交易程序失败: {str(e)}")
            return False

    def send_notification(self, message):
        """发送通知"""
        if not self.bark_key:
            logger.warning("未配置 Bark key，跳过通知")
            return
        url = "{}/{}/{}".format(self.bark_endpoint, self.bark_key, message)            
        try:
            response = requests.get(url)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"发送Bark通知失败: {e}")

    def compare_strategies(self, results_file1, results_file2):
        """
            比较两个策略的回测结果
            返回： 
            1. True， 当前策略优于远程策略
            2. False， 当前策略劣于远程策略
            精度阈值： 0.03
        """
        metrics1 = self.parse_backtest_results(results_file1)
        metrics2 = self.parse_backtest_results(results_file2)
        
        if not metrics1 or not metrics2:
            return None

        print(metrics1)
        print(metrics2)

        current_profit_percent = metrics1['total_profit_percent']
        remote_profit_percent = metrics2['total_profit_percent']
        current_winrate = metrics1['win_rate']
        remote_winrate = metrics2['win_rate']

        if abs(remote_winrate - current_winrate) < 2 and current_profit_percent > remote_profit_percent:
            return True
        else:
            return False


    def run_backtest(self, config_file, strategy_name):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # 往前推7天
        timerange = f"{start_date.strftime('%Y%m%d')}-"

        current_command = [
            "/Users/zhangjiawei/Projects/freqtrade/.venv/bin/freqtrade",
            "backtesting",
            "--strategy", 
            strategy_name,
            "-c",
            config_file,
            "--timerange", 
            timerange,
            "-d", 
            "/Users/zhangjiawei/Projects/GeneTrader/user_data/data/binance",
            "--userdir",
            "/Users/zhangjiawei/Projects/GeneTrader/user_data",
            "--timeframe-detail",
            "1m",
            "--enable-protections",
            "--cache",
            "none"
        ]

        remote_command = [
            "/Users/zhangjiawei/Projects/freqtrade/.venv/bin/freqtrade",
            "backtesting",
            "--strategy", 
            "GeneStrategy",
            "-c", 
            "user_data/config.json",
            "--timerange",
            timerange,
            "-d", 
            "/Users/zhangjiawei/Projects/GeneTrader/user_data/data/binance",
            "--userdir",
            "/Users/zhangjiawei/Projects/GeneTrader/user_data",
            "--timeframe-detail",
            "1m",
            "--enable-protections",
            "--cache",
            "none"
        ]
        current_result = subprocess.run(current_command, cwd=self.project_root, capture_output=True, text=True)
        remote_result = subprocess.run(remote_command, cwd=self.project_root, capture_output=True, text=True)
        return current_result.stdout, remote_result.stdout


    def run(self):
        """运行完整工作流程"""
        try:
            # 1. 运行优化
            start_time = time.time()
            # skip optimization
            # if not self.run_optimization():
            #     return False
            end_time = time.time()
            consuming_time = int(end_time - start_time)
            self.send_notification("策略优化完成, 耗时: {} 秒".format(consuming_time))

            # 2. 获取当前最佳策略的 fitness
            current_fitness, current_best = self.get_current_best()

            if current_fitness is None:
                self.send_notification("当前没有最佳策略")
                return False
            
            splits = current_best.strip(".txt").split("_")
            generation = splits[-3]
            timestamp = splits[-2]
            number = splits[-1].rstrip(',')  # 移除可能的逗号
            current_fitness = float(current_fitness)
            new_fitness = float(current_fitness)
            
            # 3. 获取最新结果
            best_result_file = current_best
            if not os.path.exists(best_result_file):
                self.send_notification("最优回测结果不存在")
                return False

            # 4. 检查文件
            config_file = 'user_data/temp_config_{}_{}.json'.format(timestamp, number)
            strategy_file = "user_data/strategies/GeneTrader_{}_{}_{}.py".format(generation, timestamp, number)
            if not os.path.exists(config_file):
                self.send_notification("配置文件不存在")
                return False
            if not os.path.exists(strategy_file):
                self.send_notification("策略文件不存在")
                return False

            # 5. 保存最佳策略到 daily_results 目录
            print("save best to daily")
            self.save_best_to_daily(generation, best_result_file, config_file, strategy_file)

            # 6. strategy 统一处理
            print("rename strategy")
            self.rename_strategy_class(strategy_file,)

            # 7. 复制 config_file 到 strategies 目录， 文件名改为config.json
            print("copy config file")
            shutil.copy2(config_file, 'strategies/config.json')
            
            # 8. 比较新旧策略的回测结果
            # - 从服务器获取 config.json  和策略文件
            # - 运行回测
            # - 比较当前策略和新策略
            # - 发送通知
            # 从服务器获取 config.json  和策略文件
            print("download from server")
            if not self.download_from_server():
                self.send_notification("下载配置文件和策略到本地失败")
                return False

            # 运行回测
            print("run backtest")
            strategy_name = strategy_file.split("/")[-1].split(".")[0]  
            current_result, remote_result = self.run_backtest(config_file, strategy_name)

            # 比较当前策略和新策略
            print("compare strategies")
            if not current_result or not remote_result:
                self.send_notification("回测结果为空")
                return False

            comparison = self.compare_strategies(current_result, remote_result)
            if comparison:
                self.send_notification("当前策略优于远程策略")
            else:
                self.send_notification("当前策略劣于远程策略")
                return False

            # 9. 上传到服务器, 策略和config 文件
            if self.upload_to_server():
                # 重启交易程序
                if self.restart_trading():
                    self.send_notification(
                        f"发现更好的策略!\n"
                        f"新 Fitness: {new_fitness:.4f}\n"
                        f"已更新到服务器并重启交易程序"
                    )
                    return True
                else:
                    self.send_notification("重启交易程序失败")
                    return False
            else:
                self.send_notification("上传策略到服务器失败")
                return False

        except Exception as e:
            logger.error(f"工作流程执行失败: {str(e)}")
            self.send_notification(f"工作流程执行失败: {str(e)}")
            return False

    def download_from_server(self):
        if not self.remote_server:
            logger.warning("未配置远程服务器，跳过下载步骤")
            return True
            
        try:
            # 使用 -i 参数指定 SSH 私钥
            subprocess.run(['scp', '-i', self.remote_server['key_path'], f'{self.remote_server["username"]}@{self.remote_server["hostname"]}:/root/trade/user_data/config.json', 'user_data/'])
            subprocess.run(['scp', '-i', self.remote_server['key_path'], f'{self.remote_server["username"]}@{self.remote_server["hostname"]}:/root/trade/user_data/strategies/GeneStrategy.py', 'user_data/strategies/'])
            return True
        except Exception as e:
            logger.error(f"下载策略到本地失败: {str(e)}")
            return False

    def rename_strategy_class(self, file_path, src_path="user_data/strategies/GeneStrategy.py", new_class_name="GeneStrategy"):
        # 读取文件内容
        with open(file_path, 'r') as file:
            content = file.read()
        
        # 使用正则表达式替换类名
        pattern = r'class GeneTrader_gen\d+_\d+_\d+\(IStrategy\)'
        new_content = re.sub(pattern, f'class {new_class_name}(IStrategy)', content)
        
        # 写回文件
        with open(src_path, 'w') as file:
            file.write(new_content)
        
        print(f"Successfully renamed strategy class to {new_class_name}")

    def parse_backtest_results(self, result):
        """
        解析回测结果文件，提取关键指标
        
        Args:
            result_file (str): 回测结果文件的路径
        
        Returns:
            dict: 包含total_profit和win_rate的字典
        """
        try:
            # 读取结果文件
            # with open(result_file, 'r') as f:
            #     result_text = f.read()

            # 寻找包含 TOTAL 的行，这行包含了总体的交易统计
            lines = result.split('\n')
            total_line = None
            for line in lines:
                if '│         TOTAL │' in line:
                    total_line = line
                    break
            
            if total_line:
                # 使用字符串分割来提取数值
                parts = [p.strip() for p in total_line.split('│')]
                # Tot Profit USDT 通常在第4个位置
                total_profit_percent = float(parts[5].strip())
                # Win% 在最后一个位置
                win_rate = float(parts[-2].split()[3])
                
                return {
                    'total_profit_percent': total_profit_percent,
                    'win_rate': win_rate
                }
            else:
                print("未找到包含总计的行")
                return None
                
        except Exception as e:
            print(f"解析结果时出错: {str(e)}")
            return None



if __name__ == "__main__":
    workflow = TradeWorkflow()
    workflow.run()
