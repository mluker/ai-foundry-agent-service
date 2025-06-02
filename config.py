from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    model_deployment_name: str = Field(
        default="gpt-4o",
        description="The name of the model deployment to use for the agent.",
    )

    project_endpoint: str = Field(
        description="The endpoint for the project API.",
    )

    app_insights_connection_string: str = Field(
        description="The connection string for Azure Application Insights.",
    )

    bing_connection_name: str = Field(
        description="The name of the Bing connection.",
    )