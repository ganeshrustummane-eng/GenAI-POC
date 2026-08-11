"""
Core Validation Engine
Orchestrates validation across source and target databases
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from models import (
    ValidationConfig, TableMapping, ColumnMapping, 
    ValidationReport, TableValidationResult, ColumnValidationResult
)
from sql_generators import query_generator
from database_connectors import ConnectorFactory


class DataValidator:
    """Main validation engine"""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.validation_id = config.validation_id or str(uuid.uuid4())
        self.source_connector = None
        self.target_connector = None
        self.report = None
    
    def initialize_connectors(self) -> bool:
        """Initialize database connectors"""
        try:
            factory = ConnectorFactory()
            
            self.source_connector = factory.create_connector(self.config.source_db)
            if not self.source_connector.connect():
                return False
            
            self.target_connector = factory.create_connector(self.config.target_db)
            if not self.target_connector.connect():
                return False
            
            return True
        except Exception as e:
            print(f"✗ Failed to initialize connectors: {e}")
            return False
    
    def cleanup(self):
        """Close all connections"""
        if self.source_connector:
            self.source_connector.disconnect()
        if self.target_connector:
            self.target_connector.disconnect()
    
    def validate_row_counts(self, table_mapping: TableMapping) -> tuple:
        """
        Validate row counts between source and target
        
        Returns:
            (source_count, target_count)
        """
        # Generate row count queries
        source_gen = query_generator.get_generator(self.config.source_db.database_type)
        target_gen = query_generator.get_generator(self.config.target_db.database_type)
        
        source_query = source_gen.generate_row_count_query(
            self.config.source_db.schema,
            table_mapping.source_table
        )
        
        target_query = target_gen.generate_row_count_query(
            self.config.target_db.database,
            self.config.target_db.schema,
            table_mapping.target_table
        )
        
        # Execute queries
        source_result = self.source_connector.execute_query(source_query)
        target_result = self.target_connector.execute_query(target_query)
        
        source_count = source_result.rows[0]['row_count'] if source_result.rows else 0
        target_count = target_result.rows[0]['row_count'] if target_result.rows else 0
        
        return (source_count, target_count)
    
    def validate_data_completeness(
        self,
        table_mapping: TableMapping
    ) -> TableValidationResult:
        """
        Validate data completeness for a table
        
        Returns:
            TableValidationResult with detailed metrics
        """
        result = TableValidationResult(
            table_name=table_mapping.source_table,
            source_rows=0,
            target_rows=0,
            matched_rows=0,
            unmatched_rows=0
        )
        
        try:
            # Step 1: Validate row counts
            source_count, target_count = self.validate_row_counts(table_mapping)
            result.source_rows = source_count
            result.target_rows = target_count
            
            print(f"\n📊 Row Count Validation: {table_mapping.source_table}")
            print(f"   Source: {source_count} rows")
            print(f"   Target: {target_count} rows")
            print(f"   Status: {'✓ MATCH' if source_count == target_count else '✗ MISMATCH'}")
            
            # Step 2: Generate data queries with transformations
            source_gen = query_generator.get_generator(self.config.source_db.database_type)
            target_gen = query_generator.get_generator(self.config.target_db.database_type)
            
            source_data_query = source_gen.generate_data_query(
                self.config.source_db.schema,
                table_mapping.source_table,
                table_mapping.column_mappings
            )
            
            target_data_query = target_gen.generate_data_query(
                self.config.target_db.database,
                self.config.target_db.schema,
                table_mapping.target_table,
                table_mapping.column_mappings
            )
            
            # Step 3: Fetch transformed data
            source_data = self.source_connector.execute_query(source_data_query)
            target_data = self.target_connector.execute_query(target_data_query)
            
            if source_data.error or target_data.error:
                result.error_message = f"Source Error: {source_data.error}, Target Error: {target_data.error}"
                result.overall_status = "ERROR"
                return result
            
            print(f"\n🔄 Data Transformation & Comparison: {table_mapping.source_table}")
            print(f"   Source data fetched: {source_data.row_count} rows ({source_data.execution_time_ms:.2f}ms)")
            print(f"   Target data fetched: {target_data.row_count} rows ({target_data.execution_time_ms:.2f}ms)")
            
            # Step 4: Compare data
            matched = self._compare_data(
                source_data.rows,
                target_data.rows,
                table_mapping.column_mappings
            )
            
            result.matched_rows = matched
            result.unmatched_rows = source_count - matched
            
            # Determine overall status
            if source_count == target_count and matched == source_count:
                result.overall_status = "PASS"
            elif matched == source_count:
                result.overall_status = "PARTIAL"  # Row counts differ but all matches
            else:
                result.overall_status = "FAIL"
            
            # Step 5: Validate individual columns
            result.column_results = self._validate_columns(
                source_data.rows,
                target_data.rows,
                table_mapping.column_mappings
            )
            
            print(f"\n✅ Validation Result: {result.overall_status}")
            print(f"   Matched rows: {result.matched_rows} / {result.source_rows}")
            print(f"   Data completeness: {result.data_completeness_percentage:.2f}%")
            
        except Exception as e:
            result.error_message = str(e)
            result.overall_status = "ERROR"
            print(f"\n✗ Validation error: {e}")
        
        return result
    
    def _compare_data(
        self,
        source_rows: List[Dict],
        target_rows: List[Dict],
        column_mappings: List[ColumnMapping]
    ) -> int:
        """
        Compare source and target data
        
        Returns:
            Number of matched rows
        """
        if not source_rows or not target_rows:
            return 0
        
        matched = 0
        
        for i, source_row in enumerate(source_rows):
            if i < len(target_rows):
                target_row = target_rows[i]
                
                # Compare normalized values
                row_match = True
                for mapping in column_mappings:
                    source_col = f"{mapping.source_column}_normalized"
                    target_col = f"{mapping.target_column}_normalized"
                    
                    if source_col in source_row and target_col in target_row:
                        if source_row[source_col] != target_row[target_col]:
                            row_match = False
                            break
                
                if row_match:
                    matched += 1
        
        return matched
    
    def _validate_columns(
        self,
        source_rows: List[Dict],
        target_rows: List[Dict],
        column_mappings: List[ColumnMapping]
    ) -> List[ColumnValidationResult]:
        """
        Validate individual columns
        
        Returns:
            List of column validation results
        """
        column_results = []
        
        for mapping in column_mappings:
            result = ColumnValidationResult(
                column_name=mapping.source_column,
                source_count=len(source_rows),
                target_count=len(target_rows),
                matched_count=0,
                unmatched_count=0,
                status="PENDING",
                applied_rules=mapping.apply_rules
            )
            
            # Count matching values
            matched = 0
            for i, source_row in enumerate(source_rows):
                if i < len(target_rows):
                    source_col = f"{mapping.source_column}_normalized"
                    target_col = f"{mapping.target_column}_normalized"
                    
                    if (source_col in source_row and target_col in target_rows[i] and
                        source_row[source_col] == target_rows[i][target_col]):
                        matched += 1
            
            result.matched_count = matched
            result.unmatched_count = len(source_rows) - matched
            result.status = "PASS" if matched == len(source_rows) else "FAIL"
            
            column_results.append(result)
        
        return column_results
    
    def run_validation(self) -> ValidationReport:
        """
        Execute complete validation
        
        Returns:
            ValidationReport with all results
        """
        print(f"\n{'='*70}")
        print(f"  🚀 Migration Validator - Starting Validation")
        print(f"{'='*70}")
        print(f"Validation ID: {self.validation_id}")
        print(f"Source: {self.config.source_db}")
        print(f"Target: {self.config.target_db}")
        print(f"Tables: {len(self.config.table_mappings)}")
        
        # Initialize report
        self.report = ValidationReport(
            validation_id=self.validation_id,
            timestamp=datetime.now(),
            source_database=str(self.config.source_db),
            target_database=str(self.config.target_db),
            total_tables=len(self.config.table_mappings)
        )
        
        try:
            # Initialize connectors
            if not self.initialize_connectors():
                self.report.overall_status = "ERROR"
                return self.report
            
            # Validate each table
            for table_mapping in self.config.table_mappings:
                table_result = self.validate_data_completeness(table_mapping)
                self.report.table_results.append(table_result)
                
                # Update totals
                self.report.total_source_rows += table_result.source_rows
                self.report.total_target_rows += table_result.target_rows
                self.report.total_matched_rows += table_result.matched_rows
                
                if table_result.overall_status == "PASS":
                    self.report.passed_tables += 1
                elif table_result.overall_status == "ERROR":
                    self.report.error_tables += 1
                else:
                    self.report.failed_tables += 1
            
            # Determine overall status
            if self.report.error_tables > 0:
                self.report.overall_status = "ERROR"
            elif self.report.failed_tables == 0:
                self.report.overall_status = "PASS"
            elif self.report.failed_tables > 0 and self.report.passed_tables > 0:
                self.report.overall_status = "PARTIAL"
            else:
                self.report.overall_status = "FAIL"
        
        finally:
            self.cleanup()
        
        return self.report
    
    def get_validation_queries(self) -> Dict[str, str]:
        """
        Generate all validation queries without executing them
        Useful for manual execution or review
        
        Returns:
            Dictionary with all generated queries
        """
        queries = {}
        
        for i, table_mapping in enumerate(self.config.table_mappings):
            table_key = f"table_{i}_{table_mapping.source_table}"
            
            # Generate row count queries
            source_gen = query_generator.get_generator(self.config.source_db.database_type)
            target_gen = query_generator.get_generator(self.config.target_db.database_type)
            
            queries[f"{table_key}_row_count_source"] = source_gen.generate_row_count_query(
                self.config.source_db.schema,
                table_mapping.source_table
            )
            
            queries[f"{table_key}_row_count_target"] = target_gen.generate_row_count_query(
                self.config.target_db.database,
                self.config.target_db.schema,
                table_mapping.target_table
            )
            
            # Generate data queries
            queries[f"{table_key}_data_source"] = source_gen.generate_data_query(
                self.config.source_db.schema,
                table_mapping.source_table,
                table_mapping.column_mappings
            )
            
            queries[f"{table_key}_data_target"] = target_gen.generate_data_query(
                self.config.target_db.database,
                self.config.target_db.schema,
                table_mapping.target_table,
                table_mapping.column_mappings
            )
        
        return queries
