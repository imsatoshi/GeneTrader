# 使用命令行参数作为路径
directory_path=$1
pattern=$2
echo $directory_path

# 在指定路径下查找包含 '0101' 的文件，然后输出文件名和包含 "Total profit" 的行
for file in $(ls -l $directory_path | grep $2 | awk '{print $NF}'); do
    grep "Total profit" "$directory_path/$file" | sed "s/^/$file: /"
done

