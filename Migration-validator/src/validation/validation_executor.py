"""
Validation executor for batch processing
Orchestrates execution of count and data validations
"""
import logging
import yaml
import os
from pathlib import Path
from datetime import datetime
from src.utils.runid import generate_runid
from src.utils.logging_config import get_logger, add_file_handler
from src.utils.path_manager import get_config_output_paths
from src.db.factory import DatabaseFactory
from src.validation.count_validator import execute_count_validation
from src.validation.data_validator import execute_data_validation

logger = get_logger(__name__)


class ValidationExecutor:
    """Orchestrates batch validation execution"""
    
    def __init__(self, base_dir=None, environment="dev"):
        """
        Initialize validation executor
        
        Args:
            base_dir: Base project directory (contains config/, output/, src/)
            environment: Environment name ('dev', 'uat', 'prod') for .env selection
        """
        repo_root = Path(__file__).resolve().parents[2]
        requested_base = Path(base_dir).resolve() if base_dir else repo_root
        # Running from src/ should still write reports to repository/output/.
        self.base_dir = str(repo_root if requested_base.name.lower() == "src" else requested_base)
        self.environment = environment
        self.db_factory = DatabaseFactory()
        self.run_id, self.run_at = generate_runid()
        logger.info(f"ValidationExecutor initialized with run_id: {self.run_id}")
    
    def execute_batch(self, layer: str, tables: list = None, validation_types: list = None,
                      config_dir: str = None) -> dict:
        """
        Execute batch validation
        
        Args:
            layer: 'bronze', 'silver', 'gold', or 'reporting'
            tables: List of table names or None for all
            validation_types: ['count_validation', 'data_validation'] or subset
            config_dir: Path to config directory (default: base_dir/config)
        
        Returns:
            dict: Results of all validations executed
        
        Example:
            >>> executor = ValidationExecutor(base_dir='c:/project')
            >>> results = executor.execute_batch(
            ...     layer='bronze',
            ...     tables=['users', 'orders'],
            ...     validation_types=['count_validation', 'data_validation'],
            ...     config_dir='c:/project/config'
            ... )
            >>> for result in results.values():
            ...     print(f"{result['table']}: {result['status']}")
        """
        
        if config_dir is None:
            config_dir = os.path.join(self.base_dir, "config")
        
        if validation_types is None:
            validation_types = ['count_validation', 'data_validation']
        
        logger.info(f"Starting batch validation: layer={layer}, run_id={self.run_id}")
        
        # Setup paths
        output_paths, config_paths, log_path = get_config_output_paths(
            run_id=self.run_id,
            layer_type=layer,
            base_dir=self.base_dir,
            config_path=config_dir,
            validation_dirs=validation_types,
            table_list=tables or ['all']
        )
        
        # Setup logging with file handler
        os.makedirs(log_path, exist_ok=True)
        log_file = f"validation_{self.run_id}.log"
        add_file_handler(logger, log_path, log_file)
        
        results = {}
        
        # Execute validations
        for validation_type in validation_types:
            logger.info(f"\n{'='*60}")
            logger.info(f"Executing {validation_type}...")
            logger.info(f"{'='*60}")
            
            output_path = output_paths.get(validation_type)
            config_yamls = config_paths.get(validation_type, [])
            
            if not config_yamls:
                logger.warning(f"No config files found for {validation_type}")
                continue
            
            # Load and execute each config
            for config_yaml in config_yamls:
                try:
                    with open(config_yaml, 'r') as f:
                        config_data = yaml.safe_load(f)
                    
                    if not config_data:
                        logger.warning(f"Empty config: {config_yaml}")
                        continue
                    
                    configs = self._flatten_configs(config_data, validation_type)
                    
                    # Execute each validation in config
                    for config in configs:
                        table_name = config.get('source_table_name', 'unknown')
                        if tables and 'all' not in tables and table_name not in tables:
                            continue
                        result_key = f"{validation_type}_{table_name}"
                        
                        try:
                            if validation_type == 'count_validation':
                                result = execute_count_validation(
                                    config,
                                    self.db_factory,
                                    self.run_id,
                                    self.run_at,
                                    output_path
                                )
                            else:  # data_validation
                                result = execute_data_validation(
                                    config,
                                    self.db_factory,
                                    self.run_id,
                                    self.run_at,
                                    output_path
                                )
                            
                            result['table'] = table_name
                            result['validation_type'] = validation_type
                            results[result_key] = result
                        
                        except Exception as e:
                            logger.error(f"Failed to execute config for {table_name}: {e}", exc_info=True)
                            results[result_key] = {
                                'table': table_name,
                                'validation_type': validation_type,
                                'status': 'ERROR',
                                'error': str(e)
                            }
                
                except Exception as e:
                    logger.error(f"Failed to load config {config_yaml}: {e}", exc_info=True)
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("VALIDATION BATCH SUMMARY")
        logger.info(f"{'='*60}")
        
        pass_count = sum(1 for r in results.values() if r.get('status') == 'PASS')
        fail_count = sum(1 for r in results.values() if r.get('status') == 'FAIL')
        error_count = sum(1 for r in results.values() if r.get('status') == 'ERROR')
        
        logger.info(f"Total: {len(results)} | PASS: {pass_count} | FAIL: {fail_count} | ERROR: {error_count}")
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Logs: {log_path}")
        logger.info(f"Output: {self.base_dir}/output/{layer}/validation_{self.run_id}")
        
        return results

    @staticmethod
    def _flatten_configs(config_data, validation_type):
        """Return executable validation blocks from flat or grouped YAML."""
        if isinstance(config_data, list):
            return [item for item in config_data if isinstance(item, dict)]
        if not isinstance(config_data, dict):
            raise ValueError("Validation config must be a mapping or list")

        if 'tables' not in config_data:
            return [config_data]

        configs = []
        for table_name, table_data in config_data['tables'].items():
            if not isinstance(table_data, dict):
                continue
            validation = table_data.get('validations', {}).get(validation_type)
            if validation is None:
                continue
            if isinstance(validation, list):
                configs.extend(item for item in validation if isinstance(item, dict))
            elif isinstance(validation, dict):
                configs.append(validation)
            else:
                raise ValueError(f"Invalid {validation_type} config for table {table_name}")
        return configs


if __name__ == "__main__":
    # Example usage
    executor = ValidationExecutor(
        base_dir="c:/EPAM-Personal/Migration-validator",
        environment="dev"
    )
    
    results = executor.execute_batch(
        layer="bronze",
        validation_types=['count_validation'],
        tables=['all'],
        config_dir="c:/EPAM-Personal/Migration-validator/config"
    )
    
    for result_key, result in results.items():
        print(f"\n{result_key}:")
        for k, v in result.items():
            print(f"  {k}: {v}")
