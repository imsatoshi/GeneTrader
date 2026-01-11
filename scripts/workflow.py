"""Trade workflow automation for GeneTrader."""
import os
import sys
import re
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests
from requests.auth import HTTPBasicAuth

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from utils.logging_config import logger
from utils.fitness_helpers import extract_fitness, extract_generation, extract_strategy_name
from config.config import REMOTE_SERVER, BARK_KEY, BARK_ENDPOINT
from config.settings import settings
from data.downloader import download_data  


def clean_directory(path):
    """清空目录中的所有文件，但保留目录本身。"""
    try:
        for item in Path(path).iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    except Exception as e:
        logger.error(f"清空目录 {path} 时出错: {str(e)}")

class TradeWorkflow:
    def __init__(self, ga_config_file):
        self.ga_config_file = ga_config_file
        self.project_root = project_root
        self.best_strategy_dir = os.path.join(project_root, 'bestgenerations')
        self.results_dir = os.path.join(project_root, 'results')
        self.remote_server = REMOTE_SERVER
        self.bark_key = BARK_KEY
        self.bark_endpoint = BARK_ENDPOINT
        self.max_retries = 3    # 最大重试次数
        self.retry_interval = 5 # 重试间隔（分钟）

    def clean_workspace(self):
        """清理工作空间"""
        try:
            # 清空 results 目录
            clean_directory('results')
            # 清空 bestgenerations 目录
            clean_directory('bestgenerations')
            # 清空 user_data/backtest_results 目录
            clean_directory('user_data/backtest_results')
            # 清空 user_data/strategies 目录
            clean_directory('user_data/strategies')
            # 清空 logs 目录
            clean_directory('logs')
            # 清空 checkpoints 目录
            clean_directory('checkpoints')
            # 删除 user_data/temp_*.json 文件
            temp_files = Path('user_data').glob('temp_*.json')
            for temp_file in temp_files:
                temp_file.unlink()
            logger.info("工作空间已成功清理")
        except Exception as e:
            logger.error(f"清理工作空间时出错: {str(e)}")

    def get_next_run_time(self):
        """
        计算下一次运行的时间点
        
        Returns:
            datetime: 下一次运行的时间点
        """
        now = datetime.now()
        next_run = now + timedelta(minutes=1)
        return next_run

    def run_optimization(self):
        """运行主优化程序"""
        logger.info("开始运行策略优化...")
        # Calculate the start date as 30 days before today
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        result = subprocess.run(['python3', 'main.py', '--config', self.ga_config_file, '--start-date', start_date, '--download'], 
                              cwd=self.project_root,
                              capture_output=True,
                              text=True)
        # print(result.stdout)
        # print(result.stderr)
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
                            strategy_name = extract_strategy_name(line)
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
            # 将端口号转换为字符串
            port = str(self.remote_server['port'])

            # 使用 -i 参数指定 SSH 私钥
            result1 = subprocess.run([
                'scp', '-i', self.remote_server['key_path'],
                '-P', port,  # 使用转换后的字符串
                'strategies/config.json',
                f'{self.remote_server["username"]}@{self.remote_server["hostname"]}:{self.remote_server["remote_datadir"]}'
                ])
            if result1.returncode != 0:
                logger.error("上传 config.json 到服务器失败")
                return False

            result2 = subprocess.run([
                'scp', '-i', self.remote_server['key_path'],
                '-P', port,  # 使用转换后的字符串
                'strategies/GeneStrategy.py',
                f'{self.remote_server["username"]}@{self.remote_server["hostname"]}:{self.remote_server["remote_strategydir"]}'
                ])
            if result2.returncode != 0:
                logger.error("上传 GeneStrategy.py 到服务器失败")
                return False

            return True
        except Exception as e:
            logger.error(f"上传策略到服务器失败: {str(e)}")
            return False

    def restart_trading(self, is_restful=False):
        """重启交易程序"""
        if not self.remote_server:
            logger.warning("未配置远程服务器，跳过重启步骤")
            return True
        
        if not self.remote_server['api_url'] or not self.remote_server['freqtrade_username'] or not self.remote_server['freqtrade_password']:
            is_restful = False
        else:
            is_restful = True
        try:
            # 通过 SSH 执行重启命令
            if not is_restful:
                port = str(self.remote_server['port'])
                subprocess.run([
                    'ssh', "-i", self.remote_server['key_path'],
                    "-p", port,
                    self.remote_server['username'] + '@' + self.remote_server['hostname'],
                    'systemctl restart freqtrade'
                ])
                return True
            else:
                # restart freqtrade by restful api  
                return self.restart_freqtrade(self.remote_server['api_url'], self.remote_server['username'], self.remote_server['password'])
        except Exception as e:
            logger.error(f"重启交易程序失败: {str(e)}")
            return False

    def restart_freqtrade(self, api_url, username, password):
        try:
            response = requests.post(
                f"{api_url}/restart",
                auth=HTTPBasicAuth(username, password)
            )
            response.raise_for_status()
            logger.info("Freqtrade restarted successfully.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to restart Freqtrade: {e}")
            return False

    def send_notification(self, message):
        """发送通知"""
        if not self.bark_key or not self.bark_endpoint:
            logger.info("skip bark notification")
        else:
            strategy_name = settings.base_strategy_file.split("/")[-1].split(".")[0]
            message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {strategy_name} {message}"
            message = message.replace(" ", "%20")
            url = f"{self.bark_endpoint}/{self.bark_key}/{message}"
            try:
                response = requests.get(url)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"发送Bark通知失败: {e}")

    def exec_backtest(self, config_file, strategy_name, max_retries=3, retry_interval=5):
        """
        执行回测命令并重试
        Args:
            config_file (str): 配置文件路径
            strategy_name (str): 策略名称
            max_retries (int): 最大重试次数
            retry_interval (int): 重试间隔（分钟）
        Returns:
            str: 回测结果
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # 往前推7天
        timerange = f"{start_date.strftime('%Y%m%d')}-"
        logger.info(f"运行回测: {timerange}")

        # 构建回测命令
        command = [
            settings.freqtrade_path,
            "backtesting",
            "--strategy",
            strategy_name,
            "-c",
            config_file,
            "--timerange",
            timerange,
            "-d",
            os.path.join(settings.project_dir, settings.data_dir),
            "--userdir",
            os.path.join(settings.project_dir, settings.user_dir),
            "--timeframe-detail",
            "1m",
            "--enable-protections",
            "--cache",
            "none"
        ]

        result = ""
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1} for backtest with strategy: {strategy_name}")
                process_result = subprocess.run(command, cwd=self.project_root, capture_output=True, text=True)
                if process_result.returncode == 0:
                    result = process_result.stdout
                    break
                else:
                    logger.warning(f"Backtest failed on attempt {attempt + 1}: {process_result.stderr}")
            except Exception as e:
                logger.error(f"Error during backtest attempt {attempt + 1}: {str(e)}")
            time.sleep(retry_interval * 60)  # Convert retry_interval to seconds
        return result

    def run_backtest(self, config_file, strategy_name, max_retries=3, retry_interval=5):
        """
        执行本地和远程回测
        Args:
            config_file (str): 配置文件路径
            strategy_name (str): 本地策略名称
            max_retries (int): 最大重试次数
            retry_interval (int): 重试间隔（分钟）
        Returns:
            tuple: 本地和远程回测结果
        """
        # 执行本地回测
        local_result = self.exec_backtest(config_file, strategy_name, max_retries, retry_interval)

        # 执行远程回测
        remote_result = self.exec_backtest("user_data/config.json", "GeneStrategy", max_retries, retry_interval)

        return local_result, remote_result

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

    def rename_strategy_class(self, file_path, src_path, new_class_name="GeneStrategy"):
        # 读取文件内容
        with open(file_path, 'r') as file:
            content = file.read()

        timestring = '"' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '"'


        # 使用正则表达式替换类名
        pattern = r'class GeneTrader_gen\d+_\d+_\d+\(IStrategy\):'
        # new_content = re.sub(pattern, f'class {new_class_name}(IStrategy)', content)
        new_content = re.sub(pattern, f'class {new_class_name}(IStrategy):\n    def version(self) -> str:\n        return {timestring}\n', content)
        # 写回文件
        with open(src_path, 'w') as file:
            file.write(new_content)
        
        logger.info(f"Successfully renamed strategy class to {new_class_name}")

    def parse_backtest_results(self, result):
        try:
            # 读取结果文件
            # 寻找包含 TOTAL 的行，这行包含了总体的交易统计
            lines = result.split('\n')
            total_line = None
            for line in lines:
                if 'TOTAL' in line:
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
                logger.error("未找到包含总计的行")
                return None
                
        except Exception as e:
            logger.error(f"解析结果时出错: {str(e)}")
            return None

    def compare_strategies(self, results_file1, results_file2):
        """
        比较两个策略的回测结果
        
        Args:
            results_file1 (str): 当前策略的回测结果
            results_file2 (str): 远程策略的回测结果
            
        Returns:
            bool: True 如果当前策略更好，False 如果远程策略更好
        """
        metrics1 = self.parse_backtest_results(results_file1)
        metrics2 = self.parse_backtest_results(results_file2)
        
        if not metrics1 or not metrics2:
            logger.error("比较策略：解析结果失败")
            logger.debug(f"当前策略结果: {metrics1}")
            logger.debug(f"远程策略结果: {metrics2}")
            return False

        current_profit_percent = metrics1['total_profit_percent']
        remote_profit_percent = metrics2['total_profit_percent']
        current_winrate = metrics1['win_rate']
        remote_winrate = metrics2['win_rate']

        logger.info(f"当前策略: 收益率={current_profit_percent}%, 胜率={current_winrate}%")
        logger.info(f"远程策略: 收益率={remote_profit_percent}%, 胜率={remote_winrate}%")

        # 胜率差异小于2%时，比较收益率
        if abs(remote_winrate - current_winrate) < 2:
            return current_profit_percent > remote_profit_percent
        # 否则需要同时满足胜率和收益率都更好
        return current_winrate > remote_winrate and current_profit_percent > remote_profit_percent

    def run(self):
        """运行完整工作流程"""
        try:

            # clean workspace
            self.clean_workspace()
            self.send_notification("清理运行空间完毕")
            # 1. 运行优化
            start_time = time.time()
            if not self.run_optimization():
                return False
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
            logger.info("save best to daily: {}".format(best_result_file))
            self.save_best_to_daily(generation, best_result_file, config_file, strategy_file)

            # 6. strategy 统一处理
            logger.info("rename strategy: {} to GeneStrategy".format(strategy_file))
            self.rename_strategy_class(strategy_file, "strategies/GeneStrategy.py")

            # 7. 复制 config_file 到 strategies 目录， 文件名改为config.json
            logger.info("copy config file")
            shutil.copy2(config_file, 'strategies/config.json')
            
            # 8. 比较新旧策略的回测结果
            # - 从服务器获取 config.json  和策略文件
            logger.info("download from server")
            if not self.download_from_server():
                self.send_notification("下载配置文件和策略到本地失败")
                return False
            
            start_date = datetime.now() - timedelta(days=3)
            max_retries = 3
            retry_interval = 5  # 重试间隔(分钟)
            
            for attempt in range(max_retries):
                try:
                    download_data(start_date=start_date)
                    break  # 如果下载成功,跳出重试循环
                except Exception as e:
                    logger.warning(f"数据下载失败(尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"等待 {retry_interval} 分钟后重试...")
                        time.sleep(retry_interval * 60)  # 转换为秒
                    else:
                        logger.error("达到最大重试次数,数据下载失败")
                        raise  # 如果达到最大重试次数还是失败,抛出异常
            
            # 运行回测
            logger.info("run backtest")
            strategy_name = strategy_file.split("/")[-1].split(".")[0]  
            current_result, remote_result = self.run_backtest(config_file, strategy_name)

            # 比较当前策略和新策略
            logger.info("compare strategies")
            if not current_result or not remote_result:
                self.send_notification("回测结果为空")
                return False
            comparison = self.compare_strategies(current_result, remote_result)
            if comparison:
                self.send_notification("当前策略优于远程策略")
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
            else:
                self.send_notification("当前策略劣于远程策略")
                return True

        except Exception as e:
            logger.error(f"工作流程执行失败: {str(e)}")
            self.send_notification(f"工作流程执行失败: {str(e)}")
            return False

    def run_with_retry(self):
        """
        使用重试机制运行工作流程
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"开始第 {attempt + 1} 次尝试运行工作流...")
                if self.run():
                    return True
                else:
                    logger.warning(f"工作流运行失败，等待 {self.retry_interval} 分钟后重试...")
                    time.sleep(self.retry_interval * 60)
            except Exception as e:
                logger.error(f"工作流运行出错: {str(e)}")
                if attempt < self.max_retries - 1:
                    logger.info(f"等待 {self.retry_interval} 分钟后重试...")
                    time.sleep(self.retry_interval * 60)
                else:
                    logger.error("达到最大重试次数，退出运行")
                    self.send_notification(f"工作流运行失败，已达到最大重试次数: {str(e)}")
                    return False
        return False

    def run_forever(self, start_immediately=False):
        """
        在固定时间点持续运行工作流程
        """
        logger.info("启动定时运行模式")
        self.send_notification("交易工作流开始运行")
        
        while True:
            try:
                if not start_immediately:
                    # 计算下一次运行时间
                    next_run = self.get_next_run_time()
                    now = datetime.now()
                    wait_seconds = (next_run - now).total_seconds()
                    
                    logger.info(f"下次运行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"等待时间: {wait_seconds/3600:.1f} 小时")
                    
                    # 等待到下一个运行时间点
                    time.sleep(wait_seconds)
                
                # 运行工作流（带重试机制）
                logger.info(f"开始运行定时任务: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.run_with_retry()
                logger.info(f"完成本次运行: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Reset start_immediately after the first run
                start_immediately = False
                
            except KeyboardInterrupt:
                logger.info("收到终止信号，程序退出")
                self.send_notification("交易工作流已停止运行")
                break
            except Exception as e:
                logger.error(f"发生未预期的错误: {str(e)}")
                self.send_notification(f"发生未预期的错误: {str(e)}")
                # 等待一段时间后继续
                time.sleep(self.retry_interval * 60)


if __name__ == "__main__":
    # 创建一个解析器
    parser = argparse.ArgumentParser(description="Trade Workflow Script")
    # 添加一个参数，用于立即运行优化
    parser.add_argument('--optimize', type=str, help="optimize")
    parser.add_argument('--now', action='store_true', help="立即运行优化")
    parser.add_argument('--config', type=str, help="配置文件路径")
    parser.add_argument('--backtest', nargs=4, metavar=('CONFIG1', 'STRATEGY1', 'CONFIG2', 'STRATEGY2'), help="运行两个策略的回测并比较")
    
    # 解析命令行参数
    args = parser.parse_args()
    ga_config_file = ''
    if args.config:
        ga_config_file = args.config
    else:
        ga_config_file = 'ga.json' 

    workflow = TradeWorkflow(ga_config_file)

    # 如果传入了两个策略文件运行回测并比较
    if args.backtest:
        config1, strategy1, config2, strategy2 = args.backtest
        logger.info(f"开始对两个策略文件运行回测：{strategy1} 和 {strategy2}")
        
        # 运行第一个策略的回测
        logger.info(f"运行策略 1：{strategy1}")
        result1 = workflow.exec_backtest(config1, strategy1)
        if not result1:  # 检查回测结果是否为空
            logger.error(f"策略 {strategy1} 回测失败")
            print(f"策略 {strategy1} 回测失败")
            sys.exit(1)

        # 运行第二个策略的回测
        logger.info(f"运行策略 2：{strategy2}")
        result2 = workflow.exec_backtest(config2, strategy2)
        if not result2:  # 检查回测结果是否为空
            logger.error(f"策略 {strategy2} 回测失败")
            print(f"策略 {strategy2} 回测失败")
            sys.exit(1)

        # 比较两个回测结果
        logger.info("比较两个策略的回测结果")
        comparison_result = workflow.compare_strategies(result1, result2)
        if comparison_result:
            logger.info("策略 1 优于 策略 2")
            print("策略 1 优于 策略 2")
        else:
            logger.info("策略 2 优于 策略 1")
            print("策略 2 优于 策略 1")
        sys.exit(0)

    if args.optimize:
        if args.now:
            logger.info("立即运行优化")
            try:
                workflow.run_forever(start_immediately=True)  # Pass True to start immediately
            except Exception as e:
                logger.error(f"优化运行失败: {str(e)}")
                sys.exit(1)
        else:
            try:
                workflow.run_forever()
            except KeyboardInterrupt:
                logger.info("程序已终止")
                sys.exit(0)
