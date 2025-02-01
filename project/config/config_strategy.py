import os
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Access the FLASK_ENV variable
flask_env = os.getenv('APP_ENV')

# Print the FLASK_ENV variable to verify it's loaded
print(f"FLASK_ENV: {flask_env}")

class Config_Strategy:
    def __init__(self):
        self.dynamic_config = None

    def get_dynamic_config(self):
        if (flask_env == 'dev') :
            from .dev import AppConfig

            dynamic_config = AppConfig(flask_env)
        elif (flask_env == 'hrm') :
            from .hrm import AppConfig

            dynamic_config = AppConfig(flask_env)

        elif (flask_env == 'pdthrm'):
            from .pdthrm import AppConfig

            dynamic_config = AppConfig(flask_env)
        elif (flask_env == "pdthrm-debug"):
            from .pdthrm_debug import AppConfig

            dynamic_config = AppConfig(flask_env)
        else:
            raise ValueError("Invalid environment. Add .env with flask_env value.")
        
        return dynamic_config
