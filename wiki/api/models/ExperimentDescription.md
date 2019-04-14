## models/ExperimentDescription
De-serializes the experiment description json files.
Holds a few utility functions for working with these datafiles.

This should be extended by a subclass that knows the exact fields in your datafile.
This class makes no strong assumptions about the datafile structure, though defaults to assuming that the meta-parameters are contained in a field called `metaParameters`.

### getPermutation
Gets the parameter permutation for a single index.
```python
with open('ann.json', 'r') as f:
    d = json.load(f)
exp = ExperimentDescription(d)
permutation = exp.getPermutation(0)
# permutation is a raw dictionary exactly the same as `d` above
# except `metaParameters` has been replaced with single values (instead of sweeps)
```

### permutations
Gets the number of possible permutations for given datafile.
```python
with open('ann.json', 'r') as f:
    d = json.load(f)

exp = ExperimentDescription(d)
num_permutations = exp.permutations()
```

### getRun
Returns the run number for a given index.
This is based on the number of permutations and the index value.
```python
run_num = exp.getRun(idx=22)
# if there are 10 permutations, this would return run_num=3
```

### interpolateSavePath
Takes a save path "key" and builds a path based on experiment meta-data.
```python
# values in {} will be replaced based on experiment description
path_key = 'results/{name}/{algorithm}/{dataset}/{params}/{run}'
save_path = exp.interpolateSavePath(idx=0)

print(save_path) # results/overfit/ann/fashion_mnist/alpha-0.01_epsilon-0.01/0
```
