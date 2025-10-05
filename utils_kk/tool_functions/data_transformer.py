from __future__ import annotations
import pandas as pd
import glob
import yaml
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import logging
from langchain_core.tools import tool
from scipy.stats import linregress

FORMAT= '%Y-%m-%d %H:%M:%S'
CONFIG_FILE = 'config/transformation_config.yaml'


def read_directory_parquet(directory_path:str = "../datapoints/") -> pd.DataFrame:
    """Function that reads parquet files from a specified directory
    Args:
        directoryPath: directory location to read files from. 

    Returns:
        pd.DataFrame : read parquet files as a pandas Dataframe.
    """   
    router_data = pd.DataFrame()

    for file_name in glob.glob(directory_path+'*.parquet'):
        x = pd.read_parquet(file_name)
        router_data = pd.concat([router_data,x],axis=0).reset_index(drop=True)
    return router_data

def read_directory_csvs(directory_path:str = "../datapoints/") -> pd.DataFrame:

    """Function that reads csv files from a specified directory
    Args:
        directoryPath: directory location to read files from. 

    Returns:
        pd.DataFrame : read csv files as a pandas Dataframe.
    """    

    router_data = pd.DataFrame()
    for file_name in glob.glob(directory_path+'*.csv'):
        x = pd.read_csv(file_name, low_memory=False)
        router_data = pd.concat([router_data,x],axis=0).reset_index(drop=True)
    return router_data

def select_RDK_parameters(df:pd.DataFrame, yaml_file_location:str) -> pd.DataFrame:
    """Function to select column subset from router dataframe

    Args:
        df (pd.DataFrame): Dataframe with router parameter fields
        yaml_file_location (str): directory location string for parameters subset to be used from the router dataset

    Returns:
        pd.DataFrame: filtered dataframe
    """
    # load configuration variables
    with open(yaml_file_location) as file:
        var_config = yaml.safe_load(file)

    router_info_params = var_config['RDK_parameters'] 
    return df[router_info_params]

def rename_RDK_parameters(df:pd.DataFrame):
    df = df.rename(columns={'is_reboot':'hardware_reboot',
                            'reboot_firmware_flag':'firmware_reboot',
                            'ip_interface_1_lastchange_flag': 'ip_interface_1_reboot',
                            'ethernet_link_1_lastchange_flag': 'ethernet_interface_reboot',
                            'change_wifi_radio_1_channel': 'wifi_radio_1_channel_change',
                            'change_wifi_radio_2_channel': 'wifi_radio_2_channel_change',
                            'min_signalstrength':'signalstrength_min',
                            'max_signalstrength':'signalstrength_max',
                            'avg_signalstrength':'signalstrength_avg',
                            'min_lastdatadownlinkrate':'downlink_rate_min',
                            'max_lastdatadownlinkrate':'downlink_rate_max',
                            'avg_lastdatadownlinkrate':'downlink_rate_avg',
                            'min_lastdatauplinkrate':'uplink_rate_min',
                            'max_lastdatauplinkrate':'uplink_rate_max',
                            'avg_lastdatauplinkrate':'uplink_rate_avg',
                            'memusage':'memory_utilization',
                            'version':'firmware_version',
                            'hardwareversion': 'hardware_version'})
    df['date'] = df['time'].dt.strftime('%Y-%m-%d')
    df['timestamp'] = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')

    return df

def generate_extra_features(df:pd.DataFrame)-> pd.DataFrame:
    """Generate Extra features on router timeseries data

    Args:
        df (pd.DataFrame): router metrics dataframe

    Returns:
        pd.DataFrame: Router data metrics + additional features dataframe
    """

    df["wifi_radio_1_total_channels_active"] = df["wifi_radio_1_channelsinuse"].apply(lambda x: len(x.split(',')) if (isinstance(x, str) & (x!='NULL')) else 1)
    df["wifi_radio_2_total_channels_active"] = df["wifi_radio_2_channelsinuse"].apply(lambda x: len(x.split(',')) if (isinstance(x, str) & (x!='NULL')) else 1)
    # fix telemetry restart variable to be int
    df["telemetry_restart"] = df["telemetry_restart"].apply(lambda x: int(0 if x is None else x))
    return df

def data_period_retrieval (df:pd.DataFrame, time_start:datetime, time_end:datetime) ->  pd.DataFrame:
    """Function to filter provided data based on serial number and time period

    Args:
        df (pd.DataFrame): router fields dataset
        time_start (datetime): start date
        time_end (datetime): end date

    Returns:
        pd.DataFrame: filtered dataframe by time period and serial number
    """
    mask = (df['time'] >= time_start) & (df['time'] < time_end)
    filtered_df = df.loc[mask].copy()
    # sort values on time descending
    return filtered_df.sort_values(by=['time'], ascending=False)

def retrieve_serialnumber (df:pd.DataFrame,serial_number:str) ->  pd.DataFrame:
    """Function to filter provided data based on serial number

    Args:
        df (pd.DataFrame): router fields dataset
        serial_number (str): Router serial number to be selected

    Returns:
        pd.DataFrame: filtered dataframe by time period and serial number
    """
    mask = (df['serialnumber']==serial_number)
    filtered_df = df.loc[mask].copy()
    # sort values on time descending
    return filtered_df.sort_values(by=['time'], ascending=False)

def get_condition1_stats(df:pd.DataFrame, colname:str) -> dict:
    """function to group statuses in new categories and return counts of status appearances
    Current status of the connection. Enumeration of:
        Unconfigured
        Connecting
        Authenticating
        Connected
        PendingDisconnect
        Disconnecting
        Disconnected
    Args:
        df (pd.DataFrame): router data dataframe
        colname (str): column name for status field

    Returns:
        dict: dictionary with counts of status appearances
    """

    conditions = [(df[colname] == 'Connecting') | (df[colname] == 'Authenticating') |  (df[colname] == 'Connected') , 
                  (df[colname] == 'PendingDisconnect') | (df[colname] == 'Disconnecting') |  (df[colname] == 'Disconnected') 
                  ]
    choices = ['Up', 'Down']
    df.loc[:,colname] = np.select(conditions, choices, default='Unconfigured')
    # count how many times each status appeared in time duration
    status_count = df[colname].value_counts(normalize=True).mul(100).round(1).to_dict()
    return status_count

def get_condition2_stats(df:pd.DataFrame, colname:str) -> dict:
    """function to group statuses in new categories and return counts of status appearances
    When Enable is false then Status SHOULD normally be Down (or NotPresent or Error if there is a fault condition on the interface). 
    When Enable is changed to true then Status SHOULD change to Up if and only if the interface is able to transmit and receive network traffic; 
    it SHOULD change to Dormant if and only if the interface is operable but is waiting for external actions before it can transmit 
    and receive network traffic (and subsequently change to Up if still operable when the expected actions have completed); 
    it SHOULD change to LowerLayerDown if and only if the interface is prevented from entering the Up state because one or more of the interfaces beneath it is down; 
    it SHOULD remain in the Error state if there is an error or other fault condition detected on the interface;
    it SHOULD remain in the NotPresent state if the interface has missing (typically hardware) components; 
    it SHOULD change to Unknown if the state of the interface can not be determined for some reason. This parameter is based on ifOperStatus from [RFC2863].
    
    Args:
        df (pd.DataFrame): router data dataframe
        colname (str): column name for status field

    Returns:
        dict: dictionary with counts of status appearances
    """

    conditions = [(df[colname] == 'Up'),
                  (df[colname] == 'Down'),
                  (df[colname] == 'Error') | (df[colname] == 'LowerLayerDown') |  (df[colname] == 'NotPresent') ,
                  (df[colname] == 'Dormant')
                  ]
    choices = ['Up', 'Down', 'In error state', 'Waiting']
    df.loc[:,colname] = np.select(conditions, choices, default='Unknown')
    # count how many times each status appeared in time duration
    status_count = df[colname].value_counts(normalize=True).mul(100).round(1).to_dict()
    return status_count

def get_condition3_stats(df:pd.DataFrame, colname:str) -> dict:
    """function to group statuses in new categories and return counts of status appearances
    Available statuses:
    Disabled
    Enabled
    Error_Misconfigured
    Error (OPTIONAL)
    The Error_Misconfigured value indicates that a necessary configuration value is undefined or invalid. 
    The Error value MAY be used by the CPE to indicate a locally defined error condition.
    
    Args:
        df (pd.DataFrame): router data dataframe
        colname (str): column name for status field

    Returns:
        dict: dictionary with counts of status appearances
    """

    conditions = [
        (df[colname] == 'Enabled'),
        (df[colname] =='Disabled'),
        (df[colname]=='Error_Misconfigured') |  (df[colname]=='Error')
    ]
    choices = ['Up', 'Down', 'In error state']
    df.loc[:,colname] = np.select(conditions, choices, default='Unknown')
    # count how many times each status appeared in time duration
    status_count = df[colname].value_counts(normalize=True).mul(100).round(1).to_dict()
    return status_count

def get_aggregated_data(df:pd.DataFrame, time_start:datetime, time_end:datetime) ->  pd.DataFrame:
    """Function to return aggregated data for specified time duration

    Args:
        df (pd.DataFrame): router data dataframe
        time_start (datetime): time period start
        time_end (datetime): time period end

    Returns:
        pd.DataFrame: Aggregated data dataframe
    """
    
    time_start_str = time_start.strftime(FORMAT)
    time_end_str = time_end.strftime(FORMAT)

    feature_dict = dict()
    feature_dict[time_start_str] = dict()
    feature_dict[time_start_str]['end_timestamp'] = time_end_str
    with open(CONFIG_FILE) as file:
        config = yaml.safe_load(file)

    ################################
    ### start feature generation ###
    ################################

    # transfer as is
    for var in config['RDK_metrics']['transfer_as_is']:
        feature_dict[time_start_str][f"{var}"] = df[var].values[0]

    # count 
    for var in config['RDK_metrics']['count']:
        feature_dict[time_start_str][f"{var}_count"] = df[var].sum()
    # sum
    for var in config['RDK_metrics']['total_sum']:
        feature_dict[time_start_str][f"{var}_sum"] = df[var].sum()

    # conditions 1
    for var in config['RDK_metrics']['conditions_1']:
        perc = get_condition1_stats(df, var)
        try:
            feature_dict[time_start_str][f"{var}_Up_percentage"] = perc['Up']
        except KeyError as exc:
            feature_dict[time_start_str][f"{var}_Up_percentage"] = 0

    # conditions 2
    for var in config['RDK_metrics']['conditions_2']:
        perc = get_condition2_stats(df, var)
        try:
            feature_dict[time_start_str][f"{var}_Up_percentage"] = perc['Up']
        except KeyError as exc:
            feature_dict[time_start_str][f"{var}_Up_percentage"] = 0

    # conditions 3
    for var in config['RDK_metrics']['conditions_3']:
        perc = get_condition3_stats(df, var)
        try:
            feature_dict[time_start_str][f"{var}_Up_percentage"] = perc['Up']
        except KeyError as exc:
            feature_dict[time_start_str][f"{var}_Up_percentage"] = 0

    # min_max_avg
    for var in config['RDK_metrics']['min_max_avg']:
        feature_dict[time_start_str][f"{var}_min"] = df[var].dropna().min()
        feature_dict[time_start_str][f"{var}_max"] = df[var].dropna().max()
        feature_dict[time_start_str][f"{var}_avg"] = df[var].dropna().mean()  
    # min
    for var in config['RDK_metrics']['min']:
        name = var.replace('_min', '')
        feature_dict[time_start_str][f"{name}_min"] = df[var].dropna().min()
    # max
    for var in config['RDK_metrics']['max']:
        name = var.replace('_max', '')
        feature_dict[time_start_str][f"{name}_max"] = df[var].dropna().max()
    
    # percentage
    for var in config['RDK_metrics']['perc']:
        item = config['RDK_metrics']['perc'][var]
        percentage = (df[item[0]]/df[item[1]] )
        feature_dict[time_start_str][f"{item[0]}_perc_max"] = percentage.replace([np.inf, -np.inf], np.nan).max()

    # data rate 
    for var in config['RDK_metrics']['data_rate']:
        item = config['RDK_metrics']['data_rate'][var]
        data_rate = (df[item[0]]/df[item[1]] )
        feature_dict[time_start_str][f"{item[0]}_datarate_max"] = data_rate.replace([np.inf, -np.inf], np.nan).max()
    
    # channels in use
    '''
    wifi_radio_1_channelsinuse: 2.4GHz
    For channels 1 through 13, the channel interval is 5 MHz,
      but the width of each channel is 22 MHz. Therefore, 
      there is overlap between neighboring channels, which can lead to interference and degradation of the network.
    ===> no overlaps 1-6-11 : 5 channels distance no overlap

    wifi_radio_2_channelsinuse: 5GHz
    The 5 GHz band has a wider frequency range (about 500+ MHz) and is divided into more channels,
      as well as providing more non-overlapping channels. 
      The channels in the 5 GHz band are separated by a 20 MHz interval,
        and each channel is 20 MHz wide. The wider spacing between the channels 
        makes it less likely that there will be interference and allows for more simultaneous connections, 
        making it more suitable for high-speed data transmission.
    ===> no overlap by definition
    '''
    for var in config['RDK_metrics']['channels_in_use']:
        name = var.replace('_channelsinuse','')
        channel_df = df.copy()
        
        try:
        # IF it is list of channels else skip ( applies for HR data but not for DE data)
            channel_df['channels'] = df[var].str.split(',')
            # Explode X into Rows
            channel_df = channel_df.explode('channels').reset_index(drop=True)
        except Exception as exc:
            logging.info(f"channel explosion on DE data. results in error {exc}")
        
        unique_channels = channel_df['channels'].unique()
        unique_channels = [(lambda x: int(0 if (x is None)|(x=='') else x))(x) for x in unique_channels]
        # count unique channels used
        feature_dict[time_start_str][f"{name}_total_channels_used"] = len(unique_channels)
        # identify if there are overlapping channels
        # has close channels <5 channel distance?
        if var == 'wifi_radio_1_channelsinuse':
            feature_dict[time_start_str][f"{name}_overlapping_channels"] = (np.diff(sorted(list(unique_channels)))<5).any()
    
    for var in config['RDK_metrics']['slope']:
        # df has columns: 'time' (datetime-like) and 'y' (numeric)
        g = df.dropna(subset=['time', var]).sort_values('time')
        # pandas datetimes are ns; 30 min = 30*60*1e9 ns
        x = (g['time'].astype('int64') / (30 * 60 * 1e9)).to_numpy()
        r = linregress(x, g[var].to_numpy())
        feature_dict[time_start_str][f"{var}_30min_slope"] = round(r.slope, 8)  
    
    # Prefer IQR over standard deviation when data are skewed or contain outliers
    for var in config['RDK_metrics']['iqr']:
        s_use = df[var].dropna()
        q1 = s_use.quantile(0.25)
        q3 = s_use.quantile(0.75)
        iqr = q3 - q1
        feature_dict[time_start_str][f"{name}_q1"] = round(q1,6)
        feature_dict[time_start_str][f"{name}_q3"] = round(q3,6)
        feature_dict[time_start_str][f"{name}_iqr"] = round(iqr,6)
        
    final_router_data = pd.DataFrame.from_dict(feature_dict,orient='index')
    final_router_data = final_router_data.reset_index().rename(columns={'index': 'start_timestamp'})
    final_router_data['start_time'] = pd.to_datetime(final_router_data['start_timestamp'],format= FORMAT )
    final_router_data['end_time'] = pd.to_datetime(final_router_data['end_timestamp'],format= FORMAT )
    return final_router_data

def get_prereboot_data(df: pd.DataFrame,time_req: datetime, hours: int)->pd.DataFrame:
    """Get pre reboot data aggregates

    Args:
        df (pd.DataFrame): Dataframe holding router data
        time_req (datetime): time of the restart
        hours (int): how many hours before the reboot event

    Returns:
        pd.DataFrame: aggregated information for period specified
    """
    past_timestamp =  time_req - relativedelta(hours=hours)
    df_oneh = data_period_retrieval(df, past_timestamp,time_req)
    if (df_oneh.shape[0]==0):
        past_timestamp =  time_req - relativedelta(hours=2*hours)
        df_prereboot = data_period_retrieval(df, past_timestamp,time_req)
        df_prereboot = get_aggregated_data(df_prereboot,past_timestamp,time_req)
    else:
        df_prereboot = get_aggregated_data(df_oneh,past_timestamp,time_req)
    df_prereboot['comparison']=f'pre-reboot_{hours}_hours' if hours<24 else 'pre-reboot_1_day'
    return df_prereboot


def get_xth_hour_prereboot(df: pd.DataFrame,time_req: datetime, hours: int)->pd.DataFrame:
    """Get pre reboot data for 1h, x hours before the restart.
    eg. get 1 hour of data aggregates 24h before the restart

    Args:
        df (pd.DataFrame): Dataframe holding router data
        time_req (datetime): time of the restart
        hours (int): how many hours before the reboot event

    Returns:
        pd.DataFrame: aggregated information for period specified
    """
    end_timestamp =  time_req - relativedelta(hours=hours)
    xth_hour = end_timestamp - relativedelta(hours=1)
    df_oneh = data_period_retrieval(df, xth_hour,end_timestamp)
    if (df_oneh.shape[0]==0):
        xth_hour = end_timestamp - relativedelta(hours=2)
        df_prereboot = data_period_retrieval(df, xth_hour,end_timestamp)
        df_prereboot = get_aggregated_data(df_prereboot,xth_hour,end_timestamp)
    else:
        df_prereboot = get_aggregated_data(df_oneh,xth_hour,end_timestamp)
    df_prereboot['comparison']='pre-reboot' if hours<24 else 'pre-reboot_1_day'
    return df_prereboot


def get_baseline_data(df: pd.DataFrame,time_req: datetime) -> pd.DataFrame:
    """Get baseline information aggregates

    Args:
        df (pd.DataFrame): Dataframe holding router data
        time_req (datetime): time of the restart

    Returns:
        pd.DataFrame: aggregated information for period specified
    """
    try :
        #check if there is a hardware restart before the one at hand, if there is use it as past timestamp to generate baseline
        id = df[(df['hardware_reboot']==1) & (df['time']<time_req)].head(1).index.values[0]
        past_timestamp = df.at[id, 'time']
        # if last restart was more than 1 month away then take 1 month as sufficient data for comparison
        if (time_req - past_timestamp > datetime.timedelta(days=30)) :
            past_timestamp =  time_req - relativedelta(months=1)
    except IndexError as exc:
        # there are no other hardware restarts prior to timestamp, use 1 month before timestamp in this case
        past_timestamp =  time_req - relativedelta(months=1)
    df = data_period_retrieval(df, past_timestamp,time_req)
    df = get_aggregated_data(df,past_timestamp,time_req)
    df['comparison']='baseline'
    return df


def get_baseline_statistics():
    """"
        Returns statistical data about the baseline
    """
    data_dir = "datapoints/DE_baseline_router_data/"
    baseline_router_data = read_directory_parquet(data_dir)
    return baseline_router_data


def column_info(field_descriptions_file:str, col_name:str) ->  str:
    """Extract field descriptions for columns of dataframe

    Args:
        col_name (str): column name

    Returns:
        str: field names and descriptions in markdown
    """

    descriptions = pd.read_csv(field_descriptions_file)
    description = descriptions[descriptions['Field Name']==col_name]['Description']
    return description

def extract_comparison_data(timestamp:str) ->  pd.DataFrame:
        """Extract comparison data from before the reboot

        Args:
            timestamp (str): timestamp of reboot

        Returns:
            pd.DataFrame: aggregated data
        """
        global router_data
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
