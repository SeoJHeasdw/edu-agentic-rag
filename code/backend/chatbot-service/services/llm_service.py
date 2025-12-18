"""
OpenAI 및 Azure OpenAI API 호출을 처리하는 LLM 서비스.
"""
from typing import List, Optional
from openai import OpenAI, AzureOpenAI
from config import llm_config
from models import ChatMessage


class LLMService:
    """LLM 제공자(Provider)와의 상호작용을 위한 서비스"""
    
    def __init__(self):
        self.provider = llm_config.provider
        self._client = None
        self._initialized = False
        self._initialize_client()
    
    def _initialize_client(self):
        """제공자(Provider) 설정에 따라 적절한 LLM 클라이언트를 초기화합니다."""
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
        LLM에 채팅 메시지를 전송하고 응답을 받습니다.
        
        Args:
            message: 사용자의 메시지
            conversation_history: 대화의 이전 메시지 내역
            
        Returns:
            어시스턴트(AI)의 응답 내용
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
        LLM으로부터 채팅 응답을 스트리밍 방식으로 받습니다.
        
        Args:
            message: 사용자의 메시지
            conversation_history: 대화의 이전 메시지 내역
            
        Yields:
            어시스턴트(AI) 응답의 청크(조각) 데이터
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
            try:
                choices = getattr(chunk, "choices", None)
                if not choices or len(choices) == 0:
                    continue
                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None) if delta is not None else None
                if content:
                    yield content
            except Exception:
                # Never crash streaming due to provider-specific chunk shapes
                continue


# Global service instance
llm_service = LLMService()

