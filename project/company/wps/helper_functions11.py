from bson import DBRef

from .bank_shortname_map import bank_dict

def get_data_for_WPS_view(sif_record):
    scrs = sif_record.SCRs
    from .EDR_Models import EDR
    from .SCR_Models import SCR

    scrs = dereference_dbrefs(scrs, SCR)
    edrs = sif_record.EDR_records
    edrs = dereference_dbrefs(edrs, EDR)

    table_head = {}

    for bank, records in edrs.items():
        raw_data = records[0]
        if raw_data:
            raw_data = raw_data.get_fields_dict()
            keys = list(raw_data.keys())
            table_head[bank] = keys[3:]

    # create a dictionary for edrs with only list of values rather then object
    edrs_valus = {key: [list(record._data.values())[3:] for record in records] for key, records in edrs.items()}
    scrs_values = {key: list(record._data.values())[6:] for key, record in scrs.items()}

    return edrs_valus, scrs_values, table_head, scrs

def dereference_dbrefs(scrs, className):
    for key, value in scrs.items():
        if isinstance(value, DBRef):
            scrs[key] = className.objects(id=value.id).first()
    return scrs


import re

def normalize_bank_name(bank_name):
    # Remove text within parentheses including the parentheses
    bank_name = re.sub(r'\s*\(.*?\)\s*', '', bank_name)
    # Convert to title case
    bank_name = bank_name.title().strip()
    return bank_name

normalized_bank_dict = {normalize_bank_name(k): v for k, v in bank_dict.items()}


def get_shortname(bank_name):
    normalized_name = normalize_bank_name(bank_name)
    return normalized_bank_dict.get(normalized_name)
