
for i in {1..20}; do
    # echo "Generation $i"
    cat "generations/generation_${i}.txt" | grep "GeneTrader_gen"
done
