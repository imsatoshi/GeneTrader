
for i in {1..20}; do
    # echo "Generation $i"
    cat "generation_${i}.txt" | grep "GeneTrader_gen" | grep USDT
done
