import numpy as np
import pandas as pd
from scipy import stats
import statistics
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import sys
import glob
import time

import json
from datetime import datetime, timedelta

from sklearn.datasets import load_iris

plt.style.use('default')

filepath = sys.argv[1]
generate_full_report = True if sys.argv[2] == "True" else False
time_series = sys.argv[3]

# Make figures folder
path = "artifacts/figures"
if not os.path.exists(path):
   os.makedirs(path)

# Clear figures folder
files = glob.glob(f'{path}/*')
for f in files:
    os.remove(f)

# colors
c_good = '#026E54'
c_medium = '#FAA201'
c_poor = '#CF3C66'
c_neutral = '#4A5FF0'

def to_headline_format(s, link=False):
    """
    input: string s: arbitrary column name, e.g. 'sepal width (cm)'
    if link==False: returns nice headline title without special characters, e.g. 'sepal width cm'
    else: returns same headline but in link format, e.g. 'sepal-width-cm'
    """
    for character in ['(', ')', '[', ']', '#', '+', '-', '*', '%', '$', '€']:
        s = s.replace(character,'')
    for character in ['_', ',', '/']:
        s = s.replace(character, ' ')
    s = s.replace('³', '3').replace('²', '2')
    if link:
        return s.lower().replace(' ', '-')
    else:
        return s

# example data
if filepath == "default_non_time_series":
    # Load non time series data
    time_series = False
    data = load_iris(as_frame=True)
    df = data['data']
    # Modify non time series data (make it dirty)
    df.loc[2][1] = np.nan
    df = df.append({"sepal length (cm)": 5.9, "sepal width (cm)": 3.0, "petal length (cm)": 5.1, "petal width (cm)": 1.8}, ignore_index=True)
    df = df.append({"sepal length (cm)": 5.9, "sepal width (cm)": 3.0, "petal length (cm)": 5.1, "petal width (cm)": 1.7}, ignore_index=True)
    df["petal length duplicate (cm)"] = df["petal length (cm)"]
    df["petal width duplicate (cm)"] = df["petal width (cm)"]
    df["grade"] = df["sepal length (cm)"]
    df["grade_incomplete"] = df["sepal length (cm)"]
    df["grade"][df["grade"] < 5] = "C"
    df["grade_incomplete"][df["grade_incomplete"] < 5] = "True"
    df["grade"][df["grade"] != "C"] = "B"

# example data, Time-series
elif filepath == "default_time_series":
   # Load time series data
   time_series = "date"
   time_delta = "minutes" # seconds, minutes, hours or days
   time_delta_value = 5
   df = pd.read_csv("https://raw.githubusercontent.com/erium/halerium-example-data/main/outlier_detection/art_daily_jumpsup.csv", parse_dates=True, index_col=time_series)
   # Modify time series data (make it dirty)
   df['datetime'] = df.index.copy()
   df['datetime'].apply(lambda x: str(x))
   df['value'][-200:] = 2000
   df['string'] = 'Yes'
   df['bool'] = True
   df['string'][0] = True

# real-life data
else:
    time_series = False
    #time_delta = "minutes" # seconds, minutes, hours or days
    #time_delta_value = 1
    #df = pd.read_csv('data/data_AZO.csv')
    #df = pd.read_csv('data/data_MES.zip')
    df = pd.read_csv('data/' + filepath)

if generate_full_report:
    data_dict = {
        "full_report": True,
        "global": {
            "totalRows": 0,
            "totalColumns": 0,
            "completeRows": 0,
            "percentageCompleteRows": 0,
            "unusableRows": [], # list of indices with nans or wrong types
            "duplicatedRows": [], # list of tuples of indices
            "duplicatedColumns": [], # list of tuples of column names
            "correlatedColumns": [], # list of tuples of column names
            "timeliness": [] if time_series else None, # [date of oldest entry, date of newest entry, date of today, regularity, up-to-date-ness]
            "correlationShift": [] if time_series else None,
        },
        "time-series": time_series,
        "is_time_series_index": None,
        "figures": {}
    }

    for col in df.columns:
        data_dict[col] = {
            "totalCount": 0,
            "mainType": None,
            "allTypes": {'float': 0, 'int': 0, 'bool': 0, 'str': 0, 'datetime': 0, 'nan': 0},
            "otherTypes": {'convertable': {'str': 0}, 'non-covertable': {'str': 0, 'nan': 0}},
            "usableCount": 0,
            "numUnique": 0,
            "exampleValues": [], # :list of 5 randomly chosen values
            "exampleNonMainType": [], # to check if something has wrong type by accident
            "statistics": [], # if numerical [mean, std, min, median, max]
            "accumulatedValues": [], # cumulative sum
            "outlierValues": [],
            "timeRole": {"data shift": None, "jumps": None, "biggest_no_shift": None, "biggest_no_jump": None}
        }

if not generate_full_report:
    data_dict = {
        "full_report": False,
        "global": {
            "totalRows": 0,
            "totalColumns": 0,
            "completeRows": 0,
            "percentageCompleteRows": 0,
            "unusableRows": [], # list of indices with nans or wrong types
            "duplicatedRows": [], # list of tuples of indices
            "duplicatedColumns": [], # list of tuples of column names
            "correlatedColumns": [], # list of tuples of column names
            "timeliness": [] if time_series else None, # [date of oldest entry, date of newest entry, date of today, up-to-date-ness]
        },
        "time-series": time_series,
        "is_time_series_index": None,
        "figures": {}
    }

    for col in df.columns:
        data_dict[col] = {
            "totalCount": 0,
            "mainType": None,
            "mixedType": None,
            "usableCount": 0,
            "numUnique": 0,
            "exampleValues": [], # :list of 5 randomly chosen values
            "statistics": [], # if numerical [mean, std, min, median, max]
            "accumulatedValues": [], # cumulative sum
        }

# Threshold for correlation
corr_threshold = 0.85

# Num std threshold for correlation shift
corr_shift_std_threshold = 3

# Total rows and cols
data_dict['global']['totalRows'] = df.shape[0]
data_dict['global']['totalColumns'] = df.shape[1]

# Complete Rows and Percentage complete rows
complete_rows = df.dropna().shape[0]
data_dict['global']['completeRows'] = complete_rows

percentage_complete_rows = complete_rows/df.shape[0] * 100
data_dict['global']['percentageCompleteRows'] = percentage_complete_rows

# Cleaning
def list_to_tuples(l):
    if isinstance(l, np.ndarray) or isinstance(l, list):
        return tuple(l)
    else:
        return l

def str_to_float(s):
    if isinstance(s, str):
        try:
            s = float(s)
        except:
            pass
    return s
    

df = df.applymap(lambda x: list_to_tuples(x))
# convert to numeric if possible
df = df.apply(lambda x: str_to_float(x))

# Get list of tuples of duplicate columns
def getDuplicateColumns(df):
    if len(df.columns) == 1:
        return []
    duplicateColumns = []
    # Iterate over all the columns in dataframe
    for x in range(df.shape[1]):
        duplicateColumnNames = set()
        # Select column at xth index.
        col = df.iloc[:, x]
        # Iterate over all the columns in DataFrame from (x+1)th index till end
        for y in range(x + 1, df.shape[1]):
            # Select column at yth index.
            otherCol = df.iloc[:, y]
            # Check if two columns at x, y index are equal
            if col.equals(otherCol):
                duplicateColumnNames.add(df.columns.values[x])
                duplicateColumnNames.add(df.columns.values[y])
        if duplicateColumnNames:
            duplicateColumns.append(tuple(duplicateColumnNames))
    return duplicateColumns

# Duplicated rows and cols

data_dict['global']['duplicatedRows'] = (df.loc[df.duplicated(keep=False)].reset_index()).groupby(list(df.columns))['index' if not df.index.name else df.index.name].apply(tuple).tolist() if len(df.columns) > 1 else []
data_dict['global']['duplicatedColumns'] = getDuplicateColumns(df)

# Return tuples of column names which are correlated within corr_threshold
def correlation(dataset, threshold):
    corr_matrix = df.corr().abs()
    output = []
    for i in range(len(corr_matrix.columns)):
        current = set()
        for j in range(i):
            if (corr_matrix.iloc[i, j] >= threshold):
                colname = corr_matrix.columns[i]
                if colname in dataset.columns:
                    output.append((corr_matrix.columns[j], corr_matrix.index[i]))
    return output

data_dict['global']['correlatedColumns'] = correlation(df, corr_threshold)

# Splits the dataset into 20 chunks and compares the correlation between features between each chunk
def get_corr_shift(df, std_threshold):
    cols = df.select_dtypes(include=np.number).columns.tolist()
    if len(cols) <= 1:
        return []

    chunks = np.array_split(df, 20)
    corr_matrices = []
    for chunk in chunks:
        corr_matrices.append(chunk.corr())

    corr_mean_std = {}
    for i, col in enumerate(cols):
        corr_mean_std[col] = {}
        for j in range(i+1, len(cols)):
            corrs = []
            j_col = cols[j]
            for k, chunk in enumerate(chunks):
                corrs.append(corr_matrices[k][col][j_col])
            mean = sum(corrs) / len(corrs)
            std = statistics.stdev(corrs)
            corr_mean_std[col][j_col] = (mean, std)

    corr_shift_columns = []
    for k, chunk in enumerate(chunks):
        for i, col in enumerate(cols):
            for j in range(i+1, len(cols)):
                correlation = corr_matrices[k][col][j_col]
                corr_mean, corr_std = corr_mean_std[col][j_col]
                if correlation > corr_mean + std_threshold * corr_std or correlation < corr_mean - std_threshold * corr_std:
                    corr_shift_columns.append((col, j_col))

    return corr_shift_columns

if time_series:
    # Check if specified time series index is convertable to time series
    try:
        df.index = pd.to_datetime(df.index, errors='raise')
        data_dict["is_time_series_index"] = True
        print("Index convertable to time series")
    except:
        data_dict["is_time_series_index"] = False
        print("Index not convertable to time series")

    time_index = df.index
    time_index = time_index.sort_values()
    now = datetime.now()
    # dd/mm/YY H:M:S
    dt_string = now.strftime('%Y-%m-%d %H:%M:%S')
        
    uptodate_fraction = (time_index[-1] - time_index[0]) / (now - time_index[-1])
    
    if generate_full_report:
        # Calculate regularity by finding gaps
        df_copy = df.copy()
        df_copy['dates'] = df_copy.index

        # Take the diff of the first column (drop 1st row since it's undefined)
        deltas = df_copy['dates'].diff()

        # Filter diffs (here days > 1, but could be seconds, hours, etc)
        if time_delta == "seconds":
            gaps = deltas[deltas > timedelta(seconds=time_delta_value)]
        elif time_delta == "minutes":
            gaps = deltas[deltas > timedelta(minutes=time_delta_value)]
        elif time_delta == "hours":
            gaps = deltas[deltas > timedelta(hours=time_delta_value)]
        elif time_delta == "days":
            gaps = deltas[deltas > timedelta(days=time_delta_value)]

        # Print results
        print(f'{len(gaps)} gaps with average gap duration: {gaps.mean()}')

        # Gaps/Rows
        regularity = 1 - len(gaps) / df.shape[0]

        timeliness = [str(time_index[0]), str(time_index[-1]), dt_string, regularity, uptodate_fraction]
    
    else:
        timeliness = [str(time_index[0]), str(time_index[-1]), dt_string, uptodate_fraction]

    data_dict['global']['timeliness'] = timeliness

    
    # Plotting the histogram of values at each timestamp interval
    title = 'Number of Collected Data Points over Time'
    filename = 'artifacts/figures/timestamp.png'
    fig, ax = plt.subplots(1,1, figsize=(8,8))
    fig.autofmt_xdate(rotation=45)
    ax.hist(df.index, bins=20, rwidth=0.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    ax.title.set_text(title)
    ax.set(ylabel="data points collected")
    plt.savefig(filename, bbox_inches="tight")
    data_dict['figures'][title] = filename
    plt.show()
    #plt.clf()

    # Correlation Shift
    if generate_full_report:
        corr_shift = get_corr_shift(df, corr_shift_std_threshold)
        data_dict['global']['correlationShift'] = corr_shift

def isint(string):
    try:
        int(string)
        return True
    except ValueError:
        return False

def isfloat(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

def get_type_count(column):
    type_count = {'float': 0, 'int': 0, 'bool': 0, 'str': 0, 'datetime': 0, 'nan': 0}
    other_types = {'convertable': {'int': 0, 'float': 0, 'bool': 0}, 'non-convertable': {'str': 0, 'nan': 0}}
    unusable_rows = []
    for i, value in enumerate(column):
        if type(value) == type(None) or pd.isna(value):
            type_count['nan'] += 1
            other_types['non-convertable']['nan'] += 1
            unusable_rows.append(column.index[i])
        elif (type(value) is datetime) or (type(value) is pd.Timestamp):
            type_count['datetime'] += 1
        elif type(value) == type(0.1):
            type_count['float'] += 1
        elif type(value) == type(1):
            type_count['int'] += 1
        elif type(value) == type(True):
            type_count['bool'] += 1
        elif type(value) == type("String"):
            type_count['str'] += 1
            if isint(value):
                other_types['convertable']['int'] += 1
            elif isfloat(value):
                other_types['convertable']['float'] += 1
            elif value in ['True', 'False']:
                other_types['convertable']['bool'] += 1
            else:
                other_types['non-convertable']['str'] += 1

    return type_count, other_types, unusable_rows

def get_non_maintype_rows(column, main_type):
    non_maintyp_rows = []
    non_maintyp_examples = []
    for i, value in enumerate(column):
        if main_type=='datetime':
            if not ((type(value) is datetime) or (type(value) is pd.Timestamp)):
                non_maintyp_rows.append(i)
                non_maintyp_examples.append(value)
        elif main_type =='str':
            if not type(value) == str:
                non_maintyp_rows.append(i)
                non_maintyp_examples.append(value)
        elif (main_type != 'nan' and type(value) != eval(main_type)) or (main_type=='nan' and not np.isnan(value)):
            non_maintyp_rows.append(i)
            non_maintyp_examples.append(value)
        elif main_type != 'nan' and np.isnan(value):
            non_maintyp_rows.append(i)
            non_maintyp_examples.append(value)
    # make examples unique
    non_maintyp_examples = list(set(non_maintyp_examples))
    non_maintyp_examples = [str(x) if (type(x) is datetime) or (type(x) is pd.Timestamp) else x for x in non_maintyp_examples]
    return non_maintyp_rows, non_maintyp_examples


def get_data_shift(column):
    column = column.sort_index()
    chunks = np.array_split(column, 20)
    std = column.std()
    mean_std = []
    for chunk in chunks:
        mean_std.append([chunk.mean(), chunk.std()])
    for i, i_stat in enumerate(mean_std):
        i_mean = i_stat[0]
        i_std = i_stat[1]
        for j, j_stat in enumerate(mean_std):
            if i == j:
                continue
            j_mean = j_stat[0]
            j_std = j_stat[1]

            if j_mean > i_mean + 3 * std or j_mean < i_mean - 3 * std:
                return True
    return False

def get_biggest_no_data_shift(column):
    column = column.sort_index()
    chunks = np.array_split(column, 20)
    biggest_no_shift = None
    start = 0
    for i, chunk in enumerate(chunks[1:]):
        current_std = chunk.std()
        if chunk.mean() > chunks[i].mean() + 3 * current_std or chunk.mean() < chunks[i].mean() - 3 * current_std:
            if i - start > 1:
                if not biggest_no_shift or i - start > biggest_no_shift[1]:
                    biggest_no_shift = [(df.index.get_loc(chunks[start].index[0]), df.index.get_loc(chunks[i].index[-1])), i - start]
            start = i
    return biggest_no_shift

def get_jumps(column):
    std = column.std()
    biggest_no_jump = None
    has_jump = False
    start = 0
    for i, value in enumerate(column[1:]):
        if value > column[i] + 3 * std or value < column[i] - 3 * std:
            if i - start > 1:
                if not biggest_no_jump or i - start > biggest_no_jump[1]:
                    biggest_no_jump = [(start, i), i-start]
            start = i
            has_jump = True
    return has_jump, biggest_no_jump

# times
times_dict = {f't{i+1}': [] for i in range(20)}

total_unusable_rows = []
column_usability = {'good': 0, 'medium': 0, 'poor': 0}

all_duplicated_columns = [item for sublist in data_dict['global']['duplicatedColumns'] for item in sublist]
already_accounted_for = []

for col in df.columns:
    t1=t2=t3=t4=t5=t6=t7=t8=t9=t10=t11=t12=t13=t14=t15=t16=t17=t18=t19=t20 = None

    data_dict[col]["totalCount"] = len(df[col])

    if generate_full_report:
        t1 = time.time()
        type_count, other_types, unusable_rows = get_type_count(df[col])
        t2 = time.time()
        main_type = max(type_count, key=type_count.get)
        t3 = time.time()
        non_maintyp_rows, non_maintyp_examples = get_non_maintype_rows(df[col], main_type)
        t4 = time.time()

        total_unusable_rows.extend(unusable_rows)
        total_unusable_rows.extend(non_maintyp_rows)
        t5 = time.time()
    else:
        t1 = time.time()
        df_type = df[col].apply(type)
        type_counts = df_type.value_counts()
        main_type = type_counts.idxmax()
        t2 = time.time()
        for i, row in enumerate(list(df_type)):
            if row != main_type:
                total_unusable_rows.append(i)
        t3 = time.time()
        mixed_type = len(type_counts) > 1
        usable_rows = int(max(type_counts))
        main_type = main_type.__name__
        t4 = time.time()
        if main_type == "Timestamp":
            main_type = "datetime"
        t5 = time.time()
                
    
    unique_values = df[col].unique()
    unique_values = [_ for _ in unique_values if main_type in str(type(_))]
    t6 = time.time()
    if main_type == 'float': # also sort out nans
        unique_values = [_ for _ in unique_values if not np.isnan(_)]
        if df[col].isna().sum() > df.shape[0]/2:
            main_type = 'nan'
    
    example_values = np.random.choice(unique_values, size=min(5, len(unique_values)), replace=False)
    t7 = time.time()

    if generate_full_report:
        data_dict[col]["mainType"] = max(type_count, key=type_count.get)
        data_dict[col]["allTypes"] = type_count
        data_dict[col]["otherTypes"] = other_types
        data_dict[col]["usableCount"] = type_count[data_dict[col]["mainType"]]
    else:
        data_dict[col]["mainType"] = main_type
        data_dict[col]["mixedType"] = mixed_type
        data_dict[col]["usableCount"] = usable_rows
    data_dict[col]["numUnique"] = df[col].nunique()
    data_dict[col]["exampleValues"] = example_values.tolist()
    t8 = time.time()

    if generate_full_report:
        # examples for entries that could potentially be converted into mainType:
        if len(non_maintyp_examples) <= 5:
            data_dict[col]["exampleNonMainType"] = non_maintyp_examples
        else:
            data_dict[col]["exampleNonMainType"] = pd.Series(non_maintyp_examples).sample(n=5, random_state=1).tolist()

    if pd.to_numeric(df[col].dropna(), errors='coerce').notnull().all():
        mean = df[col].mean()
        std = df[col].std()
        min_value = df[col].min()
        median = df[col].median()
        max_value = df[col].max()
        t9 = time.time()

        try:
            data_dict[col]["statistics"] = [float(mean), float(std), float(min_value), float(median), float(max_value)]
        except:
            TypeError
        t10 = time.time()
        #cumsum = list(df[col].cumsum())
        accumulation_threshold = 0.1 # fraction of values that are allowed to be the same
        t = len(df[col])*accumulation_threshold
        value_counts = df[col].value_counts()
        accumulated = [value_counts.index[_] for _ in range(len(value_counts)) if value_counts.iloc[_]>=t]
        accumulated = [float(_) for _ in accumulated]
        data_dict[col]["accumulatedValues"] = accumulated
        t11 = time.time()
    
        if generate_full_report:
            # Get the threshold
            std_threshold = 3
            try: # TODO debugging with 1st dataset
                data_dict[col]["outlierValues"] = df[col][(np.abs(stats.zscore(df[col])) > std_threshold)].tolist()
            except:
                pass

        # Column usability
        
        if col in all_duplicated_columns and not col in already_accounted_for:
            column_usability['poor'] += 1
            already_accounted_for.append(col)
            # find duplicates of this column
            for sublist in data_dict['global']['duplicatedColumns']:
                if col in sublist:
                    already_accounted_for += list(sublist)
            t12 = time.time()
        else:
            if generate_full_report:
                crit1 = data_dict[col]["otherTypes"]['non-convertable']['nan'] == 0
            else:
                crit1 = True
            crit2 = data_dict[col]["usableCount"] == data_dict[col]["totalCount"]
            t13 = time.time()
            if time_series:
                if generate_full_report:
                    crit3 = data_dict['global']['timeliness'][4] > 0.25 # up to date
                    crit4 = data_dict['global']['timeliness'][3] > 0.4 # regularity
                else:
                    crit3 = data_dict['global']['timeliness'][3] > 0.25
                    crit4 = True
            else:
                crit3 = True
                crit4 = True
            t14 = time.time()
            if generate_full_report:
                crit5 = len(data_dict[col]['outlierValues']) == 0
                crit6 = len(data_dict[col]['accumulatedValues']) == 0
                crit7 = not data_dict[col]['timeRole']['data shift']
                crit8 = not data_dict[col]['timeRole']['jumps']
            else:
                crit5 = True
                crit6 = len(data_dict[col]['accumulatedValues']) == 0
                crit7 = True
                crit8 = True
            if crit1 and crit2 and crit3 and crit4 and crit5 and crit6 and crit7 and crit8:
                column_usability['good'] += 1
            elif data_dict[col]["usableCount"] < 2 * df.shape[1]:
                column_usability['poor'] += 1
            else:
                column_usability['medium'] += 1
            t15 = time.time()


        if time_series:

            fig = plt.figure(figsize=(16, 8))

            # Plot histogram of values
            ax1 = fig.add_subplot(121)
            title = col + ' histogram'
            filename = 'artifacts/figures/' + to_headline_format(col) + '.png'
            ax1.hist(df[col], bins=20, color=c_neutral)
            ax1.title.set_text(title)
            ax1.set(xlabel="value", ylabel="frequency")
            ax1.set_xticklabels(ax1.get_xticks(), rotation = 45)

            # Plot time series
            ax2 = fig.add_subplot(122)
            title = col
            ax2.plot(df[col])
            ax2.title.set_text(title)
            ax2.set(xlabel="time / index", ylabel="value")
            ax2.tick_params(axis='x', rotation=45)
            plt.savefig(filename, bbox_inches="tight")
            data_dict['figures'][title] = filename
            plt.clf()
            #plt.show()

            if generate_full_report:
                # Data Shift
                data_shift = get_data_shift(df[col])
                biggest_no_shift = get_biggest_no_data_shift(df[col])
                data_dict[col]["timeRole"]['data shift'] = data_shift
                data_dict[col]["timeRole"]['biggest_no_shift'] = biggest_no_shift

                # Jumps
                jumps, biggest_no_jump = get_jumps(df[col])
                data_dict[col]["timeRole"]['jumps'] = jumps
                data_dict[col]["timeRole"]['biggest_no_jump'] = biggest_no_jump
        else:
            fig = plt.figure(figsize=(9, 6))
            # Plot histogram of values
            title = col
            filename = 'artifacts/figures/' + to_headline_format(col) + '.png'
            try: # TODO debug
                if not all([np.isnan(_) for _ in df[col]]):
                    plt.hist(df[col], bins=20, color=c_neutral)
            except: 
                pass
            plt.title(title)
            plt.xlabel('value')
            plt.ylabel('frequency')
            plt.tight_layout()
            plt.savefig(filename, bbox_inches="tight")
            data_dict['figures'][title] = filename
            plt.clf()
            #plt.show()
        t16 = time.time()

    # Not numerical 
    else:
        fig = plt.figure(figsize=(9, 6))
        colors = ['#4A5FF0', '#00FF69', '#181754', '#FAA201', '#060641', '#353592', '#026E54', '#192465', '#CF3C66', '#002A43', '#DBDCFA']

        pie_df = pd.DataFrame(df[col].value_counts()).sort_values(col, ascending = False)

        # Top 10
        Nmax = 10
        pie_df2 = pie_df[:Nmax].copy()

        # Others
        if pie_df.shape[0] > Nmax:
            new_row = pd.DataFrame(data = {pie_df[col][Nmax:].sum()}, index=[str(pie_df.shape[0] - Nmax) + ' other values'], columns=[col])
            pie_df2 = pd.concat([pie_df2, new_row])

        # Plot pie chart of values
        title = col
        filename = 'artifacts/figures/' + to_headline_format(col) + '.png'
        labels = pie_df2.index
        plt.pie(pie_df2[col], labels=labels, colors=colors[:len(labels)])
        plt.title(title)
        legend = list(df[col].value_counts().index)
        if len(legend) >= Nmax:
            legend = legend[:Nmax+1]
            legend[-1] = 'others'
        plt.legend(legend, loc="best")
        plt.tight_layout()
        plt.savefig(filename)
        data_dict['figures'][title] = filename
        plt.clf()
        #plt.show()
    t17 = time.time()

    for _ in range(20):
        times_dict[f't{_+1}'].append(eval(f't{_+1}'))

    # for _ in range(20):
    #     if not eval(f't{_+1}') is None and not eval(f't{_+2}') is None:
    #         print(f'    t{_+1} to t{_+2}: ', round(eval(f't{_+2}') - eval(f't{_+1}'), 2))

total_unusable_rows = list(set(total_unusable_rows))
data_dict["global"]["unusableRows"] = total_unusable_rows

# the same figure for both subplots
fig = plt.figure(figsize=(12, 9))

# axes object for the first pie chart 
# fig.add_subplot(121) will create a grid of subplots consisting 
# of one row (the first 1 in (121)), two columns (the 2 in (121)) 
# and place the axes object as the first subplot 
# in the grid (the second 1 in (121))
ax1 = fig.add_subplot(121)

# plot the first pie chart in ax1
labels = ['usable rows: ' + str(df.shape[0] - len(total_unusable_rows)), 'unusable rows: ' + str(len(total_unusable_rows))]
sizes = [df.shape[0] - len(total_unusable_rows), len(total_unusable_rows)]
colors = (c_good, c_poor)
patches, texts = ax1.pie(sizes, colors=colors)
ax1.legend(patches, labels)
ax1.title.set_text('Row Usability')

# axes object for the second pie chart 
# fig.add_subplot(122) will place ax2 as the second 
# axes object in the grid of the same shape as specified for ax1 
ax2 = fig.add_subplot(122)

# plot the sencond pie chart in ax2
labels = ['good: ' + str(column_usability['good']), 'medium: ' + str(column_usability['medium']), 'poor: ' + str(column_usability['poor'])]
sizes = [str(column_usability['good']), str(column_usability['medium']), str(column_usability['poor'])]
colors = (c_good, c_medium, c_poor)
patches, texts = ax2.pie(sizes, colors=colors)
ax2.legend(patches, labels)
ax2.title.set_text('Column Usability')

filename = 'artifacts/figures/global_pie.png'
plt.savefig(filename)
data_dict['figures']['global_pie'] = filename
#plt.clf()
plt.show()

with open("artifacts/sample.json", "w") as outfile:
    json.dump(data_dict, outfile, indent = 4)
