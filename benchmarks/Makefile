.PHONY: bench bench-decode bench-baseline

bench:  ## WebSocket messages/second, compared against the previous local run
	poetry run python -m benchmarks ws

bench-decode:  ## Decode costs, the denominator for the ws numbers
	poetry run python -m benchmarks decode

bench-baseline:  ## Record the current commit as a reference series: make bench-baseline NAME=main
	@test -n "$(NAME)" || { echo "NAME is required, e.g. make bench-baseline NAME=main" >&2; exit 1; }
	poetry run python -m benchmarks ws --save-baseline $(NAME)
	poetry run python -m benchmarks decode --save-baseline $(NAME)
