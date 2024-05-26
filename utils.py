import pandas as pd
import numpy as np
import datetime
from joblib import Parallel, delayed
from alive_progress import alive_bar
from tqdm import tqdm
from faker import Faker
from thefuzz import fuzz, process
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import random
import string
import dask
from dask import delayed, compute
from dask.diagnostics import ProgressBar



def generate_synthetic_data(n, column_types):
    """
    Generate synthetic data for a given number of rows and column types.

    Parameters
    ----------
    n : int
        The number of rows to generate synthetic data for.
    column_types : dict
        A dictionary mapping column names to Faker column types.

    Returns
    -------
    df : pandas.DataFrame
        A pandas DataFrame containing the synthetic data.

    Notes
    -----
    The synthetic data is generated using the Faker library and includes random values for each column.
    The column types are specified in the column_types dictionary, which maps column names to Faker column types.
    """
    
    fake = Faker()
    data = {col: [getattr(fake, col_type)() for _ in range(n)] for col, col_type in column_types.items()}
    df = pd.DataFrame(data)

    return df


def generate_column_data(col_type, n):
    """
    Generate synthetic data for a given column type and number of rows.

    Parameters
    ----------
    col_type : str
        The type of data to generate (e.g. "text", "name", "email", etc.).
    n : int
        The number of rows to generate.

    Returns
    -------
    data : list
        A list of synthetic data values.

    Notes
    -----
    The synthetic data is generated using the Faker library and includes random values for the specified column type.
    The column type is specified in the col_type parameter, which should be a string matching a Faker column type.
    """
    fake = Faker()
    return [getattr(fake, col_type)() for _ in range(n)]


def generate_synthetic_data_parallelized(n, column_types):
    """
    Generate synthetic data using Faker library based on specified column types.

    Parameters:
    n: integer number of synthetic data rows to generate.
    column_types (dict): Dictionary where keys are column names and values are Faker providers.

    Returns:
    pd.DataFrame: DataFrame containing synthetic data.
    """
    fake = Faker()
    num_workers = multiprocessing.cpu_count()
    results = {}
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_col = {executor.submit(generate_column_data, col_type, n): col for col, col_type in column_types.items()}
        for future in as_completed(future_to_col):
            col = future_to_col[future]
            try:
                results[col] = future.result()
            except Exception as e:
                print(f"Error generating data for column {col}: {e}")

    df = pd.DataFrame(results)
    return df


def generate_synthetic_data_dask(n, column_types):
    """
    Generate synthetic data using Faker library based on specified column types.
    
    Parameters:
    n (int): Number of synthetic data rows to generate.
    column_types (dict): Dictionary where keys are column names and values are Faker providers.
    
    Returns:
    pd.DataFrame: DataFrame containing synthetic data.
    """
    results = {}
    
    tasks = {col: delayed(generate_column_data)(col_type, n) for col, col_type in column_types.items()}
    
    # Compute the tasks in parallel
    with ProgressBar():
        computed_results = compute(*tasks.values())
    
    for col, data in zip(tasks.keys(), computed_results):
        results[col] = data
    
    df = pd.DataFrame(results)
    return df


def replace_nth_character(original_string):
    """
    Replace the nth character in a given string with a random character.

    Parameters
    ----------
    original_string : str
        The original string to modify.

    Returns
    -------
    modified_string : str
        The modified string with the nth character replaced.

    Notes
    -----
    The nth character is chosen randomly from the string, and a random character from the alphabet is used to replace it.
    The original string is modified in-place.
    """

    original_string = str(original_string)
    # if len(original_string) ==1
    n = random.randint(0, len(original_string) - 1)
    new_character = random.choice(string.ascii_letters)
    modified_string = original_string[:n] + new_character + original_string[n + 1:]
    return modified_string

@delayed
def modify_row(df):
    """
    Modify a random row in a given DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to modify.

    Returns
    -------
    new_row : pandas.Series
        The modified row.

    Notes
    -----
    A random row is chosen from the DataFrame, and a random column is chosen from the columns.
    The nth character of the chosen column is replaced with a random character.
    The modified row is returned as a pandas Series.
    """
    row_idx = random.randint(0, df.shape[0] - 1)
    col = random.choice(df.columns)

    new_row = df.iloc[row_idx].copy()
    new_row[col] = replace_nth_character(df.at[row_idx, col])
    return new_row


def modify_dataframe_dask(df, n):
    """
    Randomly pick a row and a single column of the DataFrame,
    replace a character with another random character, and append it to a new DataFrame.
    Repeat the process n times and return the new DataFrame.

    Parameters:
    df (pd.DataFrame): Input DataFrame.
    n (int): Number of modifications to make.

    Returns:
    pd.DataFrame: New DataFrame with modified rows.
    """
    
    new_df = pd.DataFrame(columns=df.columns)

    tasks = [delayed(modify_row)(df) for _ in range(n)]
    # Compute the tasks in parallel
    with ProgressBar():
        results = compute(*tasks)
    
    # Append the results to the new DataFrame
    for result in results:
        new_df.loc[len(new_df)] = result
        
    return new_df


def concatenate_and_shuffle(df1, df2):
    """
    Concatenate two DataFrames and shuffle the rows.

    Parameters
    ----------
    df1 : pandas.DataFrame
        The first DataFrame to concatenate.
    df2 : pandas.DataFrame
        The second DataFrame to concatenate.

    Returns
    -------
    shuffled_df : pandas.DataFrame
        The concatenated and shuffled DataFrame.

    Notes
    -----
    The two input DataFrames are concatenated ignoring the index.
    The rows of the resulting DataFrame are shuffled randomly.
    The random state is set to 42 for reproducibility.
    """
    
    # Concatenate the DataFrames
    concatenated_df = pd.concat([df1, df2], ignore_index=True)

    # Shuffle the rows of the DataFrame
    shuffled_df = concatenated_df.sample(frac=1, random_state=42).reset_index(drop=True)

    return shuffled_df


def deidentify_data(df):
    """
    Deidentify a DataFrame by replacing sensitive information with fake data.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to deidentify.

    Returns
    -------
    deidentified_df : pandas.DataFrame
        The deidentified DataFrame.

    Notes
    -----
    The 'personal_id' column is added to the DataFrame with fake UUIDs.
    The 'last_name', 'first_name', and 'address' columns are removed from the DataFrame.
    """
    fake = Faker()
    df['personal_id'] = [fake.uuid4() for _ in range(len(df))]
    df = df.drop(columns=['last_name','first_name','address'])
    return df



def match_rows_parallelized(df1, df2, threshold=80):
    """
    Match rows from two DataFrames in parallel.

    Parameters
    ----------
    df1 : pandas.DataFrame
        The first DataFrame to match.
    df2 : pandas.DataFrame
        The second DataFrame to match.
    threshold : int, optional
        The threshold for the match score. Defaults to 80.

    Returns
    -------
    matched_df : pandas.DataFrame
        The matched DataFrame.

    Notes
    -----
    The function uses parallel processing to match rows from the two DataFrames.
    The match score is computed using the FuzzyWuzzy library.
    The matched rows are stored in a new DataFrame.
    """

    matches = []

    with ProcessPoolExecutor() as executor:
        futures = []
        for idx1, row1 in tqdm(df1.iterrows(), total=df1.shape[0], desc="Matching Rows"):
            futures.append(executor.submit(compute_match, row1, df2))
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing Matches"):
            row1 = future.result()
            if row1 is not None:
                row1["score"] = fuzz.ratio(str(row1), str(row1))
                matches.append(row1)

    colns = list(df1.columns) + ["score"]
    matched_df = pd.DataFrame(matches, columns=colns)

    return matched_df

def compute_match(row1, df2):
    """
    Compute the match score between a row from the first DataFrame and each row from the second DataFrame.

    Parameters
    ----------
    row1 : pandas.Series
        The row from the first DataFrame to match.
    df2 : pandas.DataFrame
        The second DataFrame to match.

    Returns
    -------
    row1 : pandas.Series or None
        The matched row from the first DataFrame, or None if no match is found.

    Notes
    -----
    The function computes the match score between the input row and each row in the second DataFrame.
    The match score is computed using the FuzzyWuzzy library.
    The function returns the matched row if the score is above the threshold, or None if no match is found.
    """
    
    for idx2, row2 in df2.iterrows():
        score = 0
        for col in df2.columns:
            score += fuzz.ratio(str(row1[col]), str(row2[col]))
        if score >= 600:  #threshold * len(df1.columns) / 100:
            return row1
    return None 
