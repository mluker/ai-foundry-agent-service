#!/usr/bin/env python3
import argparse
from typing import List

from azure.ai.agents.models import BingGroundingTool, Agent
from agent_service import AgentService
from config import Settings
from agent_instructions import (
    STOCK_PRICE_AGENT_INSTRUCTIONS,
    WEATHER_AGENT_INSTRUCTIONS,
    MAIN_AGENT_INSTRUCTIONS,
)

import os
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

# Ensure the GenAI content recording is enabled for Azure OpenTelemetry
os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = 'true'

settings = Settings()
tracer = trace.get_tracer(__name__)
configure_azure_monitor(connection_string=settings.app_insights_connection_string)


@tracer.start_as_current_span("create_specialized_agents")
def create_specialized_agents(client: AgentService) -> List[str]:

    stock_price_agent = client.create_agent(
        agent_name="stock_price_agent",
        model=Settings().model_deployment_name,
        instructions=STOCK_PRICE_AGENT_INSTRUCTIONS,
        tools=BingGroundingTool(connection_id=Settings().bing_connection_name).definitions,
    )

    weather_agent = client.create_agent(
        agent_name="weather_agent",
        model=Settings().model_deployment_name,
        instructions=WEATHER_AGENT_INSTRUCTIONS,
        tools=BingGroundingTool(connection_id=Settings().bing_connection_name).definitions,
    )

    client.add_connected_agent_tool(
        agent_id=stock_price_agent.id,
        name=stock_price_agent.name,
        description="Gets pricing information for stocks, ETFs, mutual funds, and other financial instruments",
    )

    client.add_connected_agent_tool(
        agent_id=weather_agent.id,
        name=weather_agent.name,
        description="Gets the current and historical weather data",
    )

    return [stock_price_agent.id, weather_agent.id]


@tracer.start_as_current_span("create_main_agent")
def create_main_agent(client: AgentService) -> Agent:
    combined_tools = [definition for tool in client.connected_tools.values() for definition in tool.definitions]

    # Create the main agent with access to all tools
    agent = client.create_agent(
        agent_name="main_agent",
        model=Settings().model_deployment_name,
        instructions=MAIN_AGENT_INSTRUCTIONS,
        tools=combined_tools,
    )

    return agent


@tracer.start_as_current_span("chat_loop")
def chat_loop(client: AgentService, agent_id: str):
    print("Type 'exit' to quit the application\n")

    while True:
        try:
            user_input = input("\nPrompt: ")
            if user_input.lower() == "exit":
                break

            client.add_user_message(content=user_input)
            run = client.process_run(agent_id=agent_id)

            for message in run.messages:
                print(f"\nAgent: {message}")

            if run.citations:
                print("\nSources:")
                for citation in run.citations:
                    print(f"{citation}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Azure AI Agent Chat Application")
    parser.add_argument("--thread", help="Use an existing thread ID instead of creating a new one")
    return parser.parse_args()


def main():
    args = parse_arguments()

    try:
        # Initialize the agent service
        agent_service = AgentService(thread_id=args.thread)

        # Create specialized agents
        create_specialized_agents(agent_service)

        # Create main agent
        main_agent = create_main_agent(agent_service)

        # Warm up the agent to ensure it uses tools on first query, not sure why I have to do this for the tools to be available
        agent_service.warm_up_agent(main_agent.id)

        # Start interactive chat
        chat_loop(agent_service, main_agent.id)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    main()
