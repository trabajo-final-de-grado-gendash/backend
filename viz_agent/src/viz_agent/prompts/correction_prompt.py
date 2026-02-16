# viz_agent/prompts/correction_prompt.py

CORRECTION_PROMPT_TEMPLATE = """You are debugging Plotly visualization code that failed with an error.

## Original Code
```python
{original_code}
```

## Error Information
- Error Type: {error_type}
- Error Message: {error_message}
- Attempt Number: {attempt_number}/5

## DataFrame Metadata
{df_metadata}

## Common Issues and Solutions
- **Syntax errors**: Check for typos, missing parentheses, incorrect indentation, unclosed strings
- **Runtime errors**: 
  - Verify column names exist in the DataFrame (case-sensitive)
  - Check data types are compatible with chart type
  - Handle null/NaN values with dropna() or fillna()
  - Ensure numeric operations use numeric columns
- **Empty figure**: 
  - Verify data is being plotted (check x/y parameters)
  - Review filters and conditions (may exclude all data)
  - Check aggregations return non-empty results

## Fix Requirements
1. The DataFrame is available as 'df'
2. The figure must be named 'fig'
3. Fix the specific error mentioned above
4. Keep the original visualization intent (same chart type and columns)
5. Include all necessary imports
6. Return complete, executable Python code
7. Add defensive checks if needed (e.g., check if column exists)

Generate a response following the provided JSON schema with:
- corrected_code: The complete fixed Python code
- explanation: Brief description of what was fixed and why
"""
