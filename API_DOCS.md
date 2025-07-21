# FlakeRadar Python API Documentation

The FlakeRadar Python API provides a programmatic interface to FlakeRadar's test analysis capabilities, allowing you to integrate flakiness detection into your Python scripts and workflows.

## Quick Start

```python
from flakeradar import FlakeRadar

# Initialize analyzer
radar = FlakeRadar(project="MyApp")

# Add test results
radar.add_results("test-results/*.xml")

# Analyze flakiness
analysis = radar.analyze(
    confidence_threshold=0.7,
    enable_ai=True,
    track_time_to_fix=True
)

# Generate reports
radar.generate_html_report("report.html")
radar.export_metrics("metrics.json")
```

## API Reference

### FlakeRadar Class

#### Constructor

```python
FlakeRadar(project, db_path=None, build_id=None, commit_sha=None)
```

- `project` (str): Project name for test analysis
- `db_path` (str, optional): Path to SQLite database (defaults to `~/.flakeradar/history.db`)
- `build_id` (str, optional): Build identifier (defaults to timestamp)
- `commit_sha` (str, optional): Git commit SHA (defaults to "unknown")

#### Methods

##### add_results(results_glob)
Add test results from files matching the glob pattern.

```python
count = radar.add_results("test-results/*.xml")
```

Returns the number of result files processed.

##### add_result_file(file_path)
Add a single test result file.

```python
radar.add_result_file("test-output.xml")
```

##### analyze(confidence_threshold=0.7, enable_ai=None, track_time_to_fix=True, limit_runs=50, max_ai_analysis=20)
Perform flakiness analysis on loaded test results.

```python
analysis = radar.analyze(
    confidence_threshold=0.8,  # Higher confidence threshold
    enable_ai=False,           # Disable AI analysis
    track_time_to_fix=True,    # Track time-to-fix metrics
    limit_runs=100,            # Include more historical runs
    max_ai_analysis=10         # Limit AI analysis to 10 tests
)
```

Returns a dictionary with analysis results including:
- `total_tests`: Total number of tests
- `flaky_tests`: Number of flaky tests detected
- `high_confidence_flaky`: Number of high-confidence flaky tests
- `test_results`: Detailed results for each test
- `worst_offenders`: Tests that have been flaky the longest
- `cluster_analysis`: Root cause clustering analysis

##### generate_html_report(output_path="flakeradar_report.html")
Generate HTML report from analysis results.

```python
report_path = radar.generate_html_report("my_report.html")
```

Returns the absolute path to the generated report.

##### export_metrics(output_path)
Export analysis metrics to JSON file.

```python
metrics_path = radar.export_metrics("metrics.json")
```

##### get_flaky_tests(confidence_threshold=0.7, include_always_failing=True)
Get list of flaky tests above confidence threshold.

```python
flaky_tests = radar.get_flaky_tests(confidence_threshold=0.8)
```

##### get_summary()
Get summary statistics from analysis.

```python
summary = radar.get_summary()
print(f"Flakiness rate: {summary['flakiness_rate']:.1f}%")
```

##### publish_results(redis_config=None, kafka_config=None)
Publish analysis results to Redis and/or Kafka.

```python
radar.publish_results()
```

##### close()
Close database connection.

```python
radar.close()
```

## Usage Patterns

### Context Manager

Use FlakeRadar as a context manager for automatic cleanup:

```python
with FlakeRadar(project="MyApp") as radar:
    radar.add_results("test-results/*.xml")
    analysis = radar.analyze()
    radar.generate_html_report("report.html")
# Database connection automatically closed
```

### Batch Processing

Process multiple projects:

```python
projects = ["ProjectA", "ProjectB", "ProjectC"]
results = {}

for project in projects:
    with FlakeRadar(project=project) as radar:
        radar.add_results(f"{project.lower()}/test-results/*.xml")
        analysis = radar.analyze()
        summary = radar.get_summary()
        results[project] = summary
        radar.generate_html_report(f"{project.lower()}_report.html")
```

### Error Handling

```python
try:
    radar = FlakeRadar(project="MyApp")
    radar.add_results("test-results/*.xml")
    analysis = radar.analyze()
except FileNotFoundError:
    print("No test result files found")
except ValueError as e:
    print(f"Analysis error: {e}")
finally:
    radar.close()
```

### Integration with CI/CD

```python
import os
from flakeradar import FlakeRadar

# CI/CD integration example
project = os.environ.get("CI_PROJECT_NAME", "Unknown")
build_id = os.environ.get("CI_BUILD_ID", "local")
commit = os.environ.get("CI_COMMIT_SHA", "unknown")

with FlakeRadar(project=project, build_id=build_id, commit_sha=commit) as radar:
    radar.add_results("test-results/*.xml")
    analysis = radar.analyze()
    
    # Generate artifacts
    radar.generate_html_report("flakeradar_report.html")
    radar.export_metrics("flakeradar_metrics.json")
    
    # Check if build should fail due to flakiness
    summary = radar.get_summary()
    if summary["flakiness_rate"] > 10.0:  # 10% threshold
        print(f"❌ Build failed: {summary['flakiness_rate']:.1f}% flakiness rate")
        exit(1)
    else:
        print(f"✅ Build passed: {summary['flakiness_rate']:.1f}% flakiness rate")
```

## Configuration

### Database Path

The default database path is `~/.flakeradar/history.db`. You can override this:

```python
# Custom database path
radar = FlakeRadar(project="MyApp", db_path="/custom/path/flakeradar.db")

# Or use environment variable
export FLAKERADAR_DB_PATH="/custom/path/flakeradar.db"
radar = FlakeRadar(project="MyApp")  # Uses environment variable
```

### AI Analysis

AI analysis requires an OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

```python
# Enable AI analysis (auto-detects API key)
analysis = radar.analyze(enable_ai=True)

# Disable AI analysis
analysis = radar.analyze(enable_ai=False)
```

## Examples

See `examples.py` for comprehensive usage examples including:
- Basic usage
- Context manager
- Detailed analysis with custom settings
- Batch processing
- Error handling
- API integration patterns

## Support

For issues and questions, please refer to the main FlakeRadar documentation and GitHub repository.
