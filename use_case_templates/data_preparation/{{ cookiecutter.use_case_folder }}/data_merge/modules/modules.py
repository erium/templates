import os

import numpy as np
import pandas as pd
from math import isnan

import seaborn as sns
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import LabelEncoder

class Plotter:
    def plot_line(df):
        df.plot(subplots=True, figsize=(8, 2 * len(df.columns)))
        plt.show()

    def plot_box(df):  
        df.boxplot(figsize =(8, 8), grid = False)
        plt.show()

    def show_outliers(df, outliers):
        df_outlier = df.copy()
        df_outlier['outlier'] = 0
        df_outlier['outlier'].loc[outliers.index] = 1
        pairplot_hue = 'outlier'
        palette ={0: "C0", 1: "C3"}
        sns.pairplot(df_outlier, hue = pairplot_hue, palette=palette)
        plt.show()
    
class Importer:
    def import_data(filepaths, sheets, seps, datetime_cols, join):
        if sheets and len(sheets) == 1:
            sheets = [sheets[0] for _ in range(len(filepaths))]
        if seps and len(seps) == 1:
            seps = [seps[0] for _ in range(len(filepaths))]
        if datetime_cols and len(datetime_cols) == 1:
            datetime_cols = [datetime_cols[0] for _ in range(len(filepaths))]

        dfs = []

        for i in range(len(filepaths)):
            filepath = filepaths[i]
            sheet = sheets[i]
            sep = seps[i]
            datetime_col = datetime_cols[i]

            filename, filetype = os.path.splitext(filepath)
            if not filetype:
                raise ValueError(filepath + " has missing extension")

            if filetype == '.csv':
                df = pd.read_csv(filepath)
            elif filetype == '.pkl':
                df = pd.read_pickle(filepath)
            elif filetype == '.xlsx':
                df = pd.read_excel(open(filepath,'rb'), sheet_name=sheet)
            elif filetype == '.zip':
                df = pd.read_csv(filepath)
            elif filetype == '.txt':
                df = pd.read_csv(filepath, sep=sep, header=None)
            elif filetype == '.json':
                df = pd.read_json(filepath)
            else:
                raise ValueError(filepath + " has invalid/unsupported extension")

            if datetime_col:
                df[datetime_col] = pd.to_datetime(df[datetime_col], infer_datetime_format=True)
                df = df.set_index(datetime_col)

            dfs.append(df)

        if join == 'vertical':
            df = pd.concat(dfs)
        elif join == 'inner':
            df = pd.concat(dfs, axis=1, join="inner")
        elif join == 'outer':
            df = pd.concat(dfs, axis=1, join="outer")
        return df
            
            

class PopulationSeparator:
    def separate_populations(df, indexes, label_or_position):
        populations = {}
        for name, index_range in indexes:
            if label_or_position == 'label':
                populations[name] = df.loc[index_range[0]: index_range[1]]
            elif label_or_position == 'position':
                populations[name] = df.iloc[index_range[0]: index_range[1]]
        return populations