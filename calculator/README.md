# Calculator

Run `python main.py "3 + 5 * 2"` from this directory. Successful calculations print
JSON; invalid expressions print an error to stderr and return exit status 1.

Use whitespace-separated numbers and the binary operators `+`, `-`, `*`, `/`.
Multiplication and division take precedence; equal-precedence operators evaluate
left to right. Signed numbers and scientific notation are supported (`-3 + 1e2`).
Parentheses, unspaced expressions such as `3+5`, and non-finite numbers are not
supported. Arithmetic uses floating-point numbers.

Run `python -B tests.py` for the calculator unit tests.
