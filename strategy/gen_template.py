"""Strategy template generation for GeneTrader.

This module parses Freqtrade strategy files to extract parameter definitions
and generates templates with placeholder variables for the genetic algorithm.
"""
import re
import argparse
from typing import List, Dict, Any, Tuple, Optional, Union


def parse_parameters(file_content: str) -> List[Dict[str, Any]]:
    """Parse parameter definitions from a Freqtrade strategy file.

    Extracts IntParameter, DecimalParameter, BooleanParameter, and
    CategoricalParameter definitions from the strategy source code.

    Args:
        file_content: The full content of the strategy file as a string

    Returns:
        List of parameter dictionaries, each containing:
        - name: Parameter variable name
        - type: Parameter type ('Int', 'Decimal', 'Boolean', 'Categorical')
        - optimize: Whether optimization is enabled
        - space: The hyperopt space ('buy', 'sell', etc.)
        - load: Whether the parameter should be loaded
        - Additional type-specific fields (start, end, default, options, etc.)
    """
    parameters = []
    pattern = r'(\w+)\s*=\s*(Int|Decimal|Boolean|Categorical)Parameter\(((?:[^()]+|\([^()]*\))*)\)'
    matches = re.findall(pattern, file_content)

    for match in matches:
        name, param_type, args = match
        args_list = [arg.strip() for arg in args.split(',')]

        param: Dict[str, Any] = {
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
            # Extract options list using regex
            options_match = re.search(r'\[(.*?)\]', args)
            if options_match:
                options_str = options_match.group(1)
                options: List[Union[bool, str]] = []
                for opt in options_str.split(','):
                    opt = opt.strip()
                    # Keep boolean values as booleans
                    if opt in ('True', 'False'):
                        options.append(opt == 'True')
                    else:
                        # Remove quotes for string options
                        options.append(opt.strip("'\""))
                param['options'] = options

            # Extract default value
            default_match = re.search(r"default=([^,\)]+)", args)
            if default_match:
                default_value = default_match.group(1).strip()
                if default_value in ('True', 'False'):
                    param['default'] = default_value == 'True'
                else:
                    param['default'] = default_value.strip("'\"")
            else:
                param['default'] = param['options'][0] if param.get('options') else None

        parameters.append(param)

    return parameters

def generate_template(parameters: List[Dict[str, Any]], strategy_content: str) -> str:
    """Generate a template string from strategy content.

    Args:
        parameters: List of parsed parameter dictionaries
        strategy_content: Modified strategy content with placeholders

    Returns:
        Complete template string
    """
    return strategy_content + "\n"


def replace_parameters(content: str, parameters: List[Dict[str, Any]]) -> str:
    """Replace parameter definitions with placeholder variables.

    Transforms parameter definitions in the strategy content to use
    ${parameter_name} placeholders that can be filled by the template engine.

    Args:
        content: Original strategy file content
        parameters: List of parsed parameter dictionaries

    Returns:
        Modified content with placeholder variables
    """
    # Replace class name with placeholder
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


def generate_dynamic_template(strategy_file_path: str,
                               add_max_open_trades: bool = True,
                               add_dynamic_timeframes: bool = False) -> Tuple[str, List[Dict[str, Any]]]:
    """Generate a dynamic template from a Freqtrade strategy file.

    Reads a strategy file, extracts all optimizable parameters, and generates
    a template with placeholder variables for the genetic algorithm.

    Args:
        strategy_file_path: Path to the strategy Python file
        add_max_open_trades: Whether to add max_open_trades as an optimizable parameter
        add_dynamic_timeframes: Whether to add dynamic_timeframes as an optimizable parameter

    Returns:
        Tuple of (template_string, parameters_list)

    Raises:
        FileNotFoundError: If the strategy file doesn't exist
        IOError: If the strategy file cannot be read
    """
    with open(strategy_file_path, 'r') as file:
        content = file.read()

    # Parse parameters from strategy file
    params = parse_parameters(content)

    if add_max_open_trades:
        params.append({
            'name': 'max_open_trades',
            'type': 'Int',
            'start': 2.0,
            'end': 10.0,
            'default': 6.0,
            'space': 'buy',
            'optimize': True,
            'decimal_places': 0
        })

    if add_dynamic_timeframes:
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
    parser = argparse.ArgumentParser(description='Generate dynamic template from strategy file')
    parser.add_argument('strategy_file', nargs='?', default='./candidates/E0V1E_1105.py',
                        help='Path to strategy file')
    parser.add_argument('--no-max-trades', action='store_true',
                        help='Do not add max_open_trades parameter')
    parser.add_argument('--add-timeframes', action='store_true',
                        help='Add dynamic_timeframes parameter')

    args = parser.parse_args()

    try:
        template, params = generate_dynamic_template(
            args.strategy_file,
            add_max_open_trades=not args.no_max_trades,
            add_dynamic_timeframes=args.add_timeframes
        )

        print(f"\nParsed {len(params)} Parameters:")
        for param in params:
            print(f"  - {param['name']}: {param['type']}")
        print(f"\nTemplate generated from: {args.strategy_file}")
    except FileNotFoundError:
        print(f"Error: Strategy file not found: {args.strategy_file}")
        exit(1)