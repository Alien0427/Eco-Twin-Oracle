"""Quick smoke-test verifying all type fixes are runtime-safe."""
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import ast, numpy as np

# 1. Parse both edited files
for fname in ['analytics_engine.py', 'state_machine.py']:
    with open(fname, encoding='utf-8') as f:
        src = f.read()
    try:
        ast.parse(src)
        print(f'AST OK: {fname}')
    except SyntaxError as e:
        print(f'SYNTAX ERROR in {fname}: {e}')

# 2. Import and exercise the changed classes
from state_machine import DFAStateMachine, ManufacturingPhase, PhysicalViolationError

dfa = DFAStateMachine()
assert dfa.current_state == ManufacturingPhase.PREPARATION

# IntEnum comparison
assert ManufacturingPhase.GRANULATION > ManufacturingPhase.PREPARATION
assert ManufacturingPhase.COMPRESSION > ManufacturingPhase.DRYING
print('IntEnum comparison: OK')

# validate_prescription: parameter native to GRANULATION blocked in COMPRESSION
dfa.transition_to(ManufacturingPhase.GRANULATION)
dfa.transition_to(ManufacturingPhase.DRYING)
dfa.transition_to(ManufacturingPhase.MILLING)
dfa.transition_to(ManufacturingPhase.BLENDING)
dfa.transition_to(ManufacturingPhase.COMPRESSION)
try:
    dfa.validate_prescription(ManufacturingPhase.COMPRESSION, "Binder_Amount")
    print('ERROR: should have raised PhysicalViolationError')
except PhysicalViolationError as e:
    print(f'DFA guardrail: OK — {e}')

# 3. Exercise KohonenSOM sentinel init
from analytics_engine import KohonenSOM, LVQClassifier, FEATURE_COLUMNS

som = KohonenSOM(grid_h=5, grid_w=5, n_iterations=10, seed=0)
assert som._mean.shape == (len(FEATURE_COLUMNS),), "SOM _mean wrong shape"
assert som._std.shape  == (len(FEATURE_COLUMNS),), "SOM _std wrong shape"
assert np.allclose(som._mean, 0.0), "SOM _mean should be zeros before fit"
assert np.allclose(som._std,  1.0), "SOM _std should be ones before fit"
print('KohonenSOM sentinel arrays: OK')

# 4. Train and verify real values
rng = np.random.default_rng(0)
X = rng.uniform(0, 1, (50, len(FEATURE_COLUMNS)))
som.fit(X)
assert som.is_trained
assert not np.allclose(som._mean, 0.0), "mean should update after fit"
print('KohonenSOM fit + sentinel update: OK')

# 5. Exercise LVQClassifier sentinel init
lvq = LVQClassifier(n_prototypes_per_class=2, n_epochs=20)
assert lvq.codebook.shape[0] == 0, "codebook should be empty before fit"
assert lvq._mean.shape == (len(FEATURE_COLUMNS),)
print('LVQClassifier sentinel arrays: OK')

y = np.array(['Normal'] * 30 + ['Thermal Drift'] * 20)
lvq.fit(X, y)
label = lvq.predict(X[0])
assert isinstance(label, str)
print(f'LVQClassifier predict: OK — got {label!r}')

# 6. np.round returns float correctly
val = np.float64(3.14159265)
result = float(np.round(val, 4))
assert isinstance(result, float)
assert result == 3.1416
print(f'np.round float cast: OK — {result}')

print('\nAll runtime checks passed. ✅')
