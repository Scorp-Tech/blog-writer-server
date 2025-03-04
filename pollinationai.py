import requests
import json

class PollinationAIAssistant():
    def __init__(self, model="openai-large", instruction="You are a helpful assistant", response_format={"type": "text"}, messages=[]):
        self.messages = [{
            "role": "system",
            "content": instruction
        },*messages]
        self.model, self.instruction, self.response_format = model, instruction, response_format
    
    def sendMessage(self, message):
        self.addMessage(message)
        return self.getMessage()
    
    def addMessage(self, message):
        self.messages.append({
            "role": "user",
            "content": message
        })
    
    def getMessage(self):
        response = requests.post("https://text.pollinations.ai/", data=json.dumps({
            "model": self.model,
            "messages": self.messages,
            "response_format": self.response_format
        }), headers={ "Content-Type": "application/json" })
        self.messages.append({
            "role": "assistant",
            "content": response.text
        })
        if(response.status_code != 200):
            return
        return response.text

class PollinationAI():
    def __init__(self):
        pass
    
    def createAssistant(
        model="openai-large",
        instruction="You are a helpful assistant",
        response_format={"type": "text"},
        messages = []
    ) -> PollinationAIAssistant:
        return PollinationAIAssistant(model, instruction, response_format, messages)
    
    def sendMessage(self, message, model="openai-large", response_format={"type": "text"}):
        response = requests.post("https://text.pollinations.ai/", data=json.dumps({
            "model": model,
            "messages": [{
                "role": "user",
                "content": message
            }],
            "response_format": response_format
        }), headers={ "Content-Type": "application/json" })
        if(response.status_code != 200):
            return
        return response.text

    def generateImage(prompt, width=1024, height=640, model='flux', seed=None, generate=False):
        url = f"https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model={model}&seed={seed}&nologo=true&safe=true"
        response = requests.get(url)
        return response.url
    