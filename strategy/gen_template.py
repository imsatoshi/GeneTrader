import re

def parse_parameters(file_content):
    parameters = []
    pattern = r'(\w+)\s*=\s*(Int|Decimal|Boolean)Parameter\(((?:[^()]+|\([^()]*\))*)\)'
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
        
        parameters.append(param)
    
    return parameters

def generate_template(parameters, strategy_content):
    template = ""
    template += strategy_content + "\n"
    return template

def replace_parameters(content, parameters):
    # 替换类名
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
            content = re.sub(pattern, replacement, content)
    return content

def generate_dynamic_template(strategy_file_path):
    # Read the strategy file
    with open(strategy_file_path, 'r') as file:
        content = file.read()

    # Parse parameters
    params = parse_parameters(content)

    # Add max_open_trades parameter
    params.append({
        'name': 'max_open_trades',
        'type': 'Int',
        'start': 1.0,
        'end': 6.0,
        'default': 2.0,  # You can change this default value if needed
        'space': 'buy',
        'optimize': True,
        'decimal_places': 0
    })

    # Replace parameters with placeholders
    modified_content = replace_parameters(content, params)

    # Generate template
    template = generate_template(params, modified_content)

    return template, params

if __name__ == "__main__":
    strategy_file_path = './E0V1E.py'
    
    template, params = generate_dynamic_template(strategy_file_path)
        
    print("\nParsed Parameters:")
    for param in params:
        print(param)

    print("\nTemplate has been generated and saved to 'generated_template.py'")
    print(len(params))
