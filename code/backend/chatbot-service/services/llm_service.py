"""
LLM Service for handling OpenAI and Azure OpenAI API calls.
"""
from typing import List, Optional
from openai import OpenAI, AzureOpenAI
from config import llm_config
from models import ChatMessage


class LLMService:
    """Service for interacting with LLM providers"""
    
    def __init__(self):
        self.provider = llm_config.provider
        self._client = None
        self._initialized = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client based on provider"""
        if self.provider == "mock":
            self._client = None
            self._initialized = True
            return

        if self.provider == "azure_openai":
            if not (llm_config.azure_openai_api_key and llm_config.azure_openai_endpoint and llm_config.azure_openai_deployment_name):
                self.provider = "mock"
                self._client = None
                self._initialized = True
                return
            self._client = AzureOpenAI(
                api_key=llm_config.azure_openai_api_key,
                api_version=llm_config.azure_openai_api_version,
                azure_endpoint=llm_config.azure_openai_endpoint,
            )
            self._deployment_name = llm_config.azure_openai_deployment_name
            self._temperature = llm_config.azure_openai_temperature
            self._max_tokens = llm_config.azure_openai_max_tokens
            self._initialized = True
        else:  # openai
            if not llm_config.openai_api_key:
                self.provider = "mock"
                self._client = None
                self._initialized = True
                return
            self._client = OpenAI(
                api_key=llm_config.openai_api_key,
                base_url=llm_config.openai_base_url,
            )
            self._model = llm_config.openai_model
            self._temperature = llm_config.openai_temperature
            self._max_tokens = llm_config.openai_max_tokens
            self._initialized = True

    def is_enabled(self) -> bool:
        return self.provider in ("openai", "azure_openai") and self._client is not None
    
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> str:
        """
        Send a chat message to the LLM and get a response.
        
        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            
        Returns:
            The assistant's response
        """
        if not self._initialized:
            self._initialize_client()
        if self.provider == "mock":
            return "현재 LLM이 설정되지 않아(mock) 마이크로서비스 오케스트레이터로 처리합니다."

        # Build messages list
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Call the appropriate API
        if self.provider == "azure_openai":
            response = self._client.chat.completions.create(
                model=self._deployment_name,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
        else:  # openai
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
        
        return response.choices[0].message.content
    
    def stream_chat(
        self,
        message: str,
        conversation_history: Optional[List[ChatMessage]] = None
    ):
        """
        Stream a chat response from the LLM.
        
        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            
        Yields:
            Chunks of the assistant's response
        """
        if not self._initialized:
            self._initialize_client()
        if self.provider == "mock":
            text = self.chat(message=message, conversation_history=conversation_history)
            for i in range(0, len(text), 32):
                yield text[i : i + 32]
            return

        # Build messages list
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Call the appropriate API with streaming
        if self.provider == "azure_openai":
            stream = self._client.chat.completions.create(
                model=self._deployment_name,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                stream=True,
            )
        else:  # openai
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                stream=True,
            )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# Global service instance
llm_service = LLMService()

