import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt 
import io
import sheryanalysis as sh

def get_Summary(df:pd.DataFrame)->str:
    buffer=io.StringIO()
    df.info(buf=buffer)
    shape=df.shape
    columns=df.columns
    info=buffer.getvalue()
    describe=df.describe().to_string()
    head_rows=df.head().to_string()
    tail_rows=df.tail().to_string()
    null_sum=df.isna().sum()
    duplicated_sum=df.duplicated().sum()
    numerical_cols=df.select_dtypes(include="number").columns
    categorical_cols=df.select_dtypes(include="object").columns
    datetime_cols=df.select_dtypes(include="datetime64").columns
    corr=df.corr(numeric_only=True).to_string
    
    smart_summary_str=f"""This is Smart Summary of dataset:\n
    shape:{shape}\n
    columns:{columns}\n
    info:{info}\n
    describe:{describe}\n
    head:{head_rows}\n
    tail:{tail_rows}\n
    null values sum:{null_sum}\n
    duplicated sum:{duplicated_sum}\n
    numerical columns:{numerical_cols}\n
    categorical columns:{categorical_cols}\n
    date time columns:{datetime_cols}\n
    correlation:{corr}\n
    """
    final_summary=smart_summary_str.replace("{","{{").replace("}","}}")
    return final_summary