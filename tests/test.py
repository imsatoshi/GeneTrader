"""Utility for renaming strategy classes in generated strategy files."""
import os
import sys
import re
import argparse
from datetime import datetime
from typing import Optional


def rename_strategy_class(file_path: str, output_path: str,
                          new_class_name: str = "GeneStrategy") -> bool:
    """Rename a GeneTrader strategy class and add version method.

    Args:
        file_path: Path to the input strategy file
        output_path: Path to write the modified strategy file
        new_class_name: New name for the strategy class

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: Input file not found: {file_path}")
        return False
    except IOError as e:
        print(f"Error reading file: {e}")
        return False

    timestring = '"' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '"'

    # Use regex to replace the class name and add version method
    pattern = r'class GeneTrader_gen\d+_\d+_\d+\(IStrategy\):'
    new_content = re.sub(
        pattern,
        f'class {new_class_name}(IStrategy):\n    def version(self) -> str:\n        return {timestring}\n',
        content
    )

    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as file:
            file.write(new_content)
        return True
    except IOError as e:
        print(f"Error writing file: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Rename GeneTrader strategy class')
    parser.add_argument('input_file', help='Path to input strategy file')
    parser.add_argument('output_file', help='Path to output strategy file')
    parser.add_argument('--class-name', default='GeneStrategy',
                        help='New class name (default: GeneStrategy)')

    args = parser.parse_args()

    if rename_strategy_class(args.input_file, args.output_file, args.class_name):
        print(f"Successfully renamed strategy class to '{args.class_name}'")
        print(f"Output written to: {args.output_file}")
    else:
        sys.exit(1)