# Repository Note: Fuzzy Matching - Data Quality & De-identification

## Overview
This repository demonstrates **fuzzy matching techniques combined with synthetic data generation and de-identification workflows**. The project showcases end-to-end data quality management, record linkage using approximate string matching, and privacy-preserving data techniques. It's valuable for understanding how to identify duplicates, resolve data discrepancies, and protect sensitive information in real-world datasets.

**Primary Application:** Record linkage, duplicate detection, data privacy, and data quality assurance

## Repository Details
- **Owner:** daggbt
- **Repository:** fuzzy_matching
- **Created:** August 9, 2023
- **Last Updated:** May 26, 2024
- **Status:** Active (Public)
- **Language Composition:**
  - Jupyter Notebook (81.4%)
  - Python (18.6%)
- **Primary Files:** fuzzy_matching.ipynb, utils.py

## Project Objective

**Research Questions:**
- How can we identify records that match despite minor variations or errors?
- How do we detect intentional modifications or data discrepancies?
- How can we de-identify datasets while preserving analytical value?

**Key Techniques Covered:**
1. Synthetic data generation with realistic characteristics
2. Intentional data modification to simulate real-world errors
3. Parallelized fuzzy matching algorithms
4. Privacy-preserving de-identification techniques

## Project Architecture

### Phase 1: Synthetic Data Generation

**Objective:** Create realistic test datasets with known properties

```python
# Using Faker library to generate synthetic data
from faker import Faker
import pandas as pd
import numpy as np

fake = Faker()

# Create DataFrame 1 (df1) - Clean synthetic records
data1 = {
    'name': [fake.name() for _ in range(1000)],
    'address': [fake.address() for _ in range(1000)],
    'email': [fake.email() for _ in range(1000)],
    'phone': [fake.phone_number() for _ in range(1000)],
    'date_of_birth': [fake.date_of_birth() for _ in range(1000)]
}
df1 = pd.DataFrame(data1)

# Create DataFrame 2 (df2) - Clean synthetic records
data2 = {
    'name': [fake.name() for _ in range(800)],
    'address': [fake.address() for _ in range(800)],
    'email': [fake.email() for _ in range(800)],
    'phone': [fake.phone_number() for _ in range(800)],
    'date_of_birth': [fake.date_of_birth() for _ in range(800)]
}
df2 = pd.DataFrame(data2)
```

### Phase 2: Data Modification (Introducing Discrepancies)

**Objective:** Simulate real-world data quality issues

```python
# Select subset of df2 to modify
modification_indices = np.random.choice(len(df2), size=100, replace=False)

# Introduce intentional modifications to simulate errors
for idx in modification_indices:
    # Typo in name (simulate data entry error)
    df2.loc[idx, 'name'] = df2.loc[idx, 'name'].replace('a', 'e', 1)
    
    # Partial address (simulate incomplete data)
    address_parts = df2.loc[idx, 'address'].split(',')
    df2.loc[idx, 'address'] = ','.join(address_parts[:2])
    
    # Phone number variation (missing digits)
    df2.loc[idx, 'phone'] = df2.loc[idx, 'phone'][:-1]

# Combine modified records with df1
df_combined = pd.concat([df1, df2], ignore_index=True)

# Shuffle to obscure order
df_combined = df_combined.sample(frac=1).reset_index(drop=True)
```

### Phase 3: Parallelized Fuzzy Matching

**Objective:** Identify matching records despite discrepancies

```python
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from multiprocessing import Pool
import pandas as pd

class FuzzyMatcher:
    def __init__(self, master_df, threshold=80):
        self.master_df = master_df
        self.threshold = threshold
    
    def match_record(self, record):
        """Match single record against master data"""
        matches = []
        
        for idx, master_record in self.master_df.iterrows():
            # Calculate fuzzy match score for name
            name_score = fuzz.token_set_ratio(
                record['name'], 
                master_record['name']
            )
            
            # Calculate fuzzy match score for email
            email_score = fuzz.ratio(
                record['email'], 
                master_record['email']
            )
            
            # Combined score (weighted average)
            combined_score = (name_score * 0.6 + email_score * 0.4)
            
            if combined_score >= self.threshold:
                matches.append({
                    'original_idx': idx,
                    'match_idx': record.name,
                    'score': combined_score,
                    'matched_name': master_record['name'],
                    'original_name': record['name']
                })
        
        return matches
    
    def parallel_match(self, target_df, n_processes=4):
        """Parallelize fuzzy matching across multiple processes"""
        with Pool(n_processes) as pool:
            results = pool.map(self.match_record, 
                             [target_df.iloc[i] for i in range(len(target_df))])
        
        # Flatten results
        all_matches = [match for sublist in results for match in sublist]
        return pd.DataFrame(all_matches)

# Initialize matcher
matcher = FuzzyMatcher(df1, threshold=80)

# Run parallel matching
matches_df = matcher.parallel_match(df_combined, n_processes=4)

print(f"Found {len(matches_df)} fuzzy matches")
print(matches_df.head())
```

## Phase 4: De-identification

**Objective:** Remove personally identifiable information (PII) while preserving analytical structure

### Sensitive Information Identification

```python
# List of sensitive columns
sensitive_columns = [
    'name',           # Direct identifier
    'address',        # Direct identifier
    'email',          # Direct identifier
    'phone',          # Direct identifier
    'date_of_birth'   # Quasi-identifier
]

# Identify PII patterns
pii_patterns = {
    'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'phone': r'^\+?1?\d{9,15}$',
    'date': r'^\d{4}-\d{2}-\d{2}$'
}

# Validate PII detection
for col in sensitive_columns:
    if col in matches_df.columns:
        print(f"Column '{col}' identified as sensitive (PII)")
```

### De-identification Process

```python
# Create de-identified version
matches_deidentified = matches_df.copy()

# Method 1: Remove sensitive columns entirely
matches_deidentified = matches_deidentified.drop(
    columns=['name', 'address', 'email', 'phone']
)

# Method 2: Hash sensitive data (alternative approach)
import hashlib

def hash_pii(value):
    """One-way hash to obscure PII while maintaining consistency"""
    return hashlib.sha256(str(value).encode()).hexdigest()[:8]

# Apply hashing instead of removal (preserves linkage capability)
matches_deidentified['name_hash'] = matches_df['matched_name'].apply(hash_pii)
matches_deidentified['original_name_hash'] = matches_df['original_name'].apply(hash_pii)

# Drop original columns
matches_deidentified = matches_deidentified.drop(
    columns=['matched_name', 'original_name']
)

# Verify de-identification
print("De-identified dataset structure:")
print(matches_deidentified.head())
print(f"Columns retained: {list(matches_deidentified.columns)}")
```

## Key Technical Components

### Fuzzy Matching Algorithms Used

1. **Token Set Ratio**
   - Handles word order variations
   - Example: "John Smith" vs "Smith John"

2. **Ratio Score**
   - Simple string similarity
   - Useful for email and identifier matching

3. **Threshold-Based Filtering**
   - Default threshold: 80 out of 100
   - Adjustable based on use case

### Performance Optimization

```python
# Parallelization setup
from multiprocessing import Pool, cpu_count

# Automatic detection of available cores
n_cores = cpu_count()

# Create process pool for parallel matching
pool = Pool(processes=n_cores)

# Distribute fuzzy matching across processes
chunk_size = len(df_combined) // n_cores
results = pool.map(matcher.match_record, 
                   [df_combined.iloc[i] for i in range(len(df_combined))],
                   chunksize=chunk_size)
```

## Utilities Module (utils.py)

The `utils.py` file contains helper functions for:
- Data validation and cleaning
- Fuzzy matching wrapper functions
- De-identification utilities
- Results formatting and reporting

## Setup & Installation

### Prerequisites
```bash
# Install Conda (if not already installed)
# Download from: https://docs.conda.io/en/latest/miniconda.html
```

### Environment Creation
```bash
# Step 1: Create environment from environment.yml
conda env create -f environment.yml

# Step 2: Activate environment
conda activate link

# Step 3: Launch Jupyter Notebook
jupyter notebook fuzzy_matching.ipynb
```

## Key Packages & Dependencies

- **fuzzywuzzy** - Fuzzy string matching
- **python-Levenshtein** - String similarity calculations
- **pandas** - Data manipulation
- **numpy** - Numerical operations
- **multiprocessing** - Parallel processing
- **faker** - Synthetic data generation
- **jupyter** - Interactive notebooks

## Use Cases

✓ **Record Linkage:** Identify duplicate records in databases  
✓ **Data Quality:** Detect data entry errors and inconsistencies  
✓ **Privacy Compliance:** GDPR and HIPAA-compliant de-identification  
✓ **Customer Data:** Merge customer information from multiple sources  
✓ **Research:** Anonymize sensitive research datasets  
✓ **Fraud Detection:** Identify similar but intentionally modified records  

## Outputs & Results

### Fuzzy Matching Output
- DataFrame with matched records
- Similarity scores for each match
- Original and matched values for verification

### De-identified Output
- Clean dataset with PII removed
- Preserved analytical variables
- Maintains data integrity for analysis

## Performance Considerations

- **Parallelization:** Scales with number of CPU cores
- **Memory Usage:** Handle large datasets efficiently
- **Matching Threshold:** Balance between precision and recall
- **Processing Time:** Improves with parallel execution

---
*This fuzzy matching project demonstrates essential data quality management techniques: record linkage, duplicate detection, and privacy-preserving de-identification for real-world data scenarios.*
