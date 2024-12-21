from datetime import datetime, timedelta
import re

def rename_strategy_class(file_path, src_path, new_class_name="GeneStrategy"):
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
    


if __name__ == "__main__":
    file_path = "/Users/zhangjiawei/Projects/GeneTrader/candidates/E0V1E_Bull_copy.py"
    rename_strategy_class(file_path, '/Users/zhangjiawei/Projects/GeneTrader/scripts/Gene.py')