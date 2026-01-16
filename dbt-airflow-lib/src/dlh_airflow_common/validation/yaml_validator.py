"""YAML DAG configuration validator for DAG Factory.

This module provides validation utilities for YAML-based DAG configurations
used with dag-factory. It validates both YAML syntax and DAG structure.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        is_valid: Whether the validation passed
        file_path: Path to the validated file
        errors: List of error messages
        warnings: List of warning messages
    """

    is_valid: bool
    file_path: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Return a formatted string representation."""
        status = "VALID" if self.is_valid else "INVALID"
        lines = [f"{self.file_path}: {status}"]

        for error in self.errors:
            lines.append(f"  ERROR: {error}")

        for warning in self.warnings:
            lines.append(f"  WARNING: {warning}")

        return "\n".join(lines)


class YamlDagValidator:
    """Validator for DAG Factory YAML configurations.

    This class validates YAML files against DAG Factory schema requirements,
    checking for proper syntax, required fields, and valid task configurations.

    Example:
        >>> validator = YamlDagValidator()
        >>> result = validator.validate_file("/path/to/dag.yaml")
        >>> if not result.is_valid:
        ...     for error in result.errors:
        ...         print(f"Error: {error}")
    """

    # Required fields for DAG configuration
    REQUIRED_DAG_FIELDS: Set[str] = {"default_args", "schedule"}

    # Required fields in default_args
    REQUIRED_DEFAULT_ARGS: Set[str] = {"owner", "start_date"}

    # Required fields for task configuration
    REQUIRED_TASK_FIELDS: Set[str] = {"operator"}

    # Valid task dependency keys
    DEPENDENCY_KEYS: Set[str] = {"dependencies", "depends_on"}

    def __init__(
        self,
        required_dag_fields: Optional[Set[str]] = None,
        required_default_args: Optional[Set[str]] = None,
        required_task_fields: Optional[Set[str]] = None,
    ) -> None:
        """Initialize the validator with optional custom requirements.

        Args:
            required_dag_fields: Override default required DAG fields
            required_default_args: Override default required default_args fields
            required_task_fields: Override default required task fields
        """
        self.required_dag_fields = (
            required_dag_fields if required_dag_fields is not None else self.REQUIRED_DAG_FIELDS
        )
        self.required_default_args = (
            required_default_args
            if required_default_args is not None
            else self.REQUIRED_DEFAULT_ARGS
        )
        self.required_task_fields = (
            required_task_fields if required_task_fields is not None else self.REQUIRED_TASK_FIELDS
        )

    def validate_yaml_syntax(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate YAML syntax of a file.

        Args:
            file_path: Path to the YAML file

        Returns:
            ValidationResult with syntax validation status
        """
        file_path = Path(file_path)
        errors: List[str] = []

        try:
            with open(file_path, encoding="utf-8") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {e}")
        except FileNotFoundError:
            errors.append(f"File not found: {file_path}")
        except PermissionError:
            errors.append(f"Permission denied: {file_path}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            file_path=str(file_path),
            errors=errors,
        )

    def validate_dag_structure(
        self, config: Dict[str, Any], file_path: str = "<unknown>"
    ) -> ValidationResult:
        """Validate DAG structure and required fields.

        Args:
            config: Parsed YAML configuration dictionary
            file_path: Path to the file (for error messages)

        Returns:
            ValidationResult with structure validation status
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return ValidationResult(
                is_valid=False, file_path=file_path, errors=errors, warnings=warnings
            )

        # Check for at least one DAG definition
        dag_configs = {k: v for k, v in config.items() if isinstance(v, dict) and k != "default"}

        if not dag_configs:
            errors.append("No DAG configurations found")
            return ValidationResult(
                is_valid=False, file_path=file_path, errors=errors, warnings=warnings
            )

        # Validate each DAG configuration
        for dag_name, dag_config in dag_configs.items():
            dag_errors, dag_warnings = self._validate_single_dag(dag_name, dag_config)
            errors.extend(dag_errors)
            warnings.extend(dag_warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            file_path=file_path,
            errors=errors,
            warnings=warnings,
        )

    def _validate_single_dag(
        self, dag_name: str, dag_config: Dict[str, Any]
    ) -> tuple[List[str], List[str]]:
        """Validate a single DAG configuration.

        Args:
            dag_name: Name of the DAG
            dag_config: DAG configuration dictionary

        Returns:
            Tuple of (errors, warnings) lists
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(dag_config, dict):
            errors.append(f"DAG '{dag_name}': Configuration must be a dictionary")
            return errors, warnings

        # Check required DAG fields
        for required_field in self.required_dag_fields:
            if required_field not in dag_config:
                errors.append(f"DAG '{dag_name}': Missing required field '{required_field}'")

        # Validate default_args if present
        if "default_args" in dag_config:
            default_args = dag_config["default_args"]
            if isinstance(default_args, dict):
                for required_field in self.required_default_args:
                    if required_field not in default_args:
                        errors.append(
                            f"DAG '{dag_name}': Missing required default_args field '{required_field}'"
                        )
            else:
                errors.append(f"DAG '{dag_name}': default_args must be a dictionary")

        # Validate tasks if present
        tasks = dag_config.get("tasks", {})
        if tasks:
            if not isinstance(tasks, dict):
                errors.append(f"DAG '{dag_name}': 'tasks' must be a dictionary")
            else:
                task_errors, task_warnings = self._validate_tasks(dag_name, tasks)
                errors.extend(task_errors)
                warnings.extend(task_warnings)
        else:
            warnings.append(f"DAG '{dag_name}': No tasks defined")

        return errors, warnings

    def _validate_tasks(self, dag_name: str, tasks: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate task configurations.

        Args:
            dag_name: Name of the parent DAG
            tasks: Dictionary of task configurations

        Returns:
            Tuple of (errors, warnings) lists
        """
        errors: List[str] = []
        warnings: List[str] = []
        task_names = set(tasks.keys())

        for task_name, task_config in tasks.items():
            if not isinstance(task_config, dict):
                errors.append(
                    f"DAG '{dag_name}', task '{task_name}': Configuration must be a dictionary"
                )
                continue

            # Check required task fields
            for required_field in self.required_task_fields:
                if required_field not in task_config:
                    errors.append(
                        f"DAG '{dag_name}', task '{task_name}': Missing required field '{required_field}'"
                    )

            # Validate dependencies reference existing tasks
            for dep_key in self.DEPENDENCY_KEYS:
                if dep_key in task_config:
                    deps = task_config[dep_key]
                    if isinstance(deps, list):
                        for dep in deps:
                            if dep not in task_names:
                                errors.append(
                                    f"DAG '{dag_name}', task '{task_name}': "
                                    f"Dependency '{dep}' references non-existent task"
                                )
                    elif isinstance(deps, str):
                        if deps not in task_names:
                            errors.append(
                                f"DAG '{dag_name}', task '{task_name}': "
                                f"Dependency '{deps}' references non-existent task"
                            )

        return errors, warnings

    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate a YAML file for both syntax and DAG structure.

        Args:
            file_path: Path to the YAML file

        Returns:
            ValidationResult with full validation status
        """
        file_path = Path(file_path)

        # First validate syntax
        syntax_result = self.validate_yaml_syntax(file_path)
        if not syntax_result.is_valid:
            return syntax_result

        # Load and validate structure
        try:
            with open(file_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                file_path=str(file_path),
                errors=[f"Failed to load YAML: {e}"],
            )

        if config is None:
            return ValidationResult(
                is_valid=False,
                file_path=str(file_path),
                errors=["Empty YAML file"],
            )

        return self.validate_dag_structure(config, str(file_path))

    def validate_directory(
        self,
        directory: Union[str, Path],
        pattern: str = "*.yaml",
        recursive: bool = True,
    ) -> List[ValidationResult]:
        """Validate all YAML files in a directory.

        Args:
            directory: Path to the directory
            pattern: Glob pattern for YAML files (default: "*.yaml")
            recursive: Whether to search recursively (default: True)

        Returns:
            List of ValidationResult objects for each file
        """
        directory = Path(directory)
        results: List[ValidationResult] = []

        if not directory.exists():
            return [
                ValidationResult(
                    is_valid=False,
                    file_path=str(directory),
                    errors=[f"Directory not found: {directory}"],
                )
            ]

        if not directory.is_dir():
            return [
                ValidationResult(
                    is_valid=False,
                    file_path=str(directory),
                    errors=[f"Not a directory: {directory}"],
                )
            ]

        # Find all YAML files
        glob_method = directory.rglob if recursive else directory.glob
        yaml_files = list(glob_method(pattern))

        # Also check for .yml extension
        yml_pattern = pattern.replace(".yaml", ".yml")
        if yml_pattern != pattern:
            yaml_files.extend(glob_method(yml_pattern))

        if not yaml_files:
            return [
                ValidationResult(
                    is_valid=True,
                    file_path=str(directory),
                    warnings=[f"No YAML files found matching pattern: {pattern}"],
                )
            ]

        for file_path in sorted(yaml_files):
            results.append(self.validate_file(file_path))

        return results


def validate_yaml_file(file_path: Union[str, Path]) -> ValidationResult:
    """Convenience function to validate a single YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        ValidationResult with validation status
    """
    validator = YamlDagValidator()
    return validator.validate_file(file_path)


def validate_yaml_directory(
    directory: Union[str, Path],
    pattern: str = "*.yaml",
    recursive: bool = True,
) -> List[ValidationResult]:
    """Convenience function to validate all YAML files in a directory.

    Args:
        directory: Path to the directory
        pattern: Glob pattern for YAML files (default: "*.yaml")
        recursive: Whether to search recursively (default: True)

    Returns:
        List of ValidationResult objects for each file
    """
    validator = YamlDagValidator()
    return validator.validate_directory(directory, pattern, recursive)
