# Test Automation Framework - Production Quality

## TESTING PYRAMID

```
          ┌─────────────┐
          │  E2E Tests  │  (5-10% of tests)
          │   UI Tests  │  Slow, brittle, valuable
          ├─────────────┤
          │  Integration│  (20-30% of tests)
          │    Tests    │  Medium speed, good coverage
          ├─────────────┤
          │  Unit Tests │  (60-70% of tests)
          │ Fast, cheap │  Quick feedback
          └─────────────┘

For Data Pipeline:
- Unit: Test transformations (80%)
- Integration: Test full pipeline (15%)
- E2E: Test with real data (5%)
```

---

## UNIT TESTING (Pytest)

### Basic Unit Tests

```python
import pytest
import pandas as pd
from etl_functions import transform_customer_data

class TestTransformCustomer:
    @pytest.fixture
    def sample_data(self):
        """Setup test data"""
        return pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'email': ['alice@example.com', 'bob@invalid', None],
            'age': [25, 30, -5]
        })
    
    def test_transform_uppercase_names(self, sample_data):
        """Test name transformation"""
        result = transform_customer_data(sample_data)
        assert result['name'].iloc[0] == 'ALICE'
        assert result['name'].iloc[1] == 'BOB'
    
    def test_invalid_emails_removed(self, sample_data):
        """Test email validation"""
        result = transform_customer_data(sample_data)
        # Should remove bob@invalid and None
        assert len(result) == 1
        assert result['email'].iloc[0] == 'alice@example.com'
    
    def test_invalid_ages_removed(self, sample_data):
        """Test age validation"""
        result = transform_customer_data(sample_data)
        # Should remove age -5
        assert (result['age'] >= 0).all()
        assert (result['age'] <= 150).all()
    
    def test_empty_input(self):
        """Test with empty data"""
        empty_df = pd.DataFrame()
        result = transform_customer_data(empty_df)
        assert len(result) == 0

# Run tests
pytest test_etl_functions.py -v
```

### Parameterized Tests (Test Multiple Cases)

```python
import pytest

class TestEmailValidation:
    @pytest.mark.parametrize("email,expected", [
        ("valid@example.com", True),
        ("another.valid+tag@domain.co.uk", True),
        ("invalid@.com", False),
        ("no-at-sign.com", False),
        ("@nodomain.com", False),
        ("", False),
    ])
    def test_email_validation(self, email, expected):
        """Test multiple email formats"""
        from validators import is_valid_email
        assert is_valid_email(email) == expected

# Runs 6 tests with different inputs!
```

### Fixtures (Setup/Teardown)

```python
@pytest.fixture
def spark_session():
    """Create Spark session for tests"""
    spark = SparkSession.builder \
        .appName("test") \
        .master("local[2]") \
        .getOrCreate()
    yield spark
    spark.stop()

@pytest.fixture
def sample_df(spark_session):
    """Create sample Spark DataFrame"""
    data = [("id", "value"), (1, "a"), (2, "b")]
    return spark_session.createDataFrame(data)

def test_spark_transformation(spark_session, sample_df):
    """Test using fixtures"""
    result = sample_df.filter(sample_df.id > 1)
    assert result.count() == 1
```

---

## INTEGRATION TESTING

### Test Full Pipeline

```python
class TestETLPipeline:
    @pytest.fixture
    def setup_test_data(self):
        """Setup test data in database"""
        # Create test tables
        conn = connect_to_test_db()
        conn.execute("""
            CREATE TABLE source_customers (
                id INT, name VARCHAR(100), email VARCHAR(100)
            )
        """)
        conn.execute("""
            INSERT INTO source_customers VALUES
            (1, 'Alice', 'alice@example.com'),
            (2, 'Bob', 'bob@example.com')
        """)
        conn.commit()
        
        yield conn
        
        # Cleanup
        conn.execute("DROP TABLE source_customers")
        conn.commit()
        conn.close()
    
    def test_full_etl_pipeline(self, setup_test_data):
        """Test complete ETL flow"""
        # Run ETL
        from etl_pipeline import run_etl
        run_etl(source_db='test', target_db='test')
        
        # Verify
        conn = connect_to_test_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM target_customers")
        count = cursor.fetchone()[0]
        
        assert count == 2
        
        cursor.execute("SELECT name FROM target_customers WHERE id = 1")
        name = cursor.fetchone()[0]
        assert name == 'ALICE'  # Should be uppercase
        
        conn.close()
```

### Data Pipeline Testing

```python
class TestDataPipeline:
    def test_data_quality_metrics(self):
        """Test DQ metrics calculation"""
        df = pd.DataFrame({
            'id': [1, 2, None, 4],
            'value': [10, 20, 30, 40]
        })
        
        # Calculate metrics
        completeness = df['id'].notna().sum() / len(df)
        assert completeness == 0.75  # 3 out of 4
        
        duplicates = df['id'].duplicated().sum()
        assert duplicates == 0
    
    def test_data_quality_gates(self):
        """Test quality gates (thresholds)"""
        metrics = {
            'completeness': 0.95,  # 95%
            'validity': 0.98,      # 98%
            'uniqueness': 0.99     # 99%
        }
        
        min_thresholds = {
            'completeness': 0.95,
            'validity': 0.95,
            'uniqueness': 0.95
        }
        
        # Check if passes
        for metric, value in metrics.items():
            assert value >= min_thresholds[metric], \
                f"{metric} {value} below threshold {min_thresholds[metric]}"
```

---

## MOCKING & STUBS

### Mock External Dependencies

```python
from unittest.mock import patch, MagicMock
import requests

class TestDataFetcher:
    @patch('requests.get')
    def test_fetch_data_success(self, mock_get):
        """Test API call with mock"""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': [{'id': 1, 'name': 'Alice'}]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test
        from data_fetcher import fetch_from_api
        result = fetch_from_api('https://api.example.com/data')
        
        # Verify
        assert len(result) == 1
        assert result[0]['name'] == 'Alice'
        mock_get.assert_called_once_with('https://api.example.com/data')
    
    @patch('requests.get')
    def test_fetch_data_error(self, mock_get):
        """Test API error handling"""
        mock_get.side_effect = requests.ConnectionError("Network error")
        
        from data_fetcher import fetch_from_api
        with pytest.raises(requests.ConnectionError):
            fetch_from_api('https://api.example.com/data')
```

### Mock Database

```python
from unittest.mock import patch
from sqlalchemy import create_engine

class TestDatabaseOperations:
    @patch('sqlalchemy.create_engine')
    def test_database_insert(self, mock_engine):
        """Test DB insert with mock"""
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value = mock_conn
        
        # Test
        from db_ops import insert_customer
        insert_customer('Alice', 'alice@example.com')
        
        # Verify insert called
        assert mock_conn.execute.called
```

---

## CONTINUOUS INTEGRATION

### GitHub Actions (CI/CD)

```yaml
# .github/workflows/tests.yml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit -v --cov=src
    
    - name: Run integration tests
      run: |
        pytest tests/integration -v
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## BEST PRACTICES

### Test Organization

```python
# Good structure
tests/
├── unit/
│   ├── test_transformations.py
│   ├── test_validators.py
│   └── test_utils.py
├── integration/
│   ├── test_etl_pipeline.py
│   └── test_database.py
└── fixtures/
    ├── sample_data.csv
    └── expected_output.csv

# Test naming
def test_should_uppercase_customer_names()  # Clear intent
def test_data_quality_metric_calculation()  # Descriptive

# Avoid
def test_function()  # Too vague
def test_1()  # No meaning
```

### Assertions

```python
# Good assertions (clear error messages)
assert result['name'].equals(expected['name']), \
    f"Names don't match: {result['name']} != {expected['name']}"

# Better: Use pytest-assertions
from pandas.testing import assert_frame_equal
assert_frame_equal(result, expected)

# For Spark
from pyspark.testing import assert_pyspark_frame_equal
assert_pyspark_frame_equal(result_df, expected_df)
```

---

## TEST COVERAGE

### Measure and Track

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Results:
# src/transformations.py: 95% coverage
# src/validators.py: 87% coverage
# src/utils.py: 70% coverage (needs improvement!)

# Coverage target:
# - Critical code: 90%+
# - Important: 80%+
# - Nice-to-have: 60%+

# Check coverage in CI
pytest tests/ --cov=src --cov-fail-under=80
# Fails if coverage < 80%
```

---

## INTERVIEW QUESTIONS

### Q1: Describe your testing strategy

**Answer:**
```
1. UNIT TESTS (60%):
   - Test each function independently
   - Use fixtures for setup
   - Mock external dependencies
   - Fast: Run in seconds

2. INTEGRATION TESTS (30%):
   - Test components together
   - Use test database
   - Test full ETL pipeline
   - Medium speed: Run in minutes

3. E2E TESTS (10%):
   - Test with real data
   - Verify business logic
   - Slow but valuable
   - Run before release

4. DATA QUALITY TESTS:
   - Test transformations
   - Verify aggregations
   - Check constraints

5. PERFORMANCE TESTS:
   - Ensure query performance
   - Track regressions
```

### Q2: How to test Spark jobs?

**Answer:**
```
1. Use local mode:
   spark = SparkSession.builder.master("local[1]").getOrCreate()

2. Test in-memory DataFrames:
   df = spark.createDataFrame([(1, "a"), (2, "b")], ["id", "value"])

3. Use fixtures:
   @pytest.fixture
   def spark():
       return SparkSession.builder.master("local[1]").getOrCreate()

4. Test transformations:
   result = df.filter(...).groupBy(...)
   assert result.count() == expected_count

5. Mock external calls:
   @patch('boto3.client')
   def test_read_from_s3(self, mock_s3):
       ...

6. Use assert_pyspark_frame_equal for comparison
```

---

## KEY TAKEAWAYS

1. **Testing Pyramid** - 60% unit, 30% integration, 10% E2E
2. **Pytest** - Best Python testing framework
3. **Fixtures** - Setup/teardown data efficiently
4. **Mocking** - Isolate units, don't hit real APIs/DB
5. **Parameterized** - Test multiple inputs
6. **CI/CD** - Run tests on every commit
7. **Coverage** - Track and improve (>80%)
8. **Data Tests** - Quality, transformations, constraints

---

*Last Updated: 2026-07-29*
*Level: Intermediate (3 → 4)*
