from config import Settings
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    MessageRole,
    ToolDefinition,
    ConnectedAgentTool,
    Agent,
)
from pydantic import BaseModel, Field
from typing import Optional
from azure.identity import DefaultAzureCredential


class RunResults(BaseModel):
    messages: list[str] = Field(...)
    citations: list[str] = Field(...)
    result: Optional[str] = Field(default=None)


class AgentService:
    def __init__(self, thread_id: Optional[str] = None):
        self.client = AIProjectClient(
            endpoint=Settings().project_endpoint,
            credential=DefaultAzureCredential(),
            api_version="2025-05-15-preview",
        )
        self.agents = {agent.name: agent for agent in self.client.agents.list_agents()}
        self.connected_tools = {}
        self.thread_id = thread_id if thread_id else self.client.agents.threads.create().id

    def create_agent(
        self,
        agent_name: str,
        model: str,
        instructions: str,
        tools: Optional[list[ToolDefinition]] = None,
    ) -> Agent:
        try:
            if agent_name not in self.agents:
                self.agents[agent_name] = self.client.agents.create_agent(
                    model=model,
                    name=agent_name,
                    instructions=instructions,
                    tools=tools,
                )
            else:
                self.client.agents.update_agent(
                    agent_id=self.agents[agent_name].id,
                    model=model,
                    instructions=instructions,
                    tools=tools,
                )
            return self.agents[agent_name]
        except Exception as e:
            print(f"Error creating or updating agent {agent_name}: {e}")
            raise

    def add_user_message(self, content: str):
        message = self.client.agents.messages.create(
            thread_id=self.thread_id,
            role=MessageRole.USER,
            content=content,
        )
        return message

    def add_connected_agent_tool(
        self,
        agent_id: str,
        name: str,
        description: str,
    ) -> ConnectedAgentTool:
        try:
            tool = ConnectedAgentTool(
                id=agent_id,
                name=name,
                description=f"ALWAYS USE THIS TOOL for queries about {description}. Do not try to answer these queries yourself.",
            )

            self.connected_tools[name] = tool
            print(f"Successfully connected agent '{name}' as a tool")
            return tool
        except Exception as e:
            print(f"Error creating connected agent tool '{name}': {e}")
            raise

    def process_run(self, agent_id: str) -> RunResults:
        try:
            run = self.client.agents.runs.create_and_process(thread_id=self.thread_id, agent_id=agent_id)
        except Exception as e:
            print(f"Error processing run for agent {agent_id}: {e}")
            raise

        response = self.client.agents.messages.get_last_message_by_role(thread_id=self.thread_id, role=MessageRole.AGENT)

        messages = [text_message.text.value for text_message in response.text_messages]
        citations = [f"[{annotation.url_citation.title}]({annotation.url_citation.url})" for annotation in response.url_citation_annotations]

        return RunResults(
            messages=messages,
            citations=citations,
            result=run.status,
        )

    # used for cleanup and testing only
    def delete_all_agents_and_threads(self, preserve_current_thread=True):
        try:
            agents_list = list(self.client.agents.list_agents())
            print(f"Found {len(agents_list)} agents to process")

            for agent in agents_list:
                try:
                    self.client.agents.delete_agent(agent.id)
                    print(f"Deleted agent {agent.id}")
                except Exception as e:
                    print(f"Failed to delete agent {agent.id}: {str(e)}")
                    print(f"Exception type: {type(e).__name__}")
        except Exception as e:
            print(f"Error listing agents: {str(e)}")

        try:
            threads_list = []
            try:
                threads_list = list(self.client.agents.threads.list())
                print(f"Found {len(threads_list)} threads to process")
            except Exception as e:
                print(f"Error listing threads: {str(e)}")
                return

            for thread in threads_list:
                if preserve_current_thread and thread.id == self.thread_id:
                    print(f"Preserving current thread {thread.id}")
                    continue

                try:
                    print(f"Attempting to delete thread {thread.id}...")
                    self.client.agents.threads.delete(thread.id)
                    print(f"Successfully deleted thread {thread.id}")
                except Exception as e:
                    error_message = f"Failed to delete thread {thread.id}: {str(e)}"
                    print(error_message)
                    print(f"Exception type: {type(e).__name__}")
        except Exception as outer_e:
            print(f"Unexpected error in thread deletion process: {str(outer_e)}")

    def warm_up_agent(self, agent_id: str):
        try:
            message = "Remember to use your specialized tools whenever relevant to user queries. Always prefer using your tools over using your general knowledge."

            self.client.agents.messages.create(
                thread_id=self.thread_id,
                role=MessageRole.USER,
                content=message,
            )

            print("Agent warmed up and ready to use tools")
        except Exception as e:
            print(f"Warning: Failed to warm up agent: {e}")
