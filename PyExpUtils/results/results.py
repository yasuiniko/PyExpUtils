import numpy as np
from PyExpUtils.results.paths import listResultsPaths
from PyExpUtils.utils.arrays import first
from PyExpUtils.utils.dict import equal

"""doc
The `Result` objects allows performing operations over results lazily so that many file system calls can be avoided.
This is extremely useful when doing large parameter sweeps and plotting over slices of parameters.
The object stores some metadata about the result that can be inferred from the experiment description without needing to open the result file.

```python
results = loadResults(exp, 'returns.npy') # -> gives an iterator over Result objects

for result in results:
    print(result.path) # -> 'results/MountainCar-v0/SARSA/alpha-1.0_lambda-1.0/returns.npy'
    print(result)

# only load results from disk where alpha > 0.2
results = filter(lambda res: res.params['alpha'] > 0.2, results)
for result in results:
    plot(result.load())

```
"""
class Result:
    def __init__(self, path, exp, idx):
        self.path = path
        self.exp = exp
        self.idx = idx
        self.params = exp.getPermutation(idx)[exp._getKeys()[0]]
        self._data = None

    def _lazyLoad(self):
        if self._data is not None:
            return self._data

        try:
            self._data = np.load(self.path, allow_pickle=True)
            return self._data
        except:
            print('Result not found :: ' + self.path)
            return (np.NaN, np.NaN, 0)

    """doc
    Takes a function that manipulates the result data.
    For example: useful for truncating data or looking at only final performance, etc.

    ```python
    def getFirstNSteps(results, n):
        for result in results:
            yield result.reducer(lambda data: data[0:n])

    results = loadResults(exp, 'returns.npy')
    results = getFirstNSteps(results, 100)
    ```
    """
    def reducer(self, lm):
        view = ResultView(self)
        view.reducer(lm)
        return view

    """doc
    Load the result from disk.
    The contents of the results file are cached, so as long as this result file is accessible (e.g. not garbage collected) you will only hit the filesystem once.
    This is important for distributed filesystems (like on computecanada) where filesystem calls are extremely expensive.

    Note that if the result does not exist (e.g. compute canada job timed out), then an error message will be printed but no exception will be thrown.
    This way plotting code can still continue to run with partial results.
    """
    def load(self):
        return self._lazyLoad()

"""doc
A "window" over a `Result` object that allows changing the type of reducer on the object while still referencing the same memory cache.
Useful for applying different views at the same results file without needing to load multiple copies of the result into memory or making multiple filesystem calls.
Returned from the `Result.reducer` method.
Maintains same API as a `Result` object and can be used interchangeably.

```python
results = loadResults(exp, 'returns.npy')
for result in results:
    view = result.reducer(lambda m: m.mean())
    view2 = result.reducer(lambda m: m.std())
```
"""
class ResultView:
    def __init__(self, result):
        self._result = result
        self._reducer = lambda m: m

    def reducer(self, lm):
        self._reducer = lm
        return self

    def load(self):
        return self._reducer(self._result.load())

"""doc
Utility function for sorting results into bins based on values of a metaParameter.
Does not load results from disk.

```python
results = loadResults(exp, 'returns.npy')
bins = splitOverParameter(results, 'alpha')
print(bins) # -> { 1.0: [Result, Result, ...], 0.5: [Result, Result, ...], 0.25: [Result, Result, ...], ...}
```
"""
def splitOverParameter(results, param):
    parts = {}
    for r in results:
        param_value = r.params[param]

        if param_value not in parts:
            parts[param_value] = []

        parts[param_value].append(r)

    return parts

"""doc
Utility function for sorting results by fixing all parameters except one, and returning a list of results for all other values of the other parameter.
Takes the list of results to consider, a result whose parameter values you want to match, and the name of the parameter you want to sweep over.
Does not load results from disk.

```python
results = loadResults(exp, 'returns.npy')
result = next(results)
slice = sliceOverParameter(results, result, 'lambda')

print(slice) # => { 1.0: [Result, Result, ...], 0.99: [Result, Result, ...], 0.98: [Result, Result], ....}
```
"""
def sliceOverParameter(results, slicer, param):
    parts = splitOverParameter(results, param)

    sl = {}
    for k in parts:
        sl[k] = find(parts[k], slicer, ignore=[param])

    return sl

"""doc
Returns the best result over a list of results.
Can defined "best" based on the `comparator` option; defaults to returning smallest result (e.g. smallest error).
Can also find best result over a range of a learning curve by specifying the last n steps with `steps=n` or the last p percent of steps with `percent=p`; defaults to returning mean over whole learning curve.
**Requires loading all results in list from disk.**

```python
results = loadResults(exp, 'returns.npy')

# get the largest return over the last 10% of steps
best = getBest(results, percent=0.1, comparator=lambda a, b: a > b)
print(best.params) # -> { 'alpha': 1.0, 'lambda': 0.99 }

results = loadResults(exp, 'rmsve.npy')

# get the lowest rmsve over all steps
best = getBest(results)
print(best.params) # -> { 'alpha': 0.25, 'lambda': 1.0 }
```
"""
def getBest(results, steps=None, percent=1.0, comparator=lambda a, b: a < b):
    low = first(results)
    if steps is None:
        steps = low.load().shape[0]

    steps = int(steps * percent)

    for r in results:
        a = r.load()
        b = low.load()
        am = np.mean(a[0 - steps:])
        bm = np.mean(b[0 - steps:])
        if np.isnan(bm) or comparator(am, bm):
            low = r

    return low

"""doc
Find a specific result based on the metaParameters of another result.
Can optionally specify a list of parameters to ignore using for example `ignore=['alpha']`.
Will return the first result that matches.
Does not require loading results from disk.

```python
results = loadResults(exp, 'returns.npy')

result = next(results)
match = find(results, result, ignore=['lambda'])

print(result.params) # -> { 'alpha': 1.0, 'lambda': 1.0 }
print(match.params) # -> { 'alpha': 1.0, 'lambda': 0.98 }
```
"""
def find(stream, other, ignore=[]):
    params = other.params
    for res in stream:
        if equal(params, res.params, ignore):
            return res

"""doc
Utility method for filtering results based on the value of a particular parameter.
If the listed parameter does not exist for some of the results (e.g. when comparing TD vs. GTD where TD does not have the second stepsize param), then those results will match True for the comparator.
Does not require loading results from disk.

```python
results = loadResults(exp, 'returns.npy')
results = whereParameterEquals(results, 'alpha', 0.25)

for res in results:
    print(res.params) # -> { 'alpha': 0.25, 'lambda': ... }
```
"""
def whereParameterEquals(results, param, value):
    return filter(lambda r: r.params.get(param, value) == value, results)

"""doc
Utility method for filtering results based on the value of a particular parameter.
If the listed parameter does not exist for some of the results (e.g. when comparing TD vs. GTD where TD does not have the second stepsize param), then those results will match True for the comparator.
Does not require loading results from disk.

```python
results = loadResults(exp, 'returns.npy')
results = whereParameterGreaterEq(results, 'alpha', 0.25)

for res in results:
    print(res.params) # -> { 'alpha': 0.25, 'lambda': ... }, { 'alpha': 0.5, 'lambda': ... }, ...
```
"""
def whereParameterGreaterEq(results, param, value):
    return filter(lambda r: r.params.get(param, value) >= value, results)

"""doc
Returns an iterator over all results that are expected to exist given a particular experiment.
Takes the `ExperimentDescription` and the name of the result file.
Does not load results from disk.

```python
results = loadResults(exp, 'returns.npy')

for result in results:
    print(result) # -> `<Result>`
```
"""
def loadResults(exp, result_file):
    for i, path in enumerate(listResultsPaths(exp)):
        summary_path = path + '/' + result_file
        yield Result(summary_path, exp, i)
