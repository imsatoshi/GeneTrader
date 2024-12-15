Strategy 模板使用教程

以下是如何使用 gen_template.py 生成和定制策略模板的详细教程。

1. 准备工作
确保你的环境中已经安装了所有必要的依赖项。gen_template.py 依赖于 Python 的标准库，因此不需要额外安装第三方包。
2. gen_template.py 文件简介
该脚本的主要功能是从给定的策略文件（例如 E0V1E.py）中解析参数，并自动生成一个新的策略模板。你可以使用这个模板来创建新的策略，或者定制现有的策略。
parse_parameters：解析策略文件中的参数定义（例如 IntParameter, BooleanParameter 等）。
replace_parameters：用解析出的参数动态替换策略文件中的默认参数。
generate_template：生成包含参数占位符的模板文件。
generate_dynamic_template：从指定的策略文件生成完整的模板，支持动态添加 max_open_trades 和 dynamic_timeframes 参数。

3. 如何使用脚本
3.1 运行 gen_template.py 来生成模板
你只需执行 gen_template.py 脚本，它会读取指定的策略文件并根据文件内容自动生成一个新的模板文件。
3.2 使用方法
python strategy/gen_template.py
在脚本中，默认会读取位于 ./candidates/E0V1E.py 的策略文件。你可以通过修改 strategy_file_path 变量来指定你自己的策略文件路径。

3.3 调整模板生成选项
generate_dynamic_template 函数接受两个可选参数：add_max_open_trades 和 add_dynamic_timeframes。它们控制是否在生成的模板中添加 max_open_trades 和 dynamic_timeframes 参数。
add_max_open_trades：默认值为 True，表示在生成的模板中添加 max_open_trades 参数。
add_dynamic_timeframes：默认值为 False，表示是否在模板中添加 dynamic_timeframes 参数。
如果你希望在模板中添加这些参数，可以按以下方式调用：
template, params = generate_dynamic_template(strategy_file_path, add_max_open_trades=True, add_dynamic_timeframes=True)
3.4 输出结果
脚本执行后，生成的模板将输出在终端，并保存为 generated_template.py 文件。所有解析出的参数将以字典的形式打印出来，并展示给用户。

```
Parsed Parameters:
{'name': 'param1', 'type': 'Int', 'optimize': True, 'space': 'buy', 'start': 1.0, 'end': 10.0, 'default': 5.0, 'decimal_places': 0}
{'name': 'param2', 'type': 'Boolean', 'optimize': True, 'space': 'sell', 'default': True}
...
Template has been generated and saved to 'generated_template.py'
```


4. 模板文件示例
当你生成模板时，它会替换掉所有策略文件中的参数，生成一个包含动态参数占位符的模板。例如，以下是一个简单的 generated_template.py 示例：

```
class StrategyTemplate(IStrategy):
    # Hyperopt parameters
    pHSL = DecimalParameter(-0.200, -0.040, default=-0.10, decimals=3, space='sell', optimize=True)
    pPF_1 = DecimalParameter(0.008, 0.020, default=0.016, decimals=3, space='sell', optimize=True)
    pSL_1 = DecimalParameter(0.008, 0.020, default=0.011, decimals=3, space='sell', optimize=True)
    pPF_2 = DecimalParameter(0.040, 0.100, default=0.070, decimals=3, space='sell', optimize=True)
    pSL_2 = DecimalParameter(0.020, 0.070, default=0.030, decimals=3, space='sell', optimize=True)

    buy_rsi_fast_32 = IntParameter(20, 70, default=40, space='buy', optimize=True)
    buy_rsi_32 = IntParameter(15, 50, default=42, space='buy', optimize=True)
    buy_sma15_32 = DecimalParameter(0.900, 1, default=0.973, decimals=3, space='buy', optimize=True)
    buy_cti_32 = DecimalParameter(-1, 1, default=0.69, decimals=2, space='buy', optimize=True)

    sell_fastx = IntParameter(50, 100, default=84, space='sell', optimize=True)
    sell_loss_cci = IntParameter(0, 600, default=100, space='sell', optimize=True)
    sell_loss_cci_profit = DecimalParameter(-0.15, 0, default=-0.05, decimals=2, space='sell', optimize=True)
    # Other parameters follow...
```

5. 自定义模板
你可以修改生成的模板，调整各个参数的范围、默认值等，满足你的策略需求。例如：
修改 max_open_trades 和 dynamic_timeframes 的默认值和范围。
修改或删除某些参数，以便与不同的策略逻辑匹配。
6. 注意事项
参数类型：IntParameter, BooleanParameter, CategoricalParameter 等这些参数类型需要与你的策略逻辑一致。如果你在模板中看到某些不需要的参数类型，可以手动删除或修改。
优化参数：optimize=True 表示该参数会在策略优化过程中进行调优。根据你的需求，可以选择是否保留这些优化参数。
7. 结论
通过这个脚本，可以高效地从现有的策略中提取参数，并根据需求自动生成策略模板。它简化了参数的管理和配置过程，并允许你快速定制和优化策略。如果你需要为多个策略文件生成模板，可以多次运行该脚本，指定不同的策略文件路径。