# Python
#
# This file implements an example.
#
# This file is part of mdutils. https://github.com/didix21/mdutils
#
# MIT License: (C) 2018 Dídac Coll

import sys
import numpy as np
from datetime import date

### DEFINITIONS
c_neutral = 'black'
c_good = 'green'
c_medium = '#FAA201'
c_bad = 'red'
c_hint = '#026E54'

t_row_column_ratio = 2
t_regularity = 0.4
t_timeliness = 0.25
t_unique_values = 4

### READ JSON
import json
with open("artifacts/sample.json", "r") as outfile:
    data = json.load(outfile)

full_report = data['full_report']

# global information
N_rows = int(data['global']['totalRows'])
N_columns = int(data['global']['totalColumns'])
N_complete_rows = int(data['global']['completeRows'])
Percentage_complete_rows = data['global']['percentageCompleteRows']
unusable_rows = data['global']['unusableRows']
c1 = c_good # TODO
c2 = c_medium # TODO
duplicated_rows = data['global']['duplicatedRows']
duplicated_columns = data['global']['duplicatedColumns']
correlated_columns = data['global']['correlatedColumns']
if full_report:
    correlation_shifts = data['global']['correlationShift']
timeliness = data['global']['timeliness'] # number of gaps (seperating two pulses)
if data['time-series']:
    is_time_series_index = data['is_time_series_index']
# timeliness ok
timeliness_ok = True
if full_report:
    if data['time-series'] and data['global']['timeliness'][3] < t_regularity:
        timeliness_ok = False
    if data['time-series'] and data['global']['timeliness'][4] < t_timeliness:
        timeliness_ok = False
else: #  regularity is not accounted for
    if data['time-series'] and data['global']['timeliness'][3] < t_timeliness:
        timeliness_ok = False

# global figures
global_pie = data['figures']['global_pie']
if data['time-series']:
    global_time_histogram = data['figures']['Number of Collected Data Points over Time']

# columns
column_names = list(data.keys())
column_names.remove('global')
column_names.remove('time-series')
column_names.remove('figures')
column_names.remove('full_report')
column_names.remove('is_time_series_index')

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

def convert_file_path(s):
    """converts relative path to absolute one"""
    s = s.replace(' ', '%20')
    s = s + '?download=inline'
    return s


# get columns with problems
problem_counter = 0
column_problems = {column_name: [] for column_name in column_names}
for c in column_names:
    col_data = data[c]
    # mixed types
    if full_report:
        other_types = col_data['allTypes']
        #del other_types[col_data['mainType']]
        sum_other_types = 0
        for t,n in other_types.items():
            if t != col_data['mainType']:
                sum_other_types += n
        if sum_other_types > 0:
            column_problems[c].append('mixed types')
            problem_counter += 1

    # few usable entries
    value = col_data['usableCount']
    percentage = round(value/col_data['totalCount']*100)
    if percentage <= 50:
        column_problems[c].append('few usable entries')
        problem_counter += 1

    # few different values
    value = col_data['numUnique']
    if value < t_unique_values and col_data['mainType'] in ['int', 'float']:
        column_problems[c].append('few different values')
        problem_counter += 1

    # no statistics available
    if (col_data['mainType'] == 'int' or col_data['mainType'] == 'float') and not len(col_data['statistics']) == 5:
        column_problems[c].append('no statistics')
        problem_counter += 1

    # accumulated values
    value = col_data['accumulatedValues']
    if len(value) > 0:
        column_problems[c].append('accumulated values')
        problem_counter += 1

    # outlier values
    if full_report:
        value = col_data['outlierValues']
        if len(value) > 0:
            column_problems[c].append('outlier values')
            problem_counter += 1

    # shift
    if full_report:
        if col_data['timeRole']['data shift']: 
            column_problems[c].append('shift')
            problem_counter += 1

    # jumps 
    if full_report:
        if col_data['timeRole']['jumps']: 
            column_problems[c].append('jumps')
            problem_counter += 1

####################################################################################################################
####################################################################################################################

from mdutils.mdutils import MdUtils
from mdutils import Html

if full_report:
    document_title = 'DATA QUALITY REPORT'
else: 
    document_title = 'DATA QUALITY REPORT - SHORT'
mdFile = MdUtils(file_name='data_quality_report', title=document_title)

mdFile.new_line('---')
mdFile.new_line('title: ' + document_title)
mdFile.new_line('date: ' + str(date.today()))
mdFile.new_line('---')

if len(data['global']['unusableRows'])==0 and len(data['global']['duplicatedColumns'])==0 and len(data['global']['correlatedColumns'])==0 and problem_counter == 0 and timeliness_ok:
    mdFile.new_paragraph("The estimated data quality is **excellent**. The data can be used for analytics and "
                        "machine learning tools without restrictions.")

elif data['global']['totalRows'] - len(data['global']['unusableRows']) < data['global']['totalColumns'] and data['global']['totalColumns']>100:
    mdFile.new_paragraph("The estimated data quality seems **critical**. The data usability for analytics"
                        " and machine learning tools might be severely limited.")

else:
    mdFile.new_paragraph("The estimated data quality is **good**. However, certain aspects should be considered further before"
                        " using the data for analytics and machine learning tools.")

mdFile.new_paragraph()

##################################################################################################################
# OVERVIEW / ONEPAGER
##################################################################################################################

mdFile.new_header(level=1, title="OVERVIEW")

mdFile.new_header(level=2, title="GENERAL INFORMATION")

mdFile.new_line('If there are warnings, please follow the links and recommendations.')
mdFile.new_line()
mdFile.new_line(f'- Total number of rows: {N_rows}, thereof {round((N_rows - len(unusable_rows))/N_rows*100, 2)}% complete and usable.', color=c_neutral)
mdFile.new_line(f'- Total number of columns: {N_columns}', color=c_neutral)
if N_rows/N_columns <= t_row_column_ratio: 
    mdFile.new_line(f'    WARNING: There are too few rows compared to the number of columns. Please use only a subset of columns in further machine learning projects and make sure you have at least as many rows as columns, better twice as many rows as columns. See section "3.2 Only keep specific columns" in the data_cleaning template.', color=c_medium)
if len(duplicated_rows)>0:
    N_duplicated_rows = int(len([index for tuple in duplicated_rows for index in tuple])/2)
    mdFile.new_line(f'\n- WARNING: There are {N_duplicated_rows} duplicated rows. Please delete the duplicates. See [duplications](#duplications)', color=c_medium)
if len(duplicated_columns)>0:
    N_duplicated_columns = int(len([index for tuple in duplicated_columns for index in tuple])/2)
    mdFile.new_line(f'\n- WARNING: There are {N_duplicated_columns} duplicated columns.Please delete the duplicates. See [duplications](#duplications)', color=c_medium)
if len(correlated_columns)>0:
    N_correlated_columns = int(len([index for tuple in correlated_columns for index in tuple])/2)
    mdFile.new_line(f'\n- WARNING: There are {N_correlated_columns} highly correlated columns. For more advice see [correlations](#correlations)', color=c_medium)

if data['time-series']:
    mdFile.new_line(f'- Data was collected between {timeliness[0]} and {timeliness[1]}. ', color=c_neutral)
    if full_report:
        if len(correlation_shifts)>0:
            mdFile.new_line(f'\n- WARNING: A shift of correlations was detetcted. For more advice see [correlation shift](#correlation-shift)', color=c_medium)
        if timeliness[3] < t_regularity: 
            mdFile.new_line(f'\n- WARNING: Data was not collected steadily, there have been multiple gaps. Please make sure the data is still applicable and does not miss important parts. You might consider splitting the dataset and using only parts of it that have no gaps, see section "3.1 Use slice of dataframe" in the data_cleaning template', color=c_medium)
        if timeliness[4] < t_timeliness:
            mdFile.new_line(f'\n- WARNING: Data might not be up-to-date anymore. Please ensure that the data is still applicable, i.e. the process has not changed substantially since the data was collected.', color=c_medium)    
    else:
        if timeliness[3] < t_timeliness:
            mdFile.new_line(f'\n- WARNING: Data might not be up-to-date anymore. Please ensure that the data is still applicable, i.e. the process has not changed substantially since the data was collected.', color=c_medium)    
    if not is_time_series_index:
            mdFile.new_line(f'\n- WARNING: The column, which is assumed to be the time stamp is not convertable into any time format and will be kept as it is. Some of the following figures might therefore contain non-time-objects on their time axis.', color=c_medium)    

for c in column_names:
    # combine entries for each column
    combined_entry = ''
    for entry in column_problems[c]:
        combined_entry += entry + ', '
    combined_entry = combined_entry[:-2]
    column_problems[c+'_combined'] = combined_entry

if problem_counter > 0:
    mdFile.new_line()
    mdFile.new_header(level=2, title="PROBLEMATIC COLUMNS")
    mdFile.new_line('Please follow the links for more information and recommendations.')
    mdFile.new_line()
    for c in column_names:
        if len(column_problems[c+'_combined'])>0:
            mdFile.new_line(f"- [{c}](#{to_headline_format(c, link=True)}) <font color={c_medium}> WARNING: {column_problems[c+'_combined']} found. </font>")

mdFile.new_line()
mdFile.new_header(level=2, title="USABILITY")
mdFile.new_paragraph(Html.image(path=convert_file_path(global_pie), size='800x600', align='center'))
if data['time-series']: 
    mdFile.new_paragraph(Html.image(path=convert_file_path(global_time_histogram), size='600x550', align='center'))
    mdFile.new_paragraph('The figure above shows how many datapoints were collected at which point in time. The more evenly distributed the bars are, the better and more uniform the data have been collected. If there are gaps, please be careful and double check the applicability of the data to your case.')
    if data['global']['timeliness'][3] < t_regularity:
        mdFile.new_paragraph('WARNING: data might not have been collected at regular intervals.')
mdFile.new_line()


##################################################################################################################
# Details 
##################################################################################################################
if len(duplicated_rows)>0 or len(duplicated_columns)>0 or len(correlated_columns)>0:
    mdFile.new_header(level=1, title="DUPLICATIONS AND CORRELATIONS")

    if len(duplicated_rows)>0 or len(duplicated_columns)>0:
        mdFile.new_header(level=2, title="DUPLICATIONS")

    if len(duplicated_rows)>0:
        mdFile.new_paragraph(f"There are {N_duplicated_rows} duplicated rows in the dataset. Please only keep one row each for further use of the data set.")
        mdFile.new_line()
        items = []
        to_be_deleted_rows = []
        for t in duplicated_rows:
            first_element = t[0]
            other_elements = list(t)
            other_elements.remove(first_element)
            other_elements_str = ''
            for e in other_elements:
                other_elements_str += str(e)+', '
                to_be_deleted_rows.append(e)
            other_elements_str = other_elements_str[:-2]
            item = f'Row {first_element} has exact duplicates: {other_elements_str}.'
            items.append(item)
        mdFile.new_list(items)
        mdFile.new_line()
        mdFile.new_line('___')
        mdFile.new_line()
        mdFile.new_line(f'<font color={c_hint}> Hint: To remove all duplicated rows use `df.drop({to_be_deleted_rows}, inplace=True)` [(learn more)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop.html) <font color=black>')
        mdFile.new_line()
        mdFile.new_line('___')

    if len(duplicated_columns)>0:
        mdFile.new_paragraph(f"There are {N_duplicated_columns} duplicated columns in the dataset. Please only keep one column each for further use of the data set.")
        mdFile.new_line()
        items = []
        to_be_deleted_columns = []
        for t in duplicated_columns:
            first = t[0]
            first_element = "``" + str(t[0]) + "``"
            other_elements = list(t)
            other_elements.remove(first)
            other_elements_str = ''
            for e in other_elements:
                other_elements_str += "``" + str(e) + "``"+', '
                to_be_deleted_columns.append(e)
            other_elements_str = other_elements_str[:-2]
            item = f'Column {first_element} has exact duplicates: {other_elements_str}.'
            items.append(item)
        mdFile.new_list(items) 
        mdFile.new_line()
        mdFile.new_line('___')
        mdFile.new_line()
        mdFile.new_line(f'<font color={c_hint}> Hint: To remove the duplicated columns use `df.drop({to_be_deleted_columns}, axis=1, inplace=True)` [(learn more)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop.html) <font color=black>')
        mdFile.new_line()
        mdFile.new_line('___')  
        mdFile.new_line()

    if len(correlated_columns)>0:
        mdFile.new_header(level=2, title="CORRELATIONS")
        mdFile.new_line(f"There are {N_correlated_columns} highly correlated columns in the dataset. There are several possible reasons for correlations, which influence the way how to handle them. Please have a closer look into your dataset and choose one of the following options:")
        mdFile.new_line(f"Are the columns duplicates but with small differences? Then check what causes the differences, decide which one is the correct one and delete the other.")
        mdFile.new_line("Are both columns set-values? Then keep in mind that they cannot be considered independent and it will not be possible to distinguish which of the columns has certain effects on dependent variables. However, both columns can be kept in the dataset.")
        mdFile.new_line("Are both columns measured, i.e. dependent values? Then they might be affected by the same causes. This is already an interesting learnin and should be kept in mind. Both columns can be kept.")
        mdFile.new_line("Is one a set-value and the other a measured value? Then you might already have spotted an interesting correlation in the data set. The measured value seems to be dependent on the set value. Both column can be kept.")

        mdFile.new_line()
        items = []
        to_be_deleted_corr_columns = []
        for t in correlated_columns:
            first = t[0]
            first_element = "``" + str(t[0]) + "``"
            other_elements = list(t)
            other_elements.remove(first)
            other_elements_str = ''
            for e in other_elements:
                other_elements_str += "``" + str(e) + "``"+', '
                to_be_deleted_corr_columns.append(e)
            other_elements_str = other_elements_str[:-2]
            item = f'Row {first_element} shows a strong correlation with {other_elements_str}.'
            items.append(item)
        mdFile.new_list(items)
        mdFile.new_line()
        mdFile.new_line('___')
        mdFile.new_line()
        mdFile.new_line(f'<font color={c_hint}> Hint: To remove one or several correlated columns use `df.drop({to_be_deleted_corr_columns}, axis=1, inplace=True)` [(learn more)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop.html) <font color=black>')
        mdFile.new_line()
        mdFile.new_line('___') 
        mdFile.new_line() 
if full_report:
    if not correlation_shifts is None and len(correlation_shifts)>0:
        mdFile.new_header(level=2, title="CORRELATION SHIFT")
        mdFile.new_paragraph(f"For {len(correlation_shifts)} pair(s) of columns a shift of correlation has been detected.")
        items = []
        for t in correlation_shifts:
            first = t[0]
            first_element = "``" + str(t[0]) + "``"
            other_elements = list(t)
            other_elements.remove(first)
            other_elements_str = ''
            for e in other_elements:
                other_elements_str += "``" + str(e) + "``"+', '
            other_elements_str = other_elements_str[:-2]
            item = f'The correlation of {first_element} with {other_elements_str} has changed over time.'
            items.append(item)
        mdFile.new_list(items)
        mdFile.new_paragraph("    This indicates that the behaviour of these columns with respect to each other has changed during the data collection time. "
                                "It might also show that the overall process that generated the data has changed over time and the whole data set should be treated with care. "
                                "You might want to split the data set into phases where no correlation shift appears, see section '3. Separate Mixed Populations' in the data_cleaning template")

##################################################################################################################
# Per Column 
##################################################################################################################

mdFile.new_header(level=1, title="COLUMN INFORMATION")

# Table of content
for column_name in column_names:
    mdFile.new_line(f'\n- [{to_headline_format(column_name)}](#{to_headline_format(column_name, link=True)})')

mdFile.new_line()

# Information
for column_name in column_names:
    mdFile.new_header(level=2, title=to_headline_format(column_name).upper())

    col_data = data[column_name]

    if full_report:
        col_descriptions = ['column name', 'number of counts', 'inferred type', 'other types', 
                        'number of usable values', 'number of unique values', 'example values']
        col_descriptions_num = ['mean', 'std', 'min', 'median', 'max', 'accumulated values', 'outlier values']
    else:
        col_descriptions = ['column name', 'number of counts', 'inferred type', 'mixed types', 
                        'number of usable values', 'number of unique values', 'example values']
        col_descriptions_num = ['mean', 'std', 'min', 'median', 'max', 'accumulated values']

    list_of_strings = ["Description", "Value", "Comment"]

    counter = 0

    hint_dict = {
    'convert_into_main_type_rows': False, 
    'delete_non_main_type_rows': False, 
    'delete_few_value_column': False,
    'delete_accumulated_value_rows': False, 
    'delete_outlier_rows': False,
    'use_slice_shift': False,
    'use_slice_jumps': False 
    }

    for d in col_descriptions:
        comment = ''
        if d == 'column name':
            value = column_name
        if d == 'number of counts':
            value = col_data['totalCount']
        elif d == 'example values':
            value = col_data['exampleValues']
        elif d == 'inferred type':
            value = col_data['mainType']
        elif d == 'mixed types':
            value = col_data['mixedType']
            if value:
                comment = f"<font color={c_medium}> WARNING: there are entries with other types than {col_data['mainType']}. To find out whether or not these entries are convertable to {col_data['mainType']} please use the full report. If they are not, please delete the affected rows. <font>"
                hint_dict['delete_non_main_type_rows'] = True
        elif d == 'other types': # full report only
            other_types = col_data['allTypes']
            #del other_types[col_data['mainType']]
            value = ''
            sum_other_types = 0
            for t,c in other_types.items():
                if c>0 and t != col_data['mainType']:
                    value += f'{c} {t}; '
                    sum_other_types += c
            value = value [:-2]
            if sum_other_types > 0:
                comment = f"WARNING: there were {sum_other_types} entries with other types found. Some examples are {col_data['exampleNonMainType']}."
                # convertable?
                conv_counter = 0
                for conv_t, n in col_data['otherTypes']['convertable'].items():
                    if n > 0:
                        comment += f' {n} of them are convertable into {conv_t}; '
                        conv_counter += n
                if conv_counter > 0:
                    comment = comment[:-2] + '.'
                    comment += ' If values are convertable to the inferred type please do so. All the other values cannot be used, i.e. the corresponsing rows have to be deleted.'
                    hint_dict['convert_into_main_type_rows'] = True
                    hint_dict['delete_non_main_type_rows'] = True
                else:
                    comment += ' None of these entries seem to be convertable into usable values. Please delete the affected rows.'
                    hint_dict['delete_non_main_type_rows'] = True
                comment = f'<font color={c_medium}> ' + comment + '<font color=black>'
            else:
                value = None

        elif d == 'number of usable values':
            value = col_data['usableCount']
            percentage = round(value/col_data['totalCount']*100)
            comment = f'{percentage}% of the entries are usable.'
            if percentage <= 50:
                comment = f'<font color={c_medium}> WARNING: Only {percentage}% of the entries are usable. It might be worth improving the data collection process for these values. <font>'
        elif d == 'number of unique values':
            value = col_data['numUnique']
            if value < t_unique_values and col_data['mainType'] in ['int', 'float']:
                comment = f'<font color={c_medium}> WARNING: there are only {value} different values. Too little variety weakens the trainability and predictive power of Machine Learning models. <font>'
                if value == 1:
                    comment += f'<font color = {c_medium}> Since there is only one value this column does not provide any information and should be deleted.'
                    hint_dict['delete_few_value_column'] = True
                else:
                    comment += f'<font color={c_medium}> You might consider deleting this column.'
                    hint_dict['delete_few_value_column'] = True
        if value != None:
            list_of_strings.extend([d, value, comment])
            counter += 1

    if col_data['mainType'] == 'int' or col_data['mainType'] == 'float':
        for d in col_descriptions_num:
            if any([type(_)==int for _ in col_data['exampleValues']]):
                decimal_digits = 0
            else:
                decimal_digits = int(np.mean([len(str(_).split(".")[1]) for _ in col_data['exampleValues']]))
            comment = ''
            if len(col_data['statistics']) == 5:
                if d == 'mean':
                    value = round(col_data['statistics'][0], decimal_digits)
                if d == 'std':
                    value = round(col_data['statistics'][1], decimal_digits)
                if d == 'min':
                    value = round(col_data['statistics'][2], decimal_digits)
                if d == 'median':
                    value = round(col_data['statistics'][3], decimal_digits)
                if d == 'max':
                    value = round(col_data['statistics'][4], decimal_digits)
            else:
                if d in ['mean', 'std', 'median', 'min', 'max']:
                    value = None
                    comment = f'<font color={c_medium}> WARNING: no statistics available, probably because mixed types or nans. Remove the critical values as described at the individual problems and regenerate the report to obtain statistics. <font>'
            if d == 'accumulated values':
                value = col_data['accumulatedValues']
                if len(value)>10:
                    value = value[:10]
                    value = str(value) + ' and more'
                if len(value)>0:
                    comment = f'<font color={c_medium}> WARNING: accumulated values might be a sign for systematic errors in the data collection process. Often some values are not measured values but serve as placeholders if there is no value available. Rows that contain such placeholders should be removed. Please check the histogramm below, which gives a good basis to decide whether the observed values are physical or not. In case they are not, please remove the affected rows.'
                    hint_dict['delete_accumulated_value_rows'] = True
                else:
                    value = None
            if d == 'outlier values':
                value = col_data['outlierValues']
                if len(value)>10:
                    value = value[:10]
                    value = str(value) + ' and more'
                if len(value)>0:
                    comment = f'<font color={c_medium}> WARNING: outlier values might be a sign for errors in the data collection process. Often the occur under extreme conditions that should not be considered in the following machine learning application. Please check the histogramm below, which gives a good basis to decide whether the observed values are reasonable or not. In case they are not, please remove the affected rows.'
                    hint_dict['delete_outlier_rows'] = True
                else:
                    value = None

            if value != None:
                list_of_strings.extend([d, value, comment])
                counter += 1
    if full_report:
        if col_data['timeRole']['data shift']: 
            value = 'True'
            if col_data['timeRole']['biggest_no_shift']:
                comment = f"<font color={c_medium}> WARNING: The values's statistics change significantly over time. This might indicate that different parts of the data are not comparable often due to some external conditionas that changed unnoticed. Please see the figure below and treat this column with care, because different parts of the dataset might be not comparable and therefore should not be used together in machine learning applications. You might consider splitting the dataset and using only parts of it at a time."
                hint_dict['use_slice_shift'] = True
            else:
                comment = f"<font color={c_medium}> WARNING: The values's statistics change significantly over etime. This might indicate that different parts of the data are not comparable often due to some external conditionas that changed unnoticed. Appearently no part of the dataset can be identified that has no shift, so please use this column only if you know the cause for the shift and how to handle it. You might consider splitting the dataset and using only parts of it at a time, see section '3. Separate Mixed Populations' in the data_cleaning template."
            list_of_strings.extend(['shift', value, comment])
            counter += 1

        if col_data['timeRole']['jumps']: 
            value = 'True'
            if col_data['timeRole']['biggest_no_jump']:
                comment = f"<font color={c_medium}> WARNING: The values seem to jump. This might indicate that some circumstances have changed suddenly. If this is due to changed set-parameters everything is ok, but if it is due to external, untracked parameters make sure you do not mix up different external conditions in the further usage of the data. Please see the figure below together with the figures of the set values to judge whether the jumps are reasonable or not. In case not, please split the dataset into pieces that do not contain jumps and use only one of them for further machine learning applications."
                hint_dict['use_slice_jumps'] = True
            else:
                comment = f"<font color={c_medium}> WARNING: Every value seems to jump. This might indicate that some circumstances change suddenly. If this is due to changed set-parameters everything is ok, but if it is due to external, untracked parameters make sure you do not mix up different external conditions in the further usage of the data. Please see the figure below together with the figures of the set values to judge whether the jumps are reasonable or not. In case not, please split the dataset into pieces that do not contain jumps and use only one of them for further machine learning applications. See section '3.1 Use slice of dataframe' in the data_cleaning template."
            list_of_strings.extend(['jumps', value, comment])
            counter += 1
        
    mdFile.new_line()

    mdFile.new_table(columns=3, rows=counter+1, text=list_of_strings, text_align='left')
    if data['time-series']:
        mdFile.new_paragraph(Html.image(path=convert_file_path(data['figures'][column_name]), size='950x500', align='center'))
    else:
        mdFile.new_paragraph(Html.image(path=convert_file_path(data['figures'][column_name]), size='800x550', align='center'))

    mdFile.new_line()

    # give hints
    if any([v for k,v in hint_dict.items()]):
        mdFile.new_line('___')
        mdFile.new_line()
        for key, value in hint_dict.items():
            if value:
                if key == 'convert_into_main_type_rows':
                    mdFile.new_line(f"<font color={c_hint}> Hint: To convert all values for which this is possible into the main type use `df['{column_name}'] = df['{column_name}'].astype({col_data['mainType']}, errors='ignore')`. Also see section '3.3 Type handling' in the data_cleaning template. [(learn more)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.astype.html) </font>")
                if key == 'delete_non_main_type_rows':
                    mdFile.new_line(f"<font color={c_hint}> Hint: To delete all rows with other types use `df.drop(df[df['{column_name}'].apply(lambda x : pd.isnull(x) or not isinstance(x, {col_data['mainType']}))].index, inplace=True)`. Also see section '3.3 Type handling' in the data_cleaning template. [(learn more)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop.html) </font>")
                if key == 'delete_few_value_column':
                    mdFile.new_line(f"<font color={c_hint}> Hint: To delete the column use `df.drop({column_name}, axis=1, inplace=True)`. Also see section '3.2 Only keep specific columns' in the data_cleaning template. </font>")
                if key == 'delete_accumulated_value_rows':
                    mdFile.new_line(f"<font color={c_hint}> Hint: To delete all rows with accumulated values use `df = df[df['{column_name}'].isin({list(set(col_data['accumulatedValues']))})==False]`, ALso see section '3.5. Manually remove rows and columns' in the data_cleaning template. [(learn more)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.isin.html) </font>")
                if key == 'delete_outlier_rows':
                    mdFile.new_line(f"<font color={c_hint}> Hint: To delete all rows with outlier values use `df = df[df['{column_name}'].isin({list(set(col_data['outlierValues']))})==False]`. Also see section '4.3 Outliers' in the data_cleaning template. [(learn more)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.isin.html) </font>")
                if key == 'use_slice_shift': # maybe suggest the largest part of the data which meets the no-shift-criterion
                    mdFile.new_line(f"<font color={c_hint}> Hint: To extract a part from the data that contains no shifts use `df = df.iloc[{col_data['timeRole']['biggest_no_shift'][0][0]}:{col_data['timeRole']['biggest_no_shift'][0][1]}]`. Also see section '3.1 Use slice of dataframe' in the data_cleaning template. [(learn more)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.iloc.html) </font>") 
                if key == 'use_slice_jumps': # maybe suggest the largest part of the data which meets the no-jump-criterion
                    mdFile.new_line(f"<font color={c_hint}> Hint: To extract a part from the data that contains no jumps use `df = df.iloc[{col_data['timeRole']['biggest_no_jump'][0][0]}:{col_data['timeRole']['biggest_no_jump'][0][1]}]`. Also see section '3.1 Use slice of dataframe' in the data_cleaning template. [(learn more)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.iloc.html) </font>")

        mdFile.new_line()
        mdFile.new_line('___')

    mdFile.new_line()
    mdFile.new_line(f'Go back to \n[column information](#column-information) or [overview](#overview)')
    mdFile.new_line()
    


# Create a table of contents
#mdFile.new_table_of_contents(table_title='Contents', depth=2)

# Create File
mdFile.create_md_file()

# pip install mdutils
