from utils_kk.tool_functions.data_transformer import read_directory_parquet, select_RDK_parameters, rename_RDK_parameters, \
                                   generate_extra_features, retrieve_serialnumber, get_baseline_statistics, \
                                   column_info

def get_data():
    data_dir = "knowledge_folder/datapoints/DE_router_data_all/"
    config_fileloc = 'config/config.yaml'
    serialnumber_selected = "90100000000V412000536"

    router_data = read_directory_parquet(data_dir)
    router_data = select_RDK_parameters(router_data, config_fileloc)
    router_data = retrieve_serialnumber(router_data, serialnumber_selected)
    router_data = rename_RDK_parameters(router_data)
    router_data = generate_extra_features(router_data)
    return router_data
    