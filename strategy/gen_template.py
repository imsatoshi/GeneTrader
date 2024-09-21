import re

def parse_parameters(file_content):
    parameters = []
    pattern = r'(\w+)\s*=\s*(Int|Decimal)Parameter\(([-\d.]+),\s*([-\d.]+),\s*default=([-\d.]+)(?:,\s*decimals=(\d+))?,\s*space=\'(\w+)\',\s*optimize=(True|False)\)'
    matches = re.findall(pattern, file_content)
    
    for match in matches:
        name, param_type, start, end, default, decimals, space, optimize = match
        
        if param_type == 'Decimal':
            if decimals:
                decimal_places = int(decimals)
            else:
                # 使用 start, end, 和 default 值来确定最大小数位数
                decimal_places = max(
                    len(str(float(start)).split('.')[-1]),
                    len(str(float(end)).split('.')[-1]),
                    len(str(float(default)).split('.')[-1])
                )
        else:
            decimal_places = 0
        
        parameters.append({
            'name': name,
            'type': param_type,
            'start': float(start),
            'end': float(end),
            'default': float(default),
            'space': space,
            'optimize': optimize == 'True',
            'decimal_places': decimal_places
        })
    
    return parameters

def generate_template(parameters, strategy_content):
    template = ""
    template += strategy_content + "\n"
    # template += "\"\"\")\n\n"
    
    # template += "strategy_params = {\n"
    # template += "    'strategy_name': '${strategy_name}',\n"
    
    # for param in parameters:
    #     if param['optimize']:
    #         if param['type'] == 'DecimalParameter':
    #             value = f"{{'{param['name']}': {param['default']:.{param['decimal_places']}f}}}"
    #         else:
    #             value = f"{{'{param['name']}': {int(param['default'])}}}"
            
    #         template += f"    '{param['name']}': {value},\n"
    
    # template += "}\n\n"
    return template

def replace_parameters(content, parameters):
    # 替换类名
    content = re.sub(r'class\s+(\w+)\s*\(IStrategy\):',
                     r'class ${strategy_name}(IStrategy):',
                     content)

    for param in parameters:
        if param['optimize']:
            pattern = rf"{param['name']}\s*=\s*{param['type']}Parameter\([^)]+\)"
            replacement = f"{param['name']} = {param['type']}Parameter({param['start']}, {param['end']}, default=${{{param['name']}}}, space='{param['space']}', optimize=True)"
            content = re.sub(pattern, replacement, content)
    return content

def generate_dynamic_template(strategy_file_path):
    # Read the strategy file
    with open(strategy_file_path, 'r') as file:
        content = file.read()

    # Parse parameters
    params = parse_parameters(content)

    # Replace parameters with placeholders
    modified_content = replace_parameters(content, params)

    # Generate template
    template = generate_template(params, modified_content)

    return template, params

if __name__ == "__main__":
    strategy_file_path = '../user_data/strategies/E0V1E_20231017_1059.py'
    
    template, params = generate_dynamic_template(strategy_file_path)
    
    # print("Generated Template:")
    # print(template)
    
    print("\nParsed Parameters:")
    for param in params:
        print(param)

    # 可选：将生成的模板写入文件
    # with open('generated_template.py', 'w') as file:
    #     file.write(template)

    print("\nTemplate has been generated and saved to 'generated_template.py'")