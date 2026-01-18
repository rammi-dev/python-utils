"""Command-line interface for YAML DAG validation.

This module provides a CLI for validating DAG Factory YAML configurations
during deployment or development.

Usage:
    python -m dlh_airflow_common.validation.cli /path/to/dags
    python -m dlh_airflow_common.validation.cli /path/to/single_dag.yaml
"""

import argparse
import sys
from pathlib import Path

from dlh_airflow_common.validation.yaml_validator import (
    ValidationResult,
    YamlDagValidator,
)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, 1 for validation failures)
    """
    parser = argparse.ArgumentParser(
        description="Validate DAG Factory YAML configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Validate all YAML files in a directory:
    %(prog)s /path/to/dags/

  Validate a single file:
    %(prog)s /path/to/dag.yaml

  Validate with verbose output:
    %(prog)s -v /path/to/dags/

  Non-recursive validation:
    %(prog)s --no-recursive /path/to/dags/
        """,
    )

    parser.add_argument(
        "path",
        type=Path,
        help="Path to YAML file or directory to validate",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed output including warnings",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't search directories recursively",
    )

    parser.add_argument(
        "--pattern",
        default="*.yaml",
        help="Glob pattern for YAML files (default: *.yaml)",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )

    args = parser.parse_args(argv)

    validator = YamlDagValidator()
    results: list[ValidationResult] = []

    path = args.path

    if path.is_file():
        results.append(validator.validate_file(path))
    elif path.is_dir():
        results.extend(
            validator.validate_directory(
                path,
                pattern=args.pattern,
                recursive=not args.no_recursive,
            )
        )
    else:
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        return 1

    # Process results
    total_files = len(results)
    valid_files = sum(1 for r in results if r.is_valid)
    invalid_files = total_files - valid_files
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)

    # Print results
    for result in results:
        if not result.is_valid or args.verbose:
            print(result)
            print()

    # Print summary
    print("-" * 60)
    print("Validation Summary:")
    print(f"  Total files:   {total_files}")
    print(f"  Valid:         {valid_files}")
    print(f"  Invalid:       {invalid_files}")
    print(f"  Total errors:  {total_errors}")
    print(f"  Total warnings: {total_warnings}")
    print("-" * 60)

    # Determine exit code
    if invalid_files > 0:
        print("\nValidation FAILED")
        return 1

    if args.strict and total_warnings > 0:
        print("\nValidation FAILED (strict mode: warnings treated as errors)")
        return 1

    print("\nValidation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
