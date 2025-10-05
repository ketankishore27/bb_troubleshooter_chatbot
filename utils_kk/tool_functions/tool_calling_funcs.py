from langchain_core.tools import tool
import pandas as pd
import datetime
from utils_kk.tool_functions.data_transformer import *

def get_reboots_data(router_data:pd.DataFrame, serial_number:str) -> pd.DataFrame:
    """
    Get dataframe of hardware reboots for given serial number

    Args:
        router_data (pd.DataFrame): dataframe of router data
        serial_number (str): serial number of the router

    Returns:
        pd.DataFrame: dataframe of hardware reboots for given serial number
    """
    
    df = pd.DataFrame.from_records(router_data)
    df = df[df['serialnumber'] == serial_number]
    df = df[df['hardware_reboot'] == 1]
    return df[['serialnumber', 'timestamp','hardware_reboot']].reset_index(drop=True)


@tool(parse_docstring=True)
def extract_comparison_data(timestamp:str, router_data:pd.DataFrame) ->  pd.DataFrame:
    """Extract comparison data from before the reboot

    Args:
        timestamp (str): timestamp of reboot

    Returns:
        pd.DataFrame: aggregated data
    """

    df_h = router_data.copy(deep=True) 
    # get one hour of data if available
    time_req = datetime.datetime.strptime(timestamp, FORMAT)
    df_prereboot_h = get_prereboot_data(df_h,time_req,hours=1)
    # 6h prior to event 
    df_prereboot_6h = get_prereboot_data(df_h,time_req,hours=6)
    # 24h prior to event 
    df_prereboot_d = get_prereboot_data(df_h,time_req,hours=24)
    # get baseline data for comparison
    df = router_data.copy(deep=True) 
    df = get_baseline_data(df,time_req)
    final_data = pd.concat([df_prereboot_h,df_prereboot_6h,df_prereboot_d,df],axis=0).reset_index(drop=True).T
    final_data = final_data.rename_axis('Variable').rename(columns={0: "pre-reboot_hours", 1:"pre-reboot_6_hours",2: "pre-reboot_1_day", 3: "baseline"}).reset_index()
    descriptions = pd.read_csv(FIELD_DESCRIPTIONS_FILE)
    numbers = list(descriptions[descriptions['dtype']=='number']['Field Name'])
    final_data['hour_to_baseline_change'] = final_data.apply(lambda x: (x['pre-reboot_hours']-x['baseline']) if (x['Variable'] in numbers) else (x['pre-reboot_hours']!=x['baseline']), axis=1)
    final_data['6hour_to_baseline_change'] = final_data.apply(lambda x: (x['pre-reboot_6_hours']-x['baseline']) if (x['Variable'] in numbers) else (x['pre-reboot_6_hours']!=x['baseline']), axis=1)
    final_data['day_to_baseline_change'] = final_data.apply(lambda x: (x['pre-reboot_1_day']-x['baseline']) if (x['Variable'] in numbers) else (x['pre-reboot_1_day']!=x['baseline']), axis=1)
    
    return final_data


@tool(parse_docstring=True)
def column_info(FIELD_DESCRIPTIONS_FILE:str, col_name:str) ->  str:
    """Extract field descriptions for columns of dataframe

    Args:
        col_name (str): column name

    Returns:
        str: field names and descriptions in markdown
    """

    descriptions = pd.read_csv(FIELD_DESCRIPTIONS_FILE)
    description = descriptions[descriptions['Field Name']==col_name]['Description']
    return description


@tool(parse_docstring=True)
def get_baseline_statistics(data_dir:str) -> pd.DataFrame:
    """
    Returns statistical data about the baseline of a router

    Args:
        data_dir (str): directory containing parquet files of the baseline router data

    Returns:
        pd.DataFrame: statistical data about the baseline of the router
    """
    baseline_router_data = read_directory_parquet(data_dir)
    return baseline_router_data

