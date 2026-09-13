# Numerical replay across environments

The first cloud run of v0.2 failed at E2 training replay on Python 3.11 and 3.12: the audit compared floating-point model dictionaries using exact equality. Local validation had reused the original dependency environment.

Numerical replay now uses relative tolerance 1e-10 and absolute tolerance 1e-12 for finite floats in model parameters, predictions, prediction metrics, and E4 derived numerical outputs. Keys, list order, IDs, integers, and strings must still match exactly. E2/E3 selected memory sets and budgets retain their exact checks. Artifact hashes, frozen-model identity against the saved model, and source provenance are not tolerance-based. Nonfinite values fail.

The frozen outputs are unchanged. The release source registry explicitly records the revised audit implementation. Passing this check supports numerical reproducibility within the stated bound; it does not establish bitwise equality across BLAS implementations.
