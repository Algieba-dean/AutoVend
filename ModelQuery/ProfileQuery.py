import json
import os
#from pprint import pp

class ConnectionProfileQuery:
    def __init__(self):
        # query tree and vehicle date configure path
        self.profile_dir_path = './Backend/storage/profiles/'
        self.connection_data_list={}

        self.connection_data_list=self._get_all_connection_number_with_user_name()

    
    def query_connection_profile_name(self, phone_num: str) -> str:
        """
        based on the input phone number, find its connection user name from relation user profile
        
        Args:
            phone_num: the incoming call phone number
            
        Returns:
            matched connection user name
        """
        # if dict_query empty return
        if not phone_num:
            return ""

        if phone_num in self.connection_data_list:
            return self.connection_data_list[phone_num]
        else:
            print(f"Not found matched connection user name for {phone_num}")
            return ""
    
    def _get_all_connection_number_with_user_name(self):
        """
        get all connection numbers with their user names
        
        Returns:
            dict, key is connection number, value is user name
        """
        connection_data_list = {}
        if os.path.exists(self.profile_dir_path):
            for root, _, files in os.walk(self.profile_dir_path):
                for file in files:
                    if file.endswith('.json'):
                        try:
                            with open(root+file, 'rb') as f:
                                profile_data = json.load(f)
                                connection_data_list[profile_data["connection_information"]["connection_phone_number"]]=profile_data["connection_information"]["connection_user_name"]
                        except Exception as e:
                            print(f"Error loading car data from {file}: {e}")
        
        return connection_data_list


# test code
#if __name__ == "__main__":
#    c = ConnectionProfileQuery()
    # test query
#    result = c.query_connection_profile_name("15900000002")
#    print("query results:")
#    pp(result)