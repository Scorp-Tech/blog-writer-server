from openai import AzureOpenAI
import os
import requests

class PollinationAIAssistant():
    def __init__(self, model="gpt-4o", instruction="You are a helpful assistant", response_format={"type": "text"}, messages=[]):
        self.messages = [{
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": instruction
                }
            ]
        },*messages]
        self.model, self.instruction, self.response_format = model, instruction, response_format
        self.client = AzureOpenAI(
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"), 
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
            api_version="2024-08-01-preview"
        )
    
    def sendMessage(self, message):
        self.addMessage(message)
        return self.getMessage()
    
    def addMessage(self, message):
        self.messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        })
    
    def getMessage(self):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            response_format=self.response_format
        )
        self.messages.append({
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": response.choices[0].message.content
                }
            ]
        })
        return response.choices[0].message.content

class PollinationAI():
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"), 
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
            api_version="2024-08-01-preview"
        )
    
    def sendMessage(self, message, model="gpt-4o", response_format={"type": "text"}):
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "You're a helpful assistant.",
                        }
                    ],
                },
                {"role": "user", "content": [{"type": "text", "text": message}]},
            ],
            response_format=response_format
        )
        return response.choices[0].message.content
    
    def generateImage(self, prompt, width=1024, height=640, model='flux', seed=None, generate=True):
        url = f"https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model={model}&seed={seed}&nologo=true&safe=true"
        if(generate):
            response = requests.get(url)
            return response.url
        else:
            return url


client = PollinationAIAssistant()