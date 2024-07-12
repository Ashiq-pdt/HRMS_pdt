from .EDR_Models import *
from .SCR_Models import *
from .SIF_Model import *


class WPS_Factory:
    
    def __init__(self, strategy: 'WPS_Strategy' ) -> None:
        self.strategy = strategy

    def generate_edr(self, employee_details, employee_payroll_details, index) -> EDR:
        EDR = self.strategy.get_edr(employee_details)
        edr_record = EDR.create_edr(employee_details, employee_payroll_details)

        # sepecial atribute for fze banks
        if isinstance(edr_record, CBT_FZE_EDR):
            edr_record.no = index
        
        return edr_record
    
    @staticmethod
    def group_edr_by_bank(edr_records):
        edr_records_by_bank = {}
        for edr in edr_records:
            bank_name = edr.bank_name  # Assuming EDR has a bank_name attribute
            if bank_name not in edr_records_by_bank:
                edr_records_by_bank[bank_name] = []
            edr_records_by_bank[bank_name].append(edr)
        return edr_records_by_bank
    
    def generate_scr(self, employer_details, employee_payroll_details, sif: SIF) -> None:
            for bank_name, edr_records in sif.EDR_records.items():
                SCR = self.strategy.get_scr(bank_name)
                if not SCR: 
                    return None
                scr_record = SCR.create_scr(employer_details, employee_payroll_details)
                scr_record.save()
                for edr_record in edr_records:
                    scr_record.update_scr(edr_record)
                    scr_record.save()
                if not hasattr(sif, 'SCRs') or sif.SCRs is None:
                    sif.SCRs = {}
                sif.SCRs[bank_name] = scr_record

    def generate_sif(self, employer_details, employee_payroll_details, current_user, sub_company = None) -> SIF:
        sif = SIF()
        sif.company = employer_details
        sif.start_date = employee_payroll_details.start_date.date()
        sif.end_date = employee_payroll_details.end_date.date()
        sif.sub_company = sub_company
        sif.created_by = current_user

        return sif

class WPS_Strategy:
    
    def __init__(self) -> None:
        self.edr_map = {
            'CBD': CBD_EDR,
            'JOYALUKKAS EXCHANGE': Joyalukkas_EDR,
            'Al Ansari Exchange': Al_Ansari_EDR,
            'Emirates_Isalamic': Emirates_Islamic_EDR,
            'RAK Bank': RAK_EDR,
            'DIB': DIB_EDR,
            'Mashreq': Mashreq_EDR,
            'CBT_FZE': CBT_FZE_EDR
        }
        self.scr_map = {
            'CBD': CBD_SCR,
            'JOYALUKKAS EXCHANGE': Joyalukkas_SCR,
            'Al Ansari Exchange': Mashreq_SCR,
            'Emirates_Isalamic': Mashreq_SCR,
            'RAK Bank': Mashreq_SCR,
            'DIB': Mashreq_SCR,
            'Mashreq': Mashreq_SCR,
            'CBT_FZE': None
        }


    def get_edr(self, employee_details) -> EDR:
        """Using the bank name we select the right edr model"""

        bank_name = employee_details.employee_sif_details.company_exchange.exchange_name

        print(bank_name, 'bank name')

        if bank_name not in self.edr_map:
            # raise Exception(f'Unsupported Bank Name: {bank_name}')
            return Generic_EDR

        return self.edr_map[bank_name]
    
    def get_scr(self, bank_name) -> SCR:
        """Using the bank name we select the right scr model"""

        # bank_name = employer_details.employee_sif_details.company_exchange.exchange_name

        if bank_name not in self.scr_map:
            # raise Exception(f'Unsupported Bank Name: {bank_name}')
            return Mashreq_SCR

        return self.scr_map[bank_name]

