## results/paths
### listResultsPaths
Takes an experiment description and returns an iterable of each result path for each meta-parameter permutation and each run.
```python
for path in listResultsPaths(exp, runs = 10):
    print(path) # results/overfit/ann/fashion_mnist/alpha-0.01_epsilon-0.01/0
```

### listMissingResults
Takes an experiment description and returns an iterable of all of the missing results.
This is extremely useful for running experiments on a cluster where jobs may time out, or nodes may fail due to environmental issues.
This allows rerunning of only the failed experiments.
```python
for path in listMissingResults(exp, runs=10):
    print(path) # results/overfit/ann/fashion_mnist/alpha-0.02_epsilon-0.01/8
```
