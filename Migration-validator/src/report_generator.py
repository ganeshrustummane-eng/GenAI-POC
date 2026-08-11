"""
Report Generator
Generates validation reports in multiple formats
"""

import json
from datetime import datetime
from typing import Dict, Any
from models import ValidationReport


class ReportGenerator:
    """Generate validation reports"""
    
    @staticmethod
    def generate_json_report(report: ValidationReport) -> str:
        """Generate JSON report"""
        
        report_dict = {
            "validation_id": report.validation_id,
            "timestamp": report.timestamp.isoformat(),
            "source_database": report.source_database,
            "target_database": report.target_database,
            "overall_status": report.overall_status,
            "summary": {
                "total_tables": report.total_tables,
                "passed_tables": report.passed_tables,
                "failed_tables": report.failed_tables,
                "error_tables": report.error_tables,
                "total_source_rows": report.total_source_rows,
                "total_target_rows": report.total_target_rows,
                "total_matched_rows": report.total_matched_rows,
                "overall_data_completeness_percentage": round(report.overall_data_completeness, 2),
                "success_rate_percentage": round(report.success_rate, 2)
            },
            "table_results": []
        }
        
        for table_result in report.table_results:
            table_dict = {
                "table_name": table_result.table_name,
                "source_rows": table_result.source_rows,
                "target_rows": table_result.target_rows,
                "matched_rows": table_result.matched_rows,
                "unmatched_rows": table_result.unmatched_rows,
                "row_count_match": table_result.row_count_match,
                "status": table_result.overall_status,
                "data_completeness_percentage": round(table_result.data_completeness_percentage, 2),
                "column_results": []
            }
            
            for col_result in table_result.column_results:
                col_dict = {
                    "column_name": col_result.column_name,
                    "source_count": col_result.source_count,
                    "target_count": col_result.target_count,
                    "matched_count": col_result.matched_count,
                    "unmatched_count": col_result.unmatched_count,
                    "status": col_result.status,
                    "applied_rules": [rule.value for rule in col_result.applied_rules]
                }
                
                if col_result.error_message:
                    col_dict["error"] = col_result.error_message
                
                table_dict["column_results"].append(col_dict)
            
            if table_result.error_message:
                table_dict["error"] = table_result.error_message
            
            report_dict["table_results"].append(table_dict)
        
        if report.notes:
            report_dict["notes"] = report.notes
        
        return json.dumps(report_dict, indent=2)
    
    @staticmethod
    def generate_html_report(report: ValidationReport) -> str:
        """Generate HTML report"""
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Migration Validation Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        .metric-card h3 {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .metric-card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }}
        
        .metric-card.success {{
            border-left-color: #10b981;
        }}
        
        .metric-card.success .value {{
            color: #10b981;
        }}
        
        .metric-card.warning {{
            border-left-color: #f59e0b;
        }}
        
        .metric-card.warning .value {{
            color: #f59e0b;
        }}
        
        .metric-card.danger {{
            border-left-color: #ef4444;
        }}
        
        .metric-card.danger .value {{
            color: #ef4444;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .status-pass {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .status-fail {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .status-partial {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        .status-error {{
            background: #fecaca;
            color: #7f1d1d;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section-title {{
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            color: #333;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }}
        
        table thead {{
            background: #f3f4f6;
        }}
        
        table th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #e5e7eb;
        }}
        
        table td {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        table tbody tr:hover {{
            background: #f9fafb;
        }}
        
        .footer {{
            background: #f3f4f6;
            padding: 20px 40px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            width: {report.overall_data_completeness}%;
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Migration Validation Report</h1>
            <p>Data Migration from {report.source_database} to {report.target_database}</p>
            <p>Generated on {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="metric-card success">
                <h3>Overall Status</h3>
                <div class="value">
                    <span class="status-badge status-{report.overall_status.lower()}">
                        {report.overall_status}
                    </span>
                </div>
            </div>
            <div class="metric-card">
                <h3>Data Completeness</h3>
                <div class="value">{report.overall_data_completeness:.1f}%</div>
            </div>
            <div class="metric-card">
                <h3>Passed Tables</h3>
                <div class="value">{report.passed_tables}/{report.total_tables}</div>
            </div>
            <div class="metric-card">
                <h3>Matched Rows</h3>
                <div class="value">{report.total_matched_rows:,}/{report.total_source_rows:,}</div>
            </div>
        </div>
        
        <div class="content">
            <h2 class="section-title">📊 Detailed Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Table Name</th>
                        <th>Source Rows</th>
                        <th>Target Rows</th>
                        <th>Matched</th>
                        <th>Completeness</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for table_result in report.table_results:
            status_class = f"status-{table_result.overall_status.lower()}"
            
            html += f"""
                    <tr>
                        <td><strong>{table_result.table_name}</strong></td>
                        <td>{table_result.source_rows:,}</td>
                        <td>{table_result.target_rows:,}</td>
                        <td>{table_result.matched_rows:,}</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {table_result.data_completeness_percentage}%"></div>
                            </div>
                            {table_result.data_completeness_percentage:.1f}%
                        </td>
                        <td><span class="status-badge {status_class}">{table_result.overall_status}</span></td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Validation ID: {validation_id}</p>
            <p>Generated by Migration Validator PoC</p>
        </div>
    </div>
</body>
</html>
""".format(validation_id=report.validation_id)
        
        return html
    
    @staticmethod
    def generate_text_report(report: ValidationReport) -> str:
        """Generate text report"""
        
        text = f"""
{'='*80}
MIGRATION VALIDATION REPORT
{'='*80}

Validation ID: {report.validation_id}
Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Source Database: {report.source_database}
Target Database: {report.target_database}
Overall Status: {report.overall_status}

{'='*80}
SUMMARY
{'='*80}

Total Tables:           {report.total_tables}
Passed Tables:          {report.passed_tables}
Failed Tables:          {report.failed_tables}
Error Tables:           {report.error_tables}

Total Source Rows:      {report.total_source_rows:,}
Total Target Rows:      {report.total_target_rows:,}
Total Matched Rows:     {report.total_matched_rows:,}

Data Completeness:      {report.overall_data_completeness:.2f}%
Success Rate:           {report.success_rate:.2f}%

{'='*80}
TABLE RESULTS
{'='*80}

"""
        
        for table_result in report.table_results:
            text += f"""
Table: {table_result.table_name}
  Source Rows:           {table_result.source_rows:,}
  Target Rows:           {table_result.target_rows:,}
  Matched Rows:          {table_result.matched_rows:,}
  Unmatched Rows:        {table_result.unmatched_rows:,}
  Data Completeness:     {table_result.data_completeness_percentage:.2f}%
  Status:                {table_result.overall_status}
  Row Count Match:       {'✓ YES' if table_result.row_count_match else '✗ NO'}
"""
            
            if table_result.error_message:
                text += f"  Error: {table_result.error_message}\n"
        
        text += f"\n{'='*80}\n"
        
        return text


class ReportWriter:
    """Write reports to files"""
    
    @staticmethod
    def write_json_report(report: ValidationReport, filepath: str) -> str:
        """Write JSON report to file"""
        content = ReportGenerator.generate_json_report(report)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ JSON report written to: {filepath}")
        return filepath
    
    @staticmethod
    def write_html_report(report: ValidationReport, filepath: str) -> str:
        """Write HTML report to file"""
        content = ReportGenerator.generate_html_report(report)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ HTML report written to: {filepath}")
        return filepath
    
    @staticmethod
    def write_text_report(report: ValidationReport, filepath: str) -> str:
        """Write text report to file"""
        content = ReportGenerator.generate_text_report(report)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Text report written to: {filepath}")
        return filepath
