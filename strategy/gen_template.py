import re

def parse_parameters(file_content):
    parameters = []
    pattern = r'(\w+)\s*=\s*(Int|Decimal|Boolean|Categorical)Parameter\(((?:[^()]+|\([^()]*\))*)\)'
    matches = re.findall(pattern, file_content)
    
    for match in matches:
        name, param_type, args = match
        args_list = [arg.strip() for arg in args.split(',')]
        
        param = {
            'name': name,
            'type': param_type,
            'optimize': 'optimize=True' in args,
            'space': next((arg.split('=')[1].strip("'\"") for arg in args_list if arg.startswith('space=')), ''),
            'load': 'load=True' in args
        }
        
        if param_type in ['Int', 'Decimal']:
            param.update({
                'start': float(args_list[0]),
                'end': float(args_list[1]),
                'default': float(next((arg.split('=')[1] for arg in args_list if arg.startswith('default=')), 0)),
                'decimal_places': int(next((arg.split('=')[1] for arg in args_list if arg.startswith('decimals=')), 0))
            })
        elif param_type == 'Boolean':
            param['default'] = 'default=True' in args
        elif param_type == 'Categorical':
            # 使用正则表达式提取选项列表
            options_match = re.search(r'\[(.*?)\]', args)
            if options_match:
                options_str = options_match.group(1)
                # 分割选项并处理
                options = []
                for opt in options_str.split(','):
                    opt = opt.strip()
                    # 如果是布尔值，保持为布尔值
                    if opt in ('True', 'False'):
                        options.append(opt == 'True')
                    else:
                        # 其他情况去除引号
                        options.append(opt.strip("'\""))
                param['options'] = options
            
            # 提取默认值
            default_match = re.search(r"default=([^,\)]+)", args)
            if default_match:
                default_value = default_match.group(1).strip()
                # 如果默认值是布尔值，转换为布尔类型
                if default_value in ('True', 'False'):
                    param['default'] = default_value == 'True'
                else:
                    param['default'] = default_value.strip("'\"")
            else:
                param['default'] = param['options'][0] if param.get('options') else None
        
        parameters.append(param)
    
    return parameters

def generate_template(parameters, strategy_content):
    template = ""
    template += strategy_content + "\n"
    return template

def replace_parameters(content, parameters):
    # Replace class name
    content = re.sub(r'class\s+(\w+)\s*\(IStrategy\):',
                     r'class ${strategy_name}(IStrategy):',
                     content)

    for param in parameters:
        if param['optimize']:
            if param['type'] in ['Int', 'Decimal']:
                pattern = rf"{param['name']}\s*=\s*{param['type']}Parameter\([^)]+\)"
                replacement = f"{param['name']} = {param['type']}Parameter({param['start']}, {param['end']}, default=${{{param['name']}}}, space='{param['space']}', optimize=True)"
            elif param['type'] == 'Boolean':
                pattern = rf"{param['name']}\s*=\s*BooleanParameter\([^)]+\)"
                replacement = f"{param['name']} = BooleanParameter(default=${{{param['name']}}}, space='{param['space']}', optimize=True)"
            elif param['type'] == 'Categorical':
                pattern = rf"{param['name']}\s*=\s*CategoricalParameter\([^)]+\)"
                options_str = [str(opt) if isinstance(opt, bool) else f"'{opt}'" for opt in param['options']]
                options_formatted = f"[{', '.join(options_str)}]"
                # Add quotes around the default value placeholder for string options
                if all(isinstance(opt, str) for opt in param['options']):
                    replacement = f"{param['name']} = CategoricalParameter({options_formatted}, default='${{{param['name']}}}', space='{param['space']}', optimize=True)"
                else:
                    replacement = f"{param['name']} = CategoricalParameter({options_formatted}, default=${{{param['name']}}}, space='{param['space']}', optimize=True)"
            content = re.sub(pattern, replacement, content)
    return content

def generate_dynamic_template(strategy_file_path, add_max_open_trades=True, add_dynamic_timeframes=False):
    # Read the strategy file
    with open(strategy_file_path, 'r') as file:
        content = file.read()

    # Parse parameters
    params = parse_parameters(content)

    if add_max_open_trades:
        # Add max_open_trades parameter
        params.append({
            'name': 'max_open_trades',
            'type': 'Int',
            'start': 1.0,
            'end': 6.0,
            'default': 3.0,  # You can change this default value if needed
            'space': 'buy',
            'optimize': True,
            'decimal_places': 0
        })
    
    if add_dynamic_timeframes:
        # Add dynamic_timeframes parameter
        params.append({
            'name': 'dynamic_timeframes',
            'type': 'Int',
            'start': 0,
            'end': 7,
            'default': 1,
            'space': 'buy',
            'optimize': True
        })

    # Replace parameters with placeholders
    modified_content = replace_parameters(content, params)

    # Generate template
    template = generate_template(params, modified_content)

    return template, params

if __name__ == "__main__":
    strategy_file_path = './candidates/E0V1E_1105.py'
    
    template, params = generate_dynamic_template(strategy_file_path)
        
    print("\nParsed Parameters:")
    for param in params:
        # if param['type'] == 'Categorical':
        # print(param['name'], param['options'], param['default'])
        print(param)
    print("\nTemplate has been generated and saved to 'generated_template.py'")
    # print(len(params))
    # print("abc")
    # print(template)