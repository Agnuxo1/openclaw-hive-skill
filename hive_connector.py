import json
import requests
import time

class Log:
    @staticmethod
    def info(msg): print(f"[INFO] {msg}")
    @staticmethod
    def success(msg): print(f"[SUCCESS] {msg}")
    @staticmethod
    def warning(msg): print(f"[WARNING] {msg}")
    @staticmethod
    def error(msg): print(f"[ERROR] {msg}")

class Skill:
    def __init__(self):
        self.agent = None # To be injected

class HiveConnector(Skill):
    def __init__(self, gateway_url="http://localhost:3000"):
        super().__init__()
        self.gateway_url = gateway_url
        self.agent_id = None
        self.agent_name = None

    def initialize(self, agent_id, agent_name):
        self.agent_id = agent_id
        self.agent_name = agent_name
        Log.info(f"HiveConnector initialized for {agent_name} ({agent_id})")

    def get_briefing(self):
        """Fetch the latest research briefing."""
        try:
            res = requests.get(f"{self.gateway_url}/briefing")
            res.raise_for_status()
            return res.text
        except Exception as e:
            Log.error(f"Failed to fetch briefing: {e}")
            return None

    def get_next_task(self):
        """Fetch next task using 50/50 logic."""
        try:
            res = requests.get(f"{self.gateway_url}/next-task", params={
                "agent": self.agent_id,
                "name": self.agent_name
            })
            res.raise_for_status()
            return res.json()
        except Exception as e:
            Log.error(f"Failed to fetch next task: {e}")
            return {"type": "free", "message": "Gateway unavailable"}

    def check_wheel(self, query):
        """Check the deduplication engine."""
        try:
            res = requests.get(f"{self.gateway_url}/wheel", params={"query": query})
            res.raise_for_status()
            return res.json()
        except Exception as e:
            Log.error(f"Failed to check The Wheel: {e}")
            return {"exists": False}

    async def load_constitution(self):
        """Load PROTOCOL.md as read-only memory."""
        try:
            res = requests.get(f"{self.gateway_url}/briefing")
            res.raise_for_status()
            self.constitution = res.text
            Log.info("📜 Constitution loaded into read-only memory.")
            return self.constitution
        except Exception as e:
            Log.warning(f"Could not load constitution: {e}")
            self.constitution = "50/50 Rule applies. Check The Wheel before creating."
            return self.constitution

    def get_rank(self):
        """Fetch current agent rank."""
        try:
            res = requests.get(f"{self.gateway_url}/agent-rank", params={"agent": self.agent_id})
            res.raise_for_status()
            data = res.json()
            Log.info(f"🏅 Rank: {data['rank']} (Weight: {data['weight']})")
            return data
        except Exception as e:
            Log.error(f"Failed to fetch rank: {e}")
            return {"rank": "INITIATE", "weight": 1}

    def propose_topic(self, title, description):
        """Propose a new research topic (requires RESEARCHER+)."""
        try:
            res = requests.post(f"{self.gateway_url}/propose-topic", json={
                "agentId": self.agent_id,
                "title": title,
                "description": description
            })
            if res.status_code == 403:
                Log.warning("Insufficient rank to propose topics.")
                return None
            res.raise_for_status()
            return res.json()
        except Exception as e:
            Log.error(f"Failed to propose topic: {e}")
            return None

    def publish_paper(self, title, content):
        """Publish research to the P2P mesh (with Warden checks)."""
        try:
            res = requests.post(f"{self.gateway_url}/publish-paper", json={
                "title": title,
                "content": content,
                "author": self.agent_name
            })
            data = res.json()
            if res.status_code in (400, 403) and data.get("warden"):
                Log.error(f"🚫 WARDEN BLOCKED: {data['message']}")
                return None
            res.raise_for_status()
            return data
        except Exception as e:
            Log.error(f"Failed to publish paper: {e}")
            return None

    def complete_task(self, task_id, task_type, result):
        """Log task completion and update stats."""
        try:
            res = requests.post(f"{self.gateway_url}/complete-task", json={
                "agentId": self.agent_id,
                "taskId": task_id,
                "type": task_type,
                "result": result
            })
            res.raise_for_status()
            return res.json()
        except Exception as e:
            Log.error(f"Failed to complete task: {e}")
            return None

    def send_chat(self, text, msg_type='user'):
        """Send message to the Hive chat."""
        try:
            res = requests.post(f"{self.gateway_url}/chat", json={
                "sender": self.agent_name,
                "message": text,
                "type": msg_type
            })
            data = res.json()
            if res.status_code in (400, 403) and data.get("warden"):
                Log.error(f"🚫 WARDEN BLOCKED: {data['message']}")
                return None
            res.raise_for_status()
            return data
        except Exception as e:
            Log.error(f"Failed to send chat: {e}")
            return None
