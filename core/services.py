from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from langchain.chains import ConversationChain
from langchain.chat_models.base import BaseChatModel
from langchain.schema.messages import BaseMessage
from langchain.schema.output import ChatGeneration
from django.conf import settings
from .models import Conversation, Message, Prompt
import json
import requests

class DeepSeekChatModel(BaseChatModel):
    """Custom chat model for DeepSeek API"""
    api_key: str = None
    model_name: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 1000
    
    def __init__(self, api_key=None, **kwargs):
        """Initialize with API key from settings if not provided."""
        api_key = api_key or settings.DEEPSEEK_API_KEY
        super().__init__(api_key=api_key, **kwargs)
        
    def _call(self, messages, stop: list[str] | None = None) -> str:
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # Handle both LangChain messages and dictionary messages
        formatted_messages = []
        
        # Check if messages are already in the right format
        if messages and isinstance(messages[0], dict) and 'role' in messages[0]:
            formatted_messages = messages
        else:
            # Convert LangChain messages to dictionary format
            for message in messages:
                if isinstance(message, SystemMessage):
                    formatted_messages.append({"role": "system", "content": message.content})
                elif isinstance(message, HumanMessage):
                    formatted_messages.append({"role": "user", "content": message.content})
                elif isinstance(message, AIMessage):
                    formatted_messages.append({"role": "assistant", "content": message.content})

        data = {
            'model': self.model_name,
            'messages': formatted_messages,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'top_p': 0.9,
            'frequency_penalty': 0.5,
            'presence_penalty': 0.5
        }

        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            raise Exception(f"DeepSeek API error: {response.text}")

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None) -> list[ChatGeneration]:
        """Required implementation of _generate method"""
        response = self._call(messages, stop)
        message = AIMessage(content=response)
        return [ChatGeneration(message=message)]

    @property
    def _llm_type(self) -> str:
        return "deepseek"

class AIService:
    def __init__(self, api_key=None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.model = DeepSeekChatModel(
            api_key=self.api_key,
            model_name="deepseek-chat",
            temperature=0.7,
            max_tokens=1000
        )

    def create_conversation(self, user, title, system_prompt=None, priming_prompts=None):
        """Create a new conversation with optional system prompt and priming prompts"""
        conversation = Conversation.objects.create(
            user=user,
            title=title,
            system_prompt=system_prompt or "You are a helpful AI assistant that provides clear and concise responses."
        )
        
        if priming_prompts:
            conversation.priming_prompts.set(priming_prompts)
            
        # Add system message
        Message.objects.create(
            conversation=conversation,
            role='system',
            content=system_prompt or "You are a helpful AI assistant that provides clear and concise responses."
        )
        
        return conversation

    def get_conversation_history(self, conversation):
        """Convert conversation messages to LangChain format"""
        messages = []
        for msg in conversation.messages.all():
            if msg.role == 'system':
                messages.append(SystemMessage(content=msg.content))
            elif msg.role == 'user':
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == 'assistant':
                messages.append(AIMessage(content=msg.content))
        return messages

    def get_priming_prompts(self, conversation):
        """Get formatted priming prompts for the conversation"""
        priming_prompts = conversation.priming_prompts.all().order_by('priming_order')
        return [p.get_formatted_prompt() for p in priming_prompts]

    def generate_response(self, conversation, user_input, selected_prompt=None):
        """Generate a response using the conversation history and selected prompt"""
        try:
            # Get conversation history
            messages = self.get_conversation_history(conversation)
            
            # Add priming prompts if any
            priming_prompts = self.get_priming_prompts(conversation)
            if priming_prompts:
                messages.append(SystemMessage(content="\n\n".join(priming_prompts)))
            
            # Add selected prompt if any
            if selected_prompt:
                messages.append(SystemMessage(content=selected_prompt.get_formatted_prompt()))
            
            # Add user input
            messages.append(HumanMessage(content=user_input))
            
            # Generate response
            response = self.model._call(messages)
            
            # Save the messages
            Message.objects.create(
                conversation=conversation,
                role='user',
                content=user_input
            )
            
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=response,
                prompt_used=selected_prompt
            )
            
            return response
            
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")

    def get_conversation_summary(self, conversation):
        """Generate a summary of the conversation"""
        messages = self.get_conversation_history(conversation)
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarize the following conversation in 2-3 sentences:"),
            ("human", "{conversation}")
        ])
        
        conversation_text = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
        chain = summary_prompt | self.model
        
        return chain.invoke({"conversation": conversation_text}) 